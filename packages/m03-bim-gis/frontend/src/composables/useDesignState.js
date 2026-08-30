/**
 * useDesignState — 设计参数、位置切换、模板加载、方案生成
 *
 * 从 Design.vue 提取的设计状态管理逻辑。
 */

import { ref, watch } from 'vue'
import * as Cesium from 'cesium'
import { ElMessage, ElMessageBox } from 'element-plus'
import { designAPI, projectAPI } from '@/utils/request.js'
import { DEFAULT_LOCATION, getPresetLocation } from '@/config/location.js'
import { validateParameters } from '@/utils/parameterValidator.js'
import { cachedRequest } from '@/utils/requestCache.js'
import { logger } from '@/utils/logger.js'

export function useDesignState({ viewer, sites, siteCount, generateParams, designInfo, currentLocation, clearSites, addSitesToMap, zoomToSites, operationHistory, _safeSetTimeout, setHubPoint, setMachineRooms }) {
  const currentLocationName = ref('运城学院')
  const loading = ref(false)
  const generating = ref(false)
  const statusText = ref('就绪')
  const currentSchemeId = ref(null)
  const templates = ref([])
  const fieldErrors = ref({})
  const fieldWarnings = ref({})

  /** 设备拓扑清单（来自 Python 拓扑引擎 deviceLayout，扁平列表，parentDevice 关联站点） */
  const deviceLayout = ref([])

  /** 本地加载的原始 GeoJSON（保留全部 properties，送审 S3 时保真透传） */
  const rawGeoJSON = ref(null)

  /** 生成回执：回显实际使用的参数，供前端展示「AI 实际为你做了什么」 */
  const lastReceipt = ref(null)

  /** 切换位置 */
  function updateLocation(locationKey) {
    const config = getPresetLocation(locationKey)
    if (!config) return

    currentLocation.value = locationKey
    currentLocationName.value = config.name
    generateParams.centerLongitude = config.longitude.toString()
    generateParams.centerLatitude = config.latitude.toString()

    const v = viewer.value
    if (v) {
      v.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(config.longitude, config.latitude, DEFAULT_LOCATION.cameraHeight),
        duration: 2
      })
    }

    if (sites.value.length > 0) {
      ElMessageBox.confirm(
        `切换到${config.name}将清空当前站点数据，是否继续？`,
        '切换位置',
        { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
      ).then(() => {
        clearSites()
        ElMessage.success(`已切换到 ${config.name} (${config.city})`)
      }).catch(() => {
        currentLocation.value = 'yuncheng'
        currentLocationName.value = '运城学院'
      })
    } else {
      ElMessage.success(`已切换到 ${config.name} (${config.city})`)
    }
  }

  /** 处理位置切换命令 */
  function handleLocationChange(command) {
    updateLocation(command)
  }

  /** 校验参数 */
  function validateFields() {
    const params = {
      centerLongitude: generateParams.centerLongitude,
      centerLatitude: generateParams.centerLatitude,
      coverageRadius: generateParams.coverageRadius,
      gridSize: generateParams.gridSize,
      sectorCount: generateParams.sectorCount
    }
    const result = validateParameters(params)
    fieldErrors.value = {}
    fieldWarnings.value = {}
    if (result.errors.length > 0) fieldErrors.value.general = result.errors
    if (result.warnings.length > 0) fieldWarnings.value.general = result.warnings
    return result.errors.length === 0
  }

  // ── 加载数据：项目选择弹窗（不默认，必须手动选择） ──
  const loadProjectDialogVisible = ref(false)
  const loadProjectOptions = ref([])
  const loadSelectedProjectId = ref(null)
  const loadProjectListLoading = ref(false)
  let resolveLoadProjectId = null

  /** 拉取后端项目列表，填充下拉选项 */
  async function fetchLoadProjectOptions() {
    loadProjectListLoading.value = true
    try {
      const res = await projectAPI.list()
      if (res && res.code === 200 && Array.isArray(res.data)) {
        loadProjectOptions.value = res.data.map(p => ({
          value: p.id,
          label: p.projectName || p.projectCode || `项目 ${p.id}`
        }))
      } else {
        loadProjectOptions.value = []
        ElMessage.warning((res && res.message) || '获取项目列表失败')
      }
    } catch (e) {
      loadProjectOptions.value = []
      // 网络/接口错误已由 axios 拦截器统一提示
    } finally {
      loadProjectListLoading.value = false
    }
  }

  /** 打开项目选择弹窗，返回用户选定（或未选）的项目ID的 Promise */
  async function promptProjectId() {
    await fetchLoadProjectOptions()
    loadSelectedProjectId.value = null // 不设置默认，强制用户选择
    loadProjectDialogVisible.value = true
    return new Promise((resolve) => {
      resolveLoadProjectId = resolve
    })
  }

  /** 确认选择 */
  function confirmLoadProject() {
    const id = loadSelectedProjectId.value
    loadProjectDialogVisible.value = false
    if (resolveLoadProjectId) {
      resolveLoadProjectId(id != null ? Number(id) : null)
      resolveLoadProjectId = null
    }
  }

  /** 取消选择 */
  function cancelLoadProject() {
    loadProjectDialogVisible.value = false
    if (resolveLoadProjectId) {
      resolveLoadProjectId(null)
      resolveLoadProjectId = null
    }
  }

  /** 加载设计数据（加载成功后自动显示站点） */
  async function loadDesignData() {
    const projectId = await promptProjectId()
    if (!projectId) return

    try {
      loading.value = true
      statusText.value = '加载中...'
      const res = await designAPI.getDesign(projectId)
      if (res.code === 200) {
        designInfo.value = res.data
        currentSchemeId.value = res.data?.id

        // 如果后端返回了机房坐标/列表（QGIS同步过来的），设置到站点管理器
        // 同时带回 QGIS 确定的管线路由类型（direct=直线 / manhattan=曼哈顿），S1 据此绘制连线
        const scheme = res.data
        if (Array.isArray(scheme.machineRooms) && scheme.machineRooms.length > 0 && setMachineRooms) {
          setMachineRooms(scheme.machineRooms)
        } else if (scheme.roomLongitude != null && scheme.roomLatitude != null && setHubPoint) {
          setHubPoint(
            scheme.roomLongitude,
            scheme.roomLatitude,
            scheme.roomName || '机房',
            scheme.routeType || 'manhattan'
          )
        }

        statusText.value = '数据已加载'
        ElMessage.success('设计数据加载成功')
        // 加载完元数据后自动拉取并渲染站点（用户无需再点"显示站点"）
        await showSites()
      } else {
        ElMessage.error(res.message || '加载失败')
      }
    } catch (error) {
      ElMessage.error('加载错误: ' + (error.message || error))
    } finally {
      loading.value = false
    }
  }

  /** 显示站点 */
  async function showSites() {
    if (sites.value.length > 0) {
      addSitesToMap()
      statusText.value = `${sites.value.length}个站点`
      ElMessage.success(`显示 ${sites.value.length} 个站点`)
      _safeSetTimeout(() => zoomToSites(), 500)
      return
    }

    if (!currentSchemeId.value) {
      await loadDesignData()
      if (!currentSchemeId.value) {
        ElMessage.warning('请先在 QGIS 插件中同步数据，再点顶部「加载数据」加载站点')
        return
      }
    }

    try {
      loading.value = true
      statusText.value = '加载站点...'
      clearSites()
      const res = await designAPI.getSites(currentSchemeId.value)
      if (res.code === 200) {
        sites.value = res.data || []
        siteCount.value = sites.value.length
        addSitesToMap()
        statusText.value = `${sites.value.length}个站点`
        ElMessage.success(`显示 ${sites.value.length} 个站点`)
        _safeSetTimeout(() => zoomToSites(), 1000)
      } else {
        ElMessage.error(res.message || '获取站点失败')
      }
    } catch (error) {
      ElMessage.error('错误: ' + (error.message || error))
    } finally {
      loading.value = false
    }
  }

  /** 将 QGIS 插件导出的 GeoJSON FeatureCollection 解析为站点列表 */
  function parseGeoJSONToSites(geojson) {
    if (!geojson || geojson.type !== 'FeatureCollection' || !Array.isArray(geojson.features)) {
      throw new Error('文件格式错误：不是有效的 GeoJSON FeatureCollection')
    }

    const features = geojson.features.filter(f => f?.geometry?.type === 'Point')
    if (features.length === 0) {
      throw new Error('未在 GeoJSON 中找到 Point 类型的站点数据')
    }

    return features.map((f, idx) => {
      const props = f.properties || {}
      const coords = f.geometry.coordinates || []
      const siteId = props.site_id || props.siteId || `SITE-${String(idx + 1).padStart(3, '0')}`
      const lon = Number(coords[0] ?? props.longitude ?? props.lon)
      const lat = Number(coords[1] ?? props.latitude ?? props.lat)

      if (isNaN(lon) || isNaN(lat)) {
        logger.warn('DesignState', `站点 ${siteId} 坐标无效，跳过`)
        return null
      }

      return {
        siteId,
        longitude: lon,
        latitude: lat,
        towerHeight: Number(props.tower_height ?? props.towerHeight ?? 30),
        siteType: props.site_type || props.siteType || 'MACRO',
        numSectors: Number(props.num_sectors ?? props.numSectors ?? 3),
        scenario: (props.scenario || 'URBAN').toUpperCase(),
        band: props.band || '2.6GHz',
        frequency: Number(props.frequency ?? 2600),
        power: Number(props.power ?? 160),
        gain: Number(props.gain ?? 22),
        isValid: props.is_valid !== undefined ? Boolean(props.is_valid) : (props.isValid !== undefined ? Boolean(props.isValid) : true),
        rsrp: Number(props.rsrp ?? -85),
        roomId: props.room_id || props.roomId || props.served_room_id || props.servedRoomId || null,
        roomName: props.room_name || props.roomName || null,
      }
    }).filter(Boolean)
  }

  /** 加载本地 GeoJSON 文件并渲染到地图 */
  async function loadLocalGeoJSON(geojson) {
    try {
      loading.value = true
      rawGeoJSON.value = geojson // 保留原始数据，供「送审 S3」保真透传
      statusText.value = '加载本地文件...'
      clearSites()

      const parsedSites = parseGeoJSONToSites(geojson)
      if (parsedSites.length === 0) {
        ElMessage.warning('文件中未解析到有效站点')
        return false
      }

      sites.value = parsedSites
      siteCount.value = parsedSites.length

      // 从 GeoJSON 顶层 properties 回填设计信息（如 band/tower_height）
      const meta = geojson.properties || {}
      designInfo.value = {
        schemeName: '本地加载方案',
        projectId: null,
        frequencyBand: meta.band || meta.frequencyBand || '2.6GHz',
        towerHeight: Number(meta.tower_height ?? meta.towerHeight ?? 30),
        totalSites: parsedSites.length,
        validSites: parsedSites.filter(s => s.isValid).length,
        invalidSites: parsedSites.filter(s => !s.isValid).length,
      }
      currentSchemeId.value = null

      // 恢复机房真实坐标 + 路由类型（与 QGIS 一致）
      // 旧版 GeoJSON 无 machine_rooms 时，前端会 fallback 到几何中心（已在 useSiteManager 内处理）
      const rooms = Array.isArray(meta.machine_rooms) ? meta.machine_rooms : []
      if (rooms.length > 0) {
        const routeType = rooms[0].route_type || meta.route_type || 'manhattan'
        const normalizedRooms = rooms.map(r => ({
          roomId: r.room_id || r.roomId,
          name: r.name || r.room_name || '机房',
          longitude: r.longitude ?? r.lon,
          latitude: r.latitude ?? r.lat,
          routeType: r.route_type || r.routeType || routeType,
        }))
        if (setMachineRooms) {
          setMachineRooms(normalizedRooms)
          logger.info('DesignState', `本地加载恢复机房: ${normalizedRooms.length} 个，路由: ${routeType}`)
        } else if (setHubPoint) {
          const room = rooms[0]
          setHubPoint(room.longitude, room.latitude, room.name || '机房', routeType)
          logger.info('DesignState', `本地加载恢复机房: ${room.name} (${room.longitude}, ${room.latitude}) 路由: ${routeType}`)
        }
      }

      operationHistory.value.push({
        sites: JSON.parse(JSON.stringify(sites.value)),
        params: { ...generateParams }
      })

      addSitesToMap()
      statusText.value = `${parsedSites.length}个站点`
      ElMessage.success(`本地文件加载成功，共 ${parsedSites.length} 个站点`)
      _safeSetTimeout(() => zoomToSites(), 500)
      return true
    } catch (error) {
      ElMessage.error('加载本地文件失败: ' + (error.message || error))
      return false
    } finally {
      loading.value = false
    }
  }

  /** 加载模板列表 */
  async function loadTemplates() {
    try {
      const res = await cachedRequest('templates', () => designAPI.getTemplates())
      if (res && res.code === 200) {
        templates.value = res.data || []
      }
    } catch (error) {
      logger.error('DesignState', '加载模板失败', error)
    }
  }

  /** 参数化生成设计方案 */
  // ── P0: 前端本地兜底生成 ────────────────────────────────
  // 后端不可用或返回空时，前端按网格就地生成，保证地图一定有反应（演示不翻车）
  function generateSitesClientSide(p) {
    const lon = parseFloat(p.centerLongitude)
    const lat = parseFloat(p.centerLatitude)
    const radius = Math.max(100, parseInt(p.coverageRadius) || 500)
    const grid = Math.max(50, parseInt(p.gridSize) || 200)
    const sector = Math.max(1, parseInt(p.sectorCount) || 3)
    const band = p.frequencyBand || (p.templateType === 'macro' ? '3.5GHz' : '2.6GHz')
    const tower = Math.max(3, parseInt(p.towerHeight) || 35)
    const type = p.templateType || 'macro'
    const steps = Math.max(1, Math.round(radius / grid))
    const sites = []
    let id = 1
    for (let i = -steps; i <= steps; i++) {
      for (let j = -steps; j <= steps; j++) {
        const dLat = (j * grid) / 110540
        const dLon = (i * grid) / (111320 * Math.cos((lat * Math.PI) / 180))
        const dist = Math.sqrt(dLat * dLat + dLon * dLon) * 110540
        if (dist > radius) continue
        const nlon = +((lon + dLon).toFixed(6))
        const nlat = +((lat + dLat).toFixed(6))
        sites.push({
          siteId: `AI-${String(id).padStart(3, '0')}`,
          longitude: nlon,
          latitude: nlat,
          towerHeight: tower,
          frequencyBand: band,
          sectorCount: sector,
          scenario: type === 'macro' ? 'URBAN' : 'SUBURBAN',
          isValid: true,
          rsrp: Math.round(-70 - dist / 50),
          siteType: type,
          coverageRadius: radius
        })
        id++
      }
    }
    return sites
  }

  // ── P2: 草稿持久化（localStorage，刷新不丢） ─────────────
  const DRAFT_KEY = 'm03_ai_design_draft'
  function saveDraft() {
    try {
      const draft = {
        sites: sites.value,
        designInfo: designInfo.value,
        generateParams: { ...generateParams },
        savedAt: new Date().toISOString()
      }
      localStorage.setItem(DRAFT_KEY, JSON.stringify(draft))
    } catch (e) {
      logger.warn('Design', '草稿保存失败', e)
    }
  }
  function restoreDraft() {
    try {
      const raw = localStorage.getItem(DRAFT_KEY)
      if (!raw) return false
      const draft = JSON.parse(raw)
      if (!draft.sites || draft.sites.length === 0) return false
      sites.value = draft.sites
      siteCount.value = draft.sites.length
      if (draft.designInfo) designInfo.value = draft.designInfo
      if (draft.generateParams) Object.assign(generateParams, draft.generateParams)
      return true
    } catch (e) {
      return false
    }
  }
  // 用户主动清除时一并清掉草稿，避免刷新后草稿“复活”造成“清除没生效”的错觉
  function clearDraft() {
    try { localStorage.removeItem(DRAFT_KEY) } catch (_) { /* ignore */ }
  }

  async function generateDesign() {
    // P2: 矛盾输入校验（具体报错而非静默 return）
    const radius = parseInt(generateParams.coverageRadius)
    const sector = parseInt(generateParams.sectorCount)
    if (isNaN(radius) || radius <= 0) {
      ElMessage.error('覆盖半径必须大于 0，请检查输入')
      return
    }
    if (isNaN(sector) || sector < 1) {
      ElMessage.error('扇区数至少为 1，请检查输入')
      return
    }
    if (!validateFields()) {
      ElMessage.error('参数校验失败，请修正错误后重试')
      return
    }

    // P0: 坐标兜底 —— 解析后若无有效坐标，默认运城学院样例区域
    let centerLon = parseFloat(generateParams.centerLongitude)
    let centerLat = parseFloat(generateParams.centerLatitude)
    if (isNaN(centerLon) || isNaN(centerLat)) {
      const def = getPresetLocation(currentLocation.value) || DEFAULT_LOCATION
      centerLon = def.longitude
      centerLat = def.latitude
      generateParams.centerLongitude = String(centerLon)
      generateParams.centerLatitude = String(centerLat)
      ElMessage.info('未识别到坐标，已默认使用运城学院样例区域')
    }

    const params = {
      projectId: designInfo.value?.projectId || 1,
      schemeName: '参数化生成方案',
      templateType: generateParams.templateType,
      centerLongitude: centerLon,
      centerLatitude: centerLat,
      coverageRadius: radius,
      frequencyBand: generateParams.frequencyBand ||
        (generateParams.templateType === 'macro' ? '3.5GHz'
          : generateParams.templateType === 'micro' ? '2.6GHz' : '2100MHz'),
      towerHeight: parseInt(generateParams.towerHeight) || 35,
      gridSize: parseInt(generateParams.gridSize),
      sectorCount: sector
    }

    try {
      generating.value = true
      statusText.value = '生成中...'
      deviceLayout.value = [] // 先用空，后端返回真实设备清单时再填充
      rawGeoJSON.value = null // 本次为参数生成，不以本地文件送审

      // 方案A：走「任务式生成」——先建任务(带 paramsJson)，再执行任务(执行后自动推送 S3 审查)
      // 后端不可用或返回空 → 前端兜底（P0 保证地图有反应）。
      let sitesData = null
      let source = 'client'
      let s3TaskNo = null
      try {
        const taskNo = 'DT-' + Date.now().toString(36).toUpperCase().slice(-6)
          + Math.floor(Math.random() * 1296).toString(36).toUpperCase().padStart(2, '0')
        const createRes = await designAPI.createDesignTask({
          taskNo,
          taskName: 'S1-S3联调设计-' + taskNo,
          projectId: params.projectId,
          paramsJson: JSON.stringify(params),
          idempotencyKey: taskNo,
          createdBy: 'S1模块',
          status: 'DRAFT'
        })
        let taskId = null
        if (createRes && createRes.code === 200) {
          taskId = Number(createRes.data)
        }
        if (!taskId) {
          logger.warn('Design', '建任务未返回 id，转前端兜底')
        } else {
          const genRes = await designAPI.executeDesignTask(taskId)
          if (genRes && genRes.code === 200 && genRes.data && Array.isArray(genRes.data.sites) && genRes.data.sites.length > 0) {
            sitesData = genRes.data.sites
            source = 'backend'
            // B线：保留拓扑引擎返回的设备拓扑清单（铁塔/天线/RRU/BBU/电源/传输等）
            deviceLayout.value = Array.isArray(genRes.data.deviceLayout) ? genRes.data.deviceLayout : []
            s3TaskNo = taskNo
          } else if (genRes && genRes.code === 200) {
            logger.warn('Design', '任务执行返回空站点，转前端兜底')
          }
        }
      } catch (e) {
        logger.warn('Design', '任务式生成失败，使用前端兜底生成', e)
      }

      if (!sitesData || sitesData.length === 0) {
        sitesData = generateSitesClientSide(params)
        if (source !== 'client') {
          ElMessage.warning('后端未返回站点，已使用前端本地生成预览')
        }
      }

      // 先清旧数据，再赋新值，最后渲染；避免 clearSites() 把刚赋值的 sites 清空
      clearSites()

      sites.value = sitesData
      siteCount.value = sitesData.length

      designInfo.value = {
        projectId: 1,
        schemeName: '参数化生成方案',
        frequencyBand: params.frequencyBand,
        towerHeight: params.towerHeight,
        totalSites: sitesData.length,
        validSites: sitesData.filter(s => s.isValid !== false).length,
        invalidSites: sitesData.filter(s => s.isValid === false).length
      }

      // P1: 生成回执 —— 实际使用了什么参数，展示给用户做核对
      lastReceipt.value = {
        siteCount: sitesData.length,
        templateType: params.templateType,
        location: `${centerLon.toFixed(4)}, ${centerLat.toFixed(4)}`,
        coverageRadius: radius,
        sectorCount: sector,
        frequencyBand: params.frequencyBand,
        towerHeight: params.towerHeight,
        source,
        s3TaskNo
      }

      operationHistory.value.push({
        sites: JSON.parse(JSON.stringify(sites.value)),
        params: { ...generateParams }
      })

      addSitesToMap()
      statusText.value = `${sites.value.length}个站点已生成`
      if (source === 'backend' && s3TaskNo) {
        ElMessage.success(`成功生成 ${sites.value.length} 个站点，已推送 S3 审查（设计任务号 ${s3TaskNo}）`)
      } else {
        ElMessage.success(`成功生成 ${sites.value.length} 个站点`)
      }

      // P2: 自动存草稿
      saveDraft()

      _safeSetTimeout(() => zoomToSites(), 500)
    } catch (error) {
      ElMessage.error('生成错误: ' + (error.message || error))
    } finally {
      generating.value = false
    }
  }

  /** 送审 S3 审查（方案 A）：把当前站点推给 S3 规则引擎 */
  const submitting = ref(false)
  const lastSubmittedHash = ref(null)   // 同一批数据送审成功后锁定，站点/GeoJSON 变化时解锁

  function hashPayload(devices, designTaskName) {
    let h = 0
    const str = JSON.stringify({ designTaskName, count: devices.length, ids: devices.map(d => d.deviceId).sort() })
    for (let i = 0; i < str.length; i++) {
      h = ((h << 5) - h) + str.charCodeAt(i)
      h |= 0
    }
    return String(h)
  }

  // 需提升到「设备顶层」的工程字段（对应 S3ReviewDevice 顶层字段）。
  // S3 Python 引擎 real_engine_check 对 EL-001/002/003/FT-001 直接读 device.get('xxx')，
  // 而非 device.params；若仅放 params 会导致引擎读不到 → 标记为「待核查(pending)」。
  // 这里把这些字段从 GeoJSON properties 提升到设备顶层，同时保留 params（B-5 规则仍读 params）。
  const S3_TOP_LEVEL_FIELDS = [
    'material', 'burialDepth', 'groundingResistance', 'cableDiameter',
    'bendingRadius', 'crossSection', 'actualCurrent', 'capacity', 'fibreUsed'
  ]
  function liftS3TopLevelFields(src) {
    const out = {}
    if (src && typeof src === 'object') {
      for (const k of S3_TOP_LEVEL_FIELDS) {
        const v = src[k]
        if (v !== undefined && v !== null && v !== '') out[k] = v
      }
    }
    return out
  }

  async function submitToS3Review() {
    if (sites.value.length === 0) {
      ElMessage.warning('请先加载或生成站点数据，再送审 S3')
      return
    }
    try {
      submitting.value = true

      let devices = []
      let designTaskName = 'S1 本地加载数据送审'

      if (rawGeoJSON.value && Array.isArray(rawGeoJSON.value.features)) {
        // 优先用原始 GeoJSON，保真度最高（含全部 properties + 机房 + 馈线）
        const pointFeatures = rawGeoJSON.value.features.filter(f => f?.geometry?.type === 'Point')
        devices = pointFeatures.map((f) => {
          const props = f.properties || {}
          const coords = f.geometry.coordinates || []
          return {
            deviceId: props.site_id || props.siteId || 'SITE',
            deviceName: props.name || props.site_name || props.siteId || '站点',
            // 允许 GeoJSON properties 声明规范设备类型（tower / communication_room /
            // power_cable / communication_cable ...），S3 引擎按 deviceType 选取可比对规则；
            // 缺省回退 site，保证无声明时仍可推送。
            deviceType: props.deviceType || 'site',
            coordinates: `[${Number(coords[0])},${Number(coords[1])},0]`,
            // 提升到设备顶层，供 EL-001/002/003/FT-001 真实比对
            ...liftS3TopLevelFields(props),
            params: { ...props }
          }
        })
        // 机房也作为设备推过去，让 S3 拿到更完整的上下文
        const rooms = (rawGeoJSON.value.properties && Array.isArray(rawGeoJSON.value.properties.machine_rooms))
          ? rawGeoJSON.value.properties.machine_rooms : []
        rooms.forEach((r) => {
          devices.push({
            deviceId: r.room_id || r.roomId,
            deviceName: r.name || r.room_name || '机房',
            deviceType: r.deviceType || 'room',
            coordinates: `[${Number(r.longitude ?? r.lon)},${Number(r.latitude ?? r.lat)},0]`,
            // 提升到设备顶层：capacity/fibreUsed(FT-001 容量校验) / groundingResistance(EL-003)
            ...liftS3TopLevelFields(r),
            params: { ...r }
          })
        })
        // 馈线电缆（GeoJSON top-level properties.cables）：用于弯曲半径 / 载流量真实比对
        const cables = (rawGeoJSON.value.properties && Array.isArray(rawGeoJSON.value.properties.cables))
          ? rawGeoJSON.value.properties.cables : []
        cables.forEach((c) => {
          devices.push({
            deviceId: c.cableId || c.id || ('CABLE-' + devices.length),
            deviceName: c.name || c.cableId || '馈线',
            deviceType: c.deviceType || 'communication_cable',
            coordinates: `[${Number(c.longitude ?? c.lon)},${Number(c.latitude ?? c.lat)},0]`,
            // 提升到设备顶层：cableDiameter/bendingRadius(EL-001) / crossSection/actualCurrent/material(EL-002)
            ...liftS3TopLevelFields(c),
            params: { ...c }
          })
        })
        const savedAt = rawGeoJSON.value.properties?.saved_at
        designTaskName = 'S1-GeoJSON送审' + (savedAt ? '-' + savedAt : '')
      } else {
        // 兜底：参数生成 / 前端预览站点（字段较少，S3 覆盖率会偏低）
        devices = sites.value.map((s) => ({
          deviceId: s.siteId,
          deviceName: s.siteName || s.siteId,
          deviceType: 'site',
          coordinates: `[${Number(s.longitude)},${Number(s.latitude)},0]`,
          params: {
            towerHeight: s.towerHeight,
            siteType: s.siteType,
            scenario: s.scenario,
            band: s.band,
            frequency: s.frequency,
            power: s.power,
            gain: s.gain,
            isValid: s.isValid,
            rsrp: s.rsrp
          }
        }))
      }

      if (devices.length === 0) {
        ElMessage.warning('没有可送审的站点')
        return
      }

      const payloadHash = hashPayload(devices, designTaskName)
      if (lastSubmittedHash.value === payloadHash) {
        ElMessage.warning('当前数据已送审，请勿重复提交；如需重新送审，请先加载或生成新的站点数据')
        return
      }

      const designTaskId = 'DT-LOCAL-' + Date.now().toString(36).toUpperCase()
      const payload = {
        designTaskId,
        designTaskName,
        designType: 'communication',
        devices
      }
      // 转发 GeoJSON 顶层 pipeline（GD-001 埋深）/ groundGrid（LP-004 接地网），让 S3 真实比对
      const gjProps = (rawGeoJSON.value && rawGeoJSON.value.properties) || {}
      if (Array.isArray(gjProps.pipeline) && gjProps.pipeline.length) {
        payload.pipeline = gjProps.pipeline
      }
      if (gjProps.groundGrid && typeof gjProps.groundGrid === 'object') {
        payload.extraData = { groundGrid: gjProps.groundGrid }
      }
      const res = await designAPI.submitToS3(payload)

      if (res && res.code === 200) {
        const info = res.data || {}
        lastSubmittedHash.value = payloadHash
        ElMessage.success(`已推送 S3 审查（设计任务号 ${designTaskId}，S3 审查任务ID ${info.reviewTaskId}）`)
        lastReceipt.value = {
          ...(lastReceipt.value || {}),
          s3TaskNo: designTaskId,
          s3ReviewTaskId: info.reviewTaskId,
          s3Status: info.status
        }
      } else {
        ElMessage.error((res && res.message) || '推送 S3 失败')
      }
    } catch (e) {
      ElMessage.error('推送 S3 失败: ' + (e.message || e))
    } finally {
      submitting.value = false
    }
  }

  // 站点或原始 GeoJSON 变化后，允许再次送审
  watch([() => sites.value.length, () => rawGeoJSON.value], () => {
    lastSubmittedHash.value = null
  }, { deep: true })

  return {
    currentLocationName,
    loading,
    generating,
    statusText,
    currentSchemeId,
    templates,
    fieldErrors,
    fieldWarnings,
    updateLocation,
    handleLocationChange,
    validateFields,
    promptProjectId,
    loadDesignData,
    showSites,
    loadLocalGeoJSON,
    loadTemplates,
    generateDesign,
    submitToS3Review,
    submitting,
    lastSubmittedHash,
    lastReceipt,
    deviceLayout,
    restoreDraft,
    clearDraft,
    saveDraft,
    // 加载数据：项目选择弹窗
    loadProjectDialogVisible,
    loadProjectOptions,
    loadSelectedProjectId,
    loadProjectListLoading,
    confirmLoadProject,
    cancelLoadProject,
  }
}
