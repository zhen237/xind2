/**
 * useProjectManager — 项目保存/加载/导出/撤销重做
 *
 * 从 Design.vue 提取的项目管理逻辑。
 * 依赖: sites, generateParams, designInfo (通过参数传入)
 */

import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ProjectManager } from '@/utils/projectManager.js'
import { exportAsJSON, exportAsCSV, exportAsGeoJSON, buildExportData } from '@/utils/exportUtils.js'
import { createOperationHistory } from '@/utils/operationHistory.js'

export function useProjectManager({ sites, generateParams, designInfo, currentLocation, stats, clearSites, addSitesToMap, zoomToSites }) {
  const projectDialogVisible = ref(false)
  const projects = ref(ProjectManager.loadProjects())
  const currentProjectName = ref('')
  const activeProjectId = ref(null)
  const operationHistory = ref(createOperationHistory(50))

  let autoSaveTimer = null

  /** 保存项目 */
  async function saveProject() {
    try {
      const projectName = currentProjectName.value || `项目_${new Date().toLocaleDateString()}`
      const projectData = {
        name: projectName,
        location: currentLocation.value,
        params: { ...generateParams },
        sites: JSON.parse(JSON.stringify(sites.value)),
        designInfo: designInfo.value
      }
      const projectId = ProjectManager.saveProject(projectData)
      activeProjectId.value = projectId
      projects.value = ProjectManager.loadProjects()
      projectDialogVisible.value = false
      ElMessage.success('项目保存成功')
      scheduleAutoSave()
    } catch (error) {
      ElMessage.error('保存失败: ' + error.message)
    }
  }

  /** 加载项目 */
  function loadProject(projectId) {
    const project = ProjectManager.loadProject(projectId)
    if (project) {
      activeProjectId.value = projectId
      currentProjectName.value = project.name
      Object.assign(generateParams, project.params)
      currentLocation.value = project.location || 'yuncheng'
      sites.value = project.sites || []
      designInfo.value = project.designInfo
      projects.value = ProjectManager.loadProjects()
      ElMessage.success('项目加载成功')
    }
  }

  /** 删除项目 */
  function deleteProject(projectId) {
    ElMessageBox.confirm('确定要删除此项目吗？', '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }).then(() => {
      ProjectManager.deleteProject(projectId)
      projects.value = ProjectManager.loadProjects()
      ElMessage.success('项目已删除')
    }).catch(() => {})
  }

  /** 自动保存 (60秒后) */
  function scheduleAutoSave() {
    if (autoSaveTimer) clearTimeout(autoSaveTimer)
    autoSaveTimer = setTimeout(() => {
      if (sites.value.length > 0) {
        saveProject()
      }
    }, 60000)
  }

  /** 导出项目 */
  function exportProject(format) {
    if (sites.value.length === 0) {
      ElMessage.warning('没有数据可导出')
      return
    }
    const exportData = buildExportData({
      location: currentLocation.value,
      generateParams,
      sites: sites.value,
      stats: stats.value
    })
    try {
      if (format === 'json') {
        exportAsJSON(exportData, `design_${Date.now()}`)
        ElMessage.success('JSON导出成功')
      } else if (format === 'csv') {
        exportAsCSV(sites.value, `sites_${Date.now()}`)
        ElMessage.success('CSV导出成功')
      } else if (format === 'geojson') {
        exportAsGeoJSON(exportData, `sites_${Date.now()}`)
        ElMessage.success('GeoJSON导出成功')
      }
    } catch (error) {
      ElMessage.error('导出失败: ' + error.message)
    }
  }

  /** 撤销 */
  function undo() {
    const prevState = operationHistory.value.undo()
    if (prevState) {
      sites.value = prevState.sites || []
      Object.assign(generateParams, prevState.params)
      ElMessage.info('已撤销')
    } else {
      ElMessage.warning('没有可撤销的操作')
    }
  }

  /** 重做 */
  function redo() {
    const nextState = operationHistory.value.redo()
    if (nextState) {
      sites.value = nextState.sites || []
      Object.assign(generateParams, nextState.params)
      ElMessage.info('已重做')
    } else {
      ElMessage.warning('没有可重做的操作')
    }
  }

  /** 清理定时器 */
  function cleanup() {
    if (autoSaveTimer) clearTimeout(autoSaveTimer)
  }

  return {
    projectDialogVisible,
    projects,
    currentProjectName,
    activeProjectId,
    operationHistory,
    saveProject,
    loadProject,
    deleteProject,
    scheduleAutoSave,
    exportProject,
    undo,
    redo,
    cleanup,
  }
}
