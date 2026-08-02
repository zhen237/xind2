/**
 * useDesignState — 设计参数、位置切换、模板加载、方案生成
 *
 * 从 Design.vue 提取的设计状态管理逻辑。
 */

import { ref } from 'vue'
import * as Cesium from 'cesium'
import { ElMessage, ElMessageBox } from 'element-plus'
import { designAPI, projectAPI } from '@/utils/request.js'
import { DEFAULT_LOCATION, getPresetLocation } from '@/config/location.js'
import { validateParameters } from '@/utils/parameterValidator.js'
import { cachedRequest } from '@/utils/requestCache.js'
import { logger } from '@/utils/logger.js'

export function useDesignState({ viewer, sites, siteCount, generateParams, designInfo, currentLocation, clearSites, addSitesToMap, zoomToSites, operationHistory, _safeSetTimeout, setHubPoint }) {
  const currentLocationName = ref('运城学院')
  const loading = ref(false)
  const generating = ref(false)
  const statusText = ref('就绪')
  const currentSchemeId = ref(null)
  const templates = ref([])
  const fieldErrors = ref({})
  const fieldWarnings = ref({})

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

        // 如果后端返回了机房坐标（QGIS同步过来的），设置到站点管理器
        // 同时带回 QGIS 确定的管线路由类型（direct=直线 / manhattan=曼哈顿），S1 据此绘制连线
        const scheme = res.data
        if (scheme.roomLongitude != null && scheme.roomLatitude != null && setHubPoint) {
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
      }
    }).filter(Boolean)
  }

  /** 加载本地 GeoJSON 文件并渲染到地图 */
  async function loadLocalGeoJSON(geojson) {
    try {
      loading.value = true
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
        const room = rooms[0]
        const routeType = room.route_type || meta.route_type || 'manhattan'
        if (setHubPoint) {
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
    try { localStorage.removeItem(DRAFT_KEY) } catch (_) {}
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

      // 优先走后端；失败或返回空 → 前端兜底（P0 保证地图有反应）
      let sitesData = null
      let source = 'client'
      try {
        const res = await designAPI.generateDesign(params)
        if (res && res.code === 200 && res.data && Array.isArray(res.data.sites) && res.data.sites.length > 0) {
          sitesData = res.data.sites
          source = 'backend'
        } else if (res && res.code === 200) {
          logger.warn('Design', '后端返回空站点，转前端兜底')
        }
      } catch (e) {
        logger.warn('Design', '后端生成失败，使用前端兜底生成', e)
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
        source
      }

      operationHistory.value.push({
        sites: JSON.parse(JSON.stringify(sites.value)),
        params: { ...generateParams }
      })

      addSitesToMap()
      statusText.value = `${sites.value.length}个站点已生成`
      ElMessage.success(`成功生成 ${sites.value.length} 个站点`)

      // P2: 自动存草稿
      saveDraft()

      _safeSetTimeout(() => zoomToSites(), 500)
    } catch (error) {
      ElMessage.error('生成错误: ' + (error.message || error))
    } finally {
      generating.value = false
    }
  }

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
    lastReceipt,
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
