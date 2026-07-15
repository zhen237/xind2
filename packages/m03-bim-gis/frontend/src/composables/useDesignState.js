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
        ElMessage.warning('请先点击"生成方案"按钮创建基站布局')
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
  async function generateDesign() {
    if (!validateFields()) {
      ElMessage.error('参数校验失败，请修正错误后重试')
      return
    }

    const params = {
      templateType: generateParams.templateType,
      centerLongitude: parseFloat(generateParams.centerLongitude),
      centerLatitude: parseFloat(generateParams.centerLatitude),
      coverageRadius: parseInt(generateParams.coverageRadius),
      gridSize: parseInt(generateParams.gridSize),
      sectorCount: generateParams.sectorCount
    }

    if (isNaN(params.centerLongitude) || isNaN(params.centerLatitude)) {
      ElMessage.warning('请输入有效的经纬度')
      return
    }

    try {
      generating.value = true
      statusText.value = '生成中...'

      const res = await designAPI.generateDesign(params)
      if (res.code === 200) {
        const data = res.data
        sites.value = data.sites || []
        siteCount.value = sites.value.length

        designInfo.value = {
          projectId: 1,
          schemeName: '参数化生成方案',
          frequencyBand: '2100MHz',
          towerHeight: 35,
          totalSites: data.totalSites || 0,
          validSites: data.validSites || 0,
          invalidSites: data.invalidSites || 0
        }

        operationHistory.value.push({
          sites: JSON.parse(JSON.stringify(sites.value)),
          params: { ...generateParams }
        })

        clearSites()
        addSitesToMap()
        statusText.value = `${sites.value.length}个站点已生成`
        ElMessage.success(`成功生成 ${sites.value.length} 个站点`)

        _safeSetTimeout(() => zoomToSites(), 500)
      } else {
        ElMessage.error(res.message || '生成失败')
      }
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
    loadTemplates,
    generateDesign,
    // 加载数据：项目选择弹窗
    loadProjectDialogVisible,
    loadProjectOptions,
    loadSelectedProjectId,
    loadProjectListLoading,
    confirmLoadProject,
    cancelLoadProject,
  }
}
