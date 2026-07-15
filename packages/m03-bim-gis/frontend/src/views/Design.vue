<template>
  <div class="design-visualization">
    <!-- 顶部工具栏 -->
    <div class="top-bar">
      <div class="toolbar-left">
        <el-button type="primary" @click="loadDesignData" :loading="loading" size="small">
          <el-icon><Download /></el-icon> 加载数据
        </el-button>
        <el-button type="success" @click="showSites" :loading="loading" size="small">
          <el-icon><View /></el-icon> 显示站点
        </el-button>
        <el-button-group>
          <el-button size="small" @click="generateDesign" :loading="generating" title="生成参数化设计方案">
            <el-icon><MagicStick /></el-icon> 生成方案
          </el-button>
          <el-button size="small" @click="clearSites" title="清除所有站点">
            <el-icon><Delete /></el-icon> 清除
          </el-button>
        </el-button-group>
        <el-button type="info" @click="zoomToSites" size="small">
          <el-icon><ZoomIn /></el-icon> 缩放
        </el-button>
        <el-button-group>
          <el-button size="small" @click="generateHeatmap" title="生成覆盖热力图">
            <el-icon><TrendCharts /></el-icon> 热力图
          </el-button>
          <el-button size="small" @click="clearHeatmap" title="清除热力图">
            <el-icon><Delete /></el-icon> 清除
          </el-button>
        </el-button-group>
        <el-button size="small" @click="exportMapScreenshot" title="导出当前视图为PNG图片">
          <el-icon><Download /></el-icon> 导出图片
        </el-button>
        <el-button @click="toggleAnimation" size="small">
          <el-icon><VideoPlay /></el-icon> {{ animationEnabled ? '停止' : '动画' }}
        </el-button>
      </div>
      <div class="toolbar-center">
        <el-input
          v-model="searchText"
          placeholder="搜索站点ID..."
          @keyup.enter="searchSite"
          clearable
          size="small"
          class="search-input"
          aria-label="搜索站点ID"
        >
          <template #append>
            <el-button @click="searchSite">
              <el-icon><Search /></el-icon>
            </el-button>
          </template>
        </el-input>
      </div>
      <div class="toolbar-right">
        <el-button-group size="small">
          <el-button @click="$router.push('/models')" title="模型管理">
            <el-icon><Box /></el-icon> 模型
          </el-button>
          <el-button @click="$router.push('/regions')" title="区域管理">
            <el-icon><Location /></el-icon> 区域
          </el-button>
        </el-button-group>
      </div>
    </div>

    <!-- 状态信息（左下角） -->
    <div class="status-info">
      <span class="site-count">站点: {{ siteCount }}</span>
      <span class="status-text">{{ statusText }}</span>
      <el-dropdown trigger="click" @command="handleLocationChange" class="location-dropdown">
        <span class="location-selector">
          <el-icon><Location /></el-icon>
          {{ currentLocationName }}
          <el-icon><ArrowDown /></el-icon>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="yuncheng" :disabled="currentLocation === 'yuncheng'">
              📍 运城学院 (默认)
            </el-dropdown-item>
            <el-dropdown-item command="wuhan" :disabled="currentLocation === 'wuhan'">
              📍 武汉
            </el-dropdown-item>
            <el-dropdown-item command="beijing" :disabled="currentLocation === 'beijing'">
              📍 北京
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>

    <!-- 左侧面板 -->
    <div class="left-panel">
      <!-- 参数化设计 -->
      <div class="panel-section">
        <div class="panel-title">
          <el-icon><Wand2 /></el-icon> 参数化设计
        </div>
        <div class="panel-content">
          <div class="form-item">
            <span class="form-label">模板:</span>
            <el-select v-model="generateParams.templateType" placeholder="选择模板" size="small" class="form-full-width">
              <el-option v-for="t in templates" :key="t.id" :label="t.name" :value="t.category" />
            </el-select>
          </div>
          <div class="form-item">
            <span class="form-label">中心经度:</span>
            <el-input v-model="generateParams.centerLongitude" size="small" class="form-full-width" :placeholder="DEFAULT_LOCATION.longitude.toString()" />
          </div>
          <div class="form-item">
            <span class="form-label">中心纬度:</span>
            <el-input v-model="generateParams.centerLatitude" size="small" class="form-full-width" :placeholder="DEFAULT_LOCATION.latitude.toString()" />
          </div>
          <div class="form-item">
            <span class="form-label">覆盖半径(m):</span>
            <el-input v-model="generateParams.coverageRadius" size="small" class="form-full-width" placeholder="500" />
          </div>
          <div class="form-item">
            <span class="form-label">网格大小(m):</span>
            <el-input v-model="generateParams.gridSize" size="small" class="form-full-width" placeholder="200" />
          </div>
          <div class="form-item">
            <span class="form-label">扇区数:</span>
            <el-select v-model="generateParams.sectorCount" size="small" class="form-full-width">
              <el-option label="1扇区" :value="1" />
              <el-option label="3扇区" :value="3" />
              <el-option label="6扇区" :value="6" />
            </el-select>
          </div>
          <!-- 验证错误/警告提示 -->
          <div v-if="fieldErrors.general?.length" class="validation-errors">
            <div v-for="(err, i) in fieldErrors.general" :key="'e'+i">⚠ {{ err }}</div>
          </div>
          <div v-if="fieldWarnings.general?.length" class="validation-warnings">
            <div v-for="(warn, i) in fieldWarnings.general" :key="'w'+i">⚠ {{ warn }}</div>
          </div>
          <el-button type="primary" size="small" class="form-full-width form-mt-8" @click="generateDesign" :loading="generating">
            <el-icon><RefreshRight /></el-icon> 生成方案
          </el-button>
        </div>
      </div>

      <!-- 统计信息 -->
      <div class="panel-section" v-if="stats.total > 0">
        <div class="panel-title">
          <el-icon><DataAnalysis /></el-icon> 统计信息
        </div>
        <div class="panel-content">
          <div class="info-row">
            <span class="label">总站点:</span>
            <span class="value">{{ stats.total }}</span>
          </div>
          <div class="info-row">
            <span class="label">有效:</span>
            <span class="value success">{{ stats.valid }}</span>
          </div>
          <div class="info-row">
            <span class="label">无效:</span>
            <span class="value danger">{{ stats.invalid }}</span>
          </div>
          <div class="info-row">
            <span class="label">平均RSRP:</span>
            <span class="value">{{ stats.avgRsrp }} dBm</span>
          </div>
        </div>
      </div>

      <!-- 图层控制 -->
      <div class="panel-section">
        <div class="panel-title">
          <el-icon><Layers /></el-icon> 图层控制
        </div>
        <div class="panel-content">
          <el-checkbox v-model="showSiteMarkers" @change="toggleLayer('site', showSiteMarkers)">站点标记</el-checkbox>
          <el-checkbox v-model="showConnections" @change="toggleConnections(showConnections)">管线连线</el-checkbox>
          <el-checkbox v-model="showTowers" @change="toggleLayer('tower', showTowers)">塔桅</el-checkbox>
          <el-checkbox v-model="showCoverage" @change="toggleLayer('coverage', showCoverage)">覆盖范围</el-checkbox>
          <el-checkbox v-model="showLabels" @change="toggleLayer('label', showLabels)">站点标签</el-checkbox>
          <div class="slider-row">
            <span>透明度:</span>
            <el-slider v-model="coverageOpacity" :min="0" :max="100" @change="updateCoverageOpacity" class="slider-width" />
          </div>
        </div>
      </div>

      <!-- 图例 -->
      <div class="panel-section">
        <div class="panel-title">
          <el-icon><Info /></el-icon> 图例
        </div>
        <div class="panel-content">
          <div class="legend-item" v-for="(color, index) in legendColors" :key="index" v-once>
            <span class="legend-dot" :style="{ backgroundColor: color.color }"></span>
            <span>{{ color.label }}</span>
          </div>
          <div class="legend-divider"></div>
          <div class="legend-item">
            <span class="legend-dot" style="background-color: #888;"></span>
            <span>塔桅</span>
          </div>
          <div class="legend-item">
            <span class="legend-dot" style="background-color: rgba(0,100,255,0.3);"></span>
            <span>覆盖范围</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧面板 -->
    <div class="right-panel">
      <!-- 设计信息 -->
      <div class="panel-section" v-if="designInfo">
        <div class="panel-title">
          <el-icon><Document /></el-icon> 设计信息
        </div>
        <div class="panel-content">
          <div class="info-row">
            <span class="label">项目ID:</span>
            <span class="value">{{ designInfo.projectId }}</span>
          </div>
          <div class="info-row">
            <span class="label">方案:</span>
            <span class="value">{{ designInfo.schemeName }}</span>
          </div>
          <div class="info-row">
            <span class="label">频段:</span>
            <span class="value">{{ designInfo.frequencyBand }}</span>
          </div>
          <div class="info-row">
            <span class="label">塔高:</span>
            <span class="value">{{ designInfo.towerHeight }}m</span>
          </div>
          <div class="info-row">
            <span class="label">站点:</span>
            <span class="value">{{ designInfo.totalSites }}个</span>
          </div>
          <div class="info-row">
            <span class="label">有效:</span>
            <span class="value success">{{ designInfo.validSites }}</span>
          </div>
          <div class="info-row">
            <span class="label">无效:</span>
            <span class="value danger">{{ designInfo.invalidSites }}</span>
          </div>
        </div>
      </div>

      <!-- 站点详情 -->
      <div class="panel-section" v-if="selectedSite">
        <div class="panel-title">
          <el-icon><Location /></el-icon> 站点详情
          <el-button type="text" size="small" @click="selectedSite = null" class="close-btn">
            <el-icon><Close /></el-icon>
          </el-button>
        </div>
        <div class="panel-content">
          <div class="info-row">
            <span class="label">ID:</span>
            <span class="value">{{ selectedSite.siteId }}</span>
          </div>
          <div class="info-row">
            <span class="label">坐标:</span>
            <span class="value">{{ selectedSite.longitude.toFixed(4) }}, {{ selectedSite.latitude.toFixed(4) }}</span>
          </div>
          <div class="info-row">
            <span class="label">塔高:</span>
            <span class="value">{{ selectedSite.towerHeight }}m</span>
          </div>
          <div class="info-row">
            <span class="label">RSRP:</span>
            <span class="value" :class="getRsrpClass(selectedSite.rsrp)">{{ selectedSite.rsrp }} dBm</span>
          </div>
          <div class="info-row">
            <span class="label">状态:</span>
            <el-tag :type="selectedSite.isValid === 1 ? 'success' : 'danger'" size="small">
              {{ selectedSite.isValid === 1 ? '正常' : '故障' }}
            </el-tag>
          </div>
          <div class="info-row">
            <span class="label">覆盖:</span>
            <span class="value">~1.5km</span>
          </div>
          <div class="info-row">
            <span class="label">天线:</span>
            <span class="value">3个/3扇区</span>
          </div>
          <div class="info-row">
            <span class="label">建设:</span>
            <span class="value">2026-05-20</span>
          </div>
          <div class="info-row">
            <span class="label">维护:</span>
            <span class="value">烽火通信</span>
          </div>
          <div class="action-buttons">
            <el-button type="primary" size="small" @click="flyToSite(selectedSite)">
              <el-icon><Location /></el-icon> 飞到站点
            </el-button>
            <el-button size="small" @click="showSiteCoverage(selectedSite)">
              <el-icon><View /></el-icon> 查看覆盖
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部站点列表 -->
    <div class="bottom-panel" v-if="sites.length > 0">
      <div class="panel-title">
        <el-icon><List /></el-icon> 站点列表 ({{ filteredSites.length }}/{{ sites.length }})
        <div class="list-controls">
          <el-select v-model="filterValid" size="small" class="filter-select">
            <el-option label="全部" value="all" />
            <el-option label="正常" value="valid" />
            <el-option label="故障" value="invalid" />
          </el-select>
          <el-select v-model="sortBy" size="small" class="filter-select">
            <el-option label="ID排序" value="siteId" />
            <el-option label="RSRP排序" value="rsrp" />
            <el-option label="经度排序" value="longitude" />
          </el-select>
        </div>
      </div>
      <div class="site-list-container">
        <el-button class="scroll-btn scroll-left" @click="scrollList('left')" :disabled="listScrollLeft <= 0" aria-label="向左滚动站点列表">
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <div class="site-list-scroll" ref="siteListRef">
          <div
            v-for="site in filteredSites"
            :key="site.siteId"
            v-memo="[selectedSite?.siteId === site.siteId, site.rsrp, site.isValid]"
            class="site-card"
            :class="{ active: selectedSite?.siteId === site.siteId }"
            @click="selectSite(site)"
          >
            <div class="site-card-header">
              <span class="site-id">{{ site.siteId }}</span>
              <el-tag :type="site.isValid === 1 || site.isValid === true ? 'success' : 'danger'" size="small">
                {{ site.isValid === 1 || site.isValid === true ? '正常' : '故障' }}
              </el-tag>
            </div>
            <div class="site-card-body">
              <span class="rsrp" :class="getRsrpClass(site.rsrp)">{{ site.rsrp }} dBm</span>
              <span class="coords">{{ Number(site.longitude).toFixed(2) }}, {{ Number(site.latitude).toFixed(2) }}</span>
            </div>
          </div>
        </div>
        <el-button class="scroll-btn scroll-right" @click="scrollList('right')" aria-label="向右滚动站点列表">
          <el-icon><ArrowRight /></el-icon>
        </el-button>
      </div>
    </div>

    <!-- Cesium容器 -->
    <div id="cesiumContainer" class="cesium-container"></div>

    <!-- 加载数据：项目选择弹窗（居中显眼，不默认，必须手动选择） -->
    <el-dialog
      v-model="loadProjectDialogVisible"
      title="选择要加载的项目"
      width="480px"
      align-center
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      class="load-project-dialog"
      @closed="cancelLoadProject"
    >
      <div class="load-project-body">
        <p class="load-project-tip">
          <el-icon><InfoFilled /></el-icon>
          请选择一个项目，再点击"确定"加载设计数据：
        </p>
        <el-select
          v-model="loadSelectedProjectId"
          placeholder="请选择项目"
          size="large"
          filterable
          clearable
          :loading="loadProjectListLoading"
          style="width: 100%"
        >
          <el-option
            v-for="opt in loadProjectOptions"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
        <p v-if="!loadProjectListLoading && loadProjectOptions.length === 0" class="load-project-empty">
          暂无项目，请先在 QGIS 插件中同步数据以创建项目。
        </p>
      </div>
      <template #footer>
        <el-button @click="cancelLoadProject">取消</el-button>
        <el-button
          type="primary"
          :disabled="!loadSelectedProjectId"
          @click="confirmLoadProject"
        >确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
export default { name: 'DesignView' }
</script>
<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import * as Cesium from 'cesium'
import { createViewer } from '@/composables/useCesiumCore.js'
import { ElMessage, ElMessageBox } from 'element-plus'
import { DEFAULT_LOCATION, getPresetLocation } from '@/config/location.js'
import { registerDefaultShortcuts, shortcutManager } from '@/utils/shortcutManager.js'
import { useDesignState } from '@/composables/useDesignState.js'
import { useSiteManager, LEGEND_COLORS } from '@/composables/useSiteManager.js'
import { useProjectManager } from '@/composables/useProjectManager.js'
import { useCoverageAnalysis } from '@/composables/useCoverageAnalysis.js'
import { logger } from '@/utils/logger.js'

// ── 共享状态 ──────────────────────────────────────────────
const viewer = ref(null)
const siteListRef = ref(null)
const listScrollLeft = ref(0)
const _timers = []
const coverageOpacity = ref(15)
const designInfo = ref(null)
const currentLocation = ref('yuncheng')

// 共享响应式参数 (供 designState 和 projectManager 共同使用)
const generateParams = reactive({
  templateType: 'macro',
  centerLongitude: DEFAULT_LOCATION.longitude.toString(),
  centerLatitude: DEFAULT_LOCATION.latitude.toString(),
  coverageRadius: DEFAULT_LOCATION.defaultCoverageRadius.toString(),
  gridSize: DEFAULT_LOCATION.defaultGridSize.toString(),
  sectorCount: DEFAULT_LOCATION.defaultSectorCount
})

/** Safe setTimeout that gets cleaned up on unmount */
const _safeSetTimeout = (fn, delay) => {
  const id = setTimeout(() => {
    const idx = _timers.indexOf(id)
    if (idx > -1) _timers.splice(idx, 1)
    fn()
  }, delay)
  _timers.push(id)
  return id
}

// ── 组合式函数初始化 ──────────────────────────────────────
// 1. 站点管理 (提供 sites 给其他模块)
const {
  sites, selectedSite, siteCount, searchText, filterValid, sortBy,
  filteredSites, stats,
  showConnections,
  addSitesToMap, bindClickHandler, deleteSite, removeSiteEntities,
  clearSites, zoomToSites, selectSite, highlightSite,
  flyToSite, showSiteCoverage, searchSite, getRsrpClass,
  drawConnections, setHubPoint, clearConnections, toggleConnections, cleanupEntities,
} = useSiteManager({ viewer, coverageOpacity })

// 2. 覆盖分析 (依赖 viewer 和 sites)
// T8: 将 QGIS 设计的射频参数（频段/覆盖半径/场景）下发给 3D 热力图，强化 QGIS↔3D 同步
const frequencyMHz = computed(() => {
  const band = designInfo.value?.frequencyBand
  if (!band) return 2100
  const map = {
    'fdd-lte-800': 850, 'fdd-lte-900': 900, 'fdd-lte-1800': 1800,
    'tdd-lte-2300': 2300, 'tdd-lte-2600': 2600, '5g-n79': 4900, '5g-n41': 2500,
    '700mhz': 700, '3.5ghz': 3500, '2.1ghz': 2100,
  }
  return map[band.toLowerCase()] || 2100
})

const {
  showSiteMarkers, showTowers, showCoverage, showLabels,
  animationEnabled, coverageMetrics, coverageGaps,
  showCoverageReport, generateHeatmap, clearHeatmap, exportMapScreenshot,
  toggleLayer, updateCoverageOpacity, toggleAnimation, cleanupAnimation,
} = useCoverageAnalysis({
  viewer, sites, coverageOpacity,
  frequencyMHz: frequencyMHz.value,
  coverageRadius: Number(generateParams.coverageRadius) || 500,
  environment: 'URBAN',
})

// 3. 项目管理 (先于 designState 初始化，提供 operationHistory)
const {
  projectDialogVisible, projects, currentProjectName, activeProjectId,
  operationHistory,
  saveProject, loadProject, deleteProject, scheduleAutoSave,
  exportProject, undo, redo, cleanup: cleanupProject,
} = useProjectManager({
  sites, generateParams, designInfo, currentLocation, stats,
  clearSites, addSitesToMap, zoomToSites,
})

// 4. 设计状态 (依赖 viewer, sites, siteCount, operationHistory, generateParams)
const {
  currentLocationName, loading, generating,
  statusText, currentSchemeId, templates, fieldErrors, fieldWarnings,
  updateLocation, handleLocationChange, validateFields, promptProjectId,
  loadDesignData, showSites, loadTemplates, generateDesign,
  loadProjectDialogVisible, loadProjectOptions, loadSelectedProjectId,
  loadProjectListLoading, confirmLoadProject, cancelLoadProject,
} = useDesignState({
  viewer, sites, siteCount, generateParams, designInfo, currentLocation,
  clearSites, addSitesToMap, zoomToSites, operationHistory, _safeSetTimeout,
  setHubPoint,
})

// ── 图例颜色 ──────────────────────────────────────────────
const legendColors = LEGEND_COLORS

// ── 快捷键帮助 ────────────────────────────────────────────
const showShortcutHelp = () => {
  shortcutManager.showHelp((message, options = {}) => {
    ElMessageBox.alert(message, '快捷键列表', {
      confirmButtonText: '知道了',
      ...options
    })
  })
}

// ── 滚动站点列表 ──────────────────────────────────────────
const scrollList = (direction) => {
  if (!siteListRef.value) return
  const scrollAmount = 200
  if (direction === 'left') {
    siteListRef.value.scrollLeft -= scrollAmount
  } else {
    siteListRef.value.scrollLeft += scrollAmount
  }
  listScrollLeft.value = siteListRef.value.scrollLeft
}

// ── 初始化 Cesium ─────────────────────────────────────────
const initCesium = () => {
  try {
    viewer.value = createViewer('cesiumContainer', {
      animation: false,
      timeline: false,
      baseLayerPicker: false,
      fullscreenButton: false,
      vrButton: false,
      geocoder: false,
      homeButton: true,
      infoBox: true,
      sceneModePicker: false,
      selectionIndicator: true,
      navigationHelpButton: false,
      navigationInstructionsInitiallyVisible: false
    })

    const config = getPresetLocation(currentLocation.value)
    viewer.value.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(
        config.longitude, config.latitude, DEFAULT_LOCATION.cameraHeight
      )
    })

    statusText.value = '就绪'
  } catch (error) {
    logger.error('Design', 'Cesium初始化失败', error)
    statusText.value = '初始化失败'
  }
}

// ── 生命周期 ──────────────────────────────────────────────
onMounted(() => {
  initCesium()
  loadTemplates()

  registerDefaultShortcuts({
    generateDesign, clearSites, zoomToSites, undo, redo,
    toggleLayer, handleLocationChange, showShortcutHelp
  })

  ElMessage.info({
    message: '按 ? 查看快捷键 | 生成方案前请校验参数',
    duration: 5000
  })
})

onUnmounted(() => {
  // 清理定时器
  _timers.forEach(id => clearTimeout(id))
  _timers.length = 0
  cleanupProject()

  // 清理动画事件
  cleanupAnimation()

  // 清理站点实体
  cleanupEntities()

  // 销毁 Viewer
  if (viewer.value) {
    viewer.value.destroy()
    viewer.value = null
  }

  // 销毁快捷键管理器
  shortcutManager.destroy()
})
</script>

<!-- 非scoped: CSS自定义属性必须设在 :root 上，scoped会给选择器加 [data-v-xxx]
     导致 :root[data-v-xxx] 永远不匹配 <html>，变量全部失效 -->
<style>
/* ── 全局CSS变量（布局尺寸） ──────────────────────────────── */
:root {
  --panel-left-width: 240px;
  --panel-right-width: 240px;
  --panel-bottom-height: 160px;
  --panel-top-offset: 60px;
}
@media (max-width: 1366px) {
  :root {
    --panel-left-width: 210px;
    --panel-right-width: 200px;
    --panel-bottom-height: 130px;
  }
}
@media (max-width: 1024px) {
  :root {
    --panel-left-width: 0px;
    --panel-right-width: 0px;
    --panel-bottom-height: 120px;
  }
}

/* ── 加载数据：项目选择弹窗（居中显眼） ─────────────────── */
.load-project-dialog .el-dialog__title {
  font-weight: 600;
}
.load-project-body {
  padding: 4px 2px;
}
.load-project-tip {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0 0 14px;
  font-size: 14px;
  color: var(--el-text-color-regular, #606266);
}
.load-project-tip .el-icon {
  color: var(--el-color-primary, #409eff);
  font-size: 16px;
}
.load-project-empty {
  margin: 12px 0 0;
  font-size: 13px;
  color: var(--el-color-warning, #e6a23c);
}
</style>

<style scoped>
/* ================================================================
   M03 Design View — 暗色科技主题 (统一 global.css 设计系统)
   ================================================================ */

.design-visualization {
  width: 100%;
  height: 100%;
  position: relative;
  font-family: var(--font-sans, 'Microsoft YaHei', sans-serif);
}

/* ── 响应式布局变量（已移至非scoped style块的 :root 中） ──── */

/* ── 顶部工具栏 ──────────────────────────────────────────── */
.top-bar {
  position: absolute;
  top: 0;
  left: 0;
  right: 150px;
  z-index: 1000;
  background: var(--bg-glass, rgba(10, 15, 26, 0.92));
  padding: 6px 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--border-color, rgba(0, 212, 255, 0.15));
  border-radius: 0 0 8px 0;
}

.toolbar-left {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.toolbar-center {
  flex: 1;
  display: flex;
  justify-content: center;
}

.toolbar-right {
  display: flex;
  gap: 12px;
  align-items: center;
  color: var(--text-primary, #fff);
  font-size: 12px;
}

/* ── 状态信息 ────────────────────────────────────────────── */
.status-info {
  position: absolute;
  bottom: 12px;
  left: calc(var(--panel-left-width) + 20px);
  z-index: 1000;
  background: var(--bg-glass, rgba(10, 15, 26, 0.85));
  color: var(--text-primary, #fff);
  padding: 6px 12px;
  border-radius: var(--radius-sm, 4px);
  font-size: 12px;
  display: flex;
  gap: 15px;
  border: 1px solid var(--border-color, rgba(0, 212, 255, 0.12));
}

.site-count {
  background: var(--primary-color, #00d4ff);
  color: #0a0f1a;
  padding: 2px 8px;
  border-radius: var(--radius-sm, 4px);
  font-weight: 600;
}

.status-text {
  color: var(--text-muted, #7f8c8d);
}

/* ── 位置选择器 ──────────────────────────────────────────── */
.location-selector {
  background: rgba(72, 149, 239, 0.25);
  padding: 2px 10px;
  border-radius: var(--radius-sm, 4px);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: var(--text-primary, #fff);
  transition: all 0.3s;
  border: 1px solid rgba(72, 149, 239, 0.3);
}

.location-selector:hover {
  background: rgba(72, 149, 239, 0.4);
  border-color: rgba(72, 149, 239, 0.6);
  transform: scale(1.05);
}

/* ── 面板布局 (响应式) ───────────────────────────────────── */
.left-panel {
  position: absolute;
  top: var(--panel-top-offset);
  left: 10px;
  bottom: 10px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 8px;          /* 区块间距压缩 */
  width: var(--panel-left-width);
  overflow-y: auto;
  padding: 0 4px 8px 0; /* 上边距由 top 控制 */
  /* 细滚动条 */
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 212, 255, 0.3) transparent;
}

.right-panel {
  position: absolute;
  top: var(--panel-top-offset);
  right: 10px;
  bottom: 10px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: var(--panel-right-width);
  overflow-y: auto;
  padding-right: 4px;
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 212, 255, 0.3) transparent;
}

/* ── WebKit 细滚动条（Chrome / Edge） ─────────────────────── */
.left-panel::-webkit-scrollbar,
.right-panel::-webkit-scrollbar {
  width: 4px;
}
.left-panel::-webkit-scrollbar-track,
.right-panel::-webkit-scrollbar-track {
  background: transparent;
}
.left-panel::-webkit-scrollbar-thumb,
.right-panel::-webkit-scrollbar-thumb {
  background: rgba(0, 212, 255, 0.3);
  border-radius: 2px;
}
.left-panel::-webkit-scrollbar-thumb:hover,
.right-panel::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 212, 255, 0.5);
}

/* ── 面板通用 — 暗色主题（紧凑版） ───────────────────────── */
.panel-section {
  background: var(--bg-glass, rgba(10, 15, 26, 0.92));
  border: 1px solid var(--border-color, rgba(0, 212, 255, 0.12));
  border-radius: var(--radius-md, 6px);   /* 圆角微缩 */
  box-shadow: var(--shadow-md, 0 2px 8px rgba(0, 0, 0, 0.3));
  overflow: hidden;
  backdrop-filter: blur(8px);
}

.panel-title {
  background: var(--bg-tertiary, #1a2a4a);
  color: var(--primary-color, #00d4ff);
  padding: 6px 10px;       /* 压缩：8→6 */
  font-size: 12px;         /* 压缩：13→12 */
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 5px;               /* 压缩：6→5 */
  border-bottom: 1px solid var(--border-glow, rgba(0, 212, 255, 0.18));
}

.panel-content {
  padding: 8px 10px;       /* 压缩：10→8, 12→10 */
  color: var(--text-secondary, #b0bec5);
}

/* ── 图层控制（紧凑） ────────────────────────────────────── */
.panel-content .el-checkbox {
  display: block;
  margin-bottom: 4px;       /* 压缩：6→4 */
  font-size: 12px;
}

.slider-row {
  display: flex;
  align-items: center;
  gap: 6px;                /* 压缩：8→6 */
  margin-top: 6px;         /* 压缩：8→6 */
  font-size: 11px;         /* 压缩：12→11 */
  color: var(--text-secondary, #b0bec5);
}

/* ── 参数化设计表单（紧凑） ──────────────────────────────── */
.form-item {
  margin-bottom: 6px;      /* 压缩：8→6 */
}

.form-label {
  font-size: 11px;         /* 保持紧凑 */
  color: var(--text-muted, #7f8c8d);
  display: block;
  margin-bottom: 2px;      /* 压缩：4→2 */
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ── 验证错误提示（紧凑） ────────────────────────────────── */
.validation-errors {
  background: rgba(245, 108, 108, 0.12);
  border: 1px solid var(--danger-color, #f56c6c);
  border-radius: var(--radius-sm, 4px);
  padding: 5px 8px;        /* 压缩 */
  margin: 6px 0;
  font-size: 10px;
  color: var(--danger-color, #f56c6c);
  line-height: 1.5;
}

.validation-warnings {
  background: rgba(230, 162, 60, 0.12);
  border: 1px solid var(--warning-color, #e6a23c);
  border-radius: var(--radius-sm, 4px);
  padding: 5px 8px;
  margin: 6px 0;
  font-size: 10px;
  color: var(--warning-color, #e6a23c);
  line-height: 1.5;
}

/* ── 图例（紧凑） ────────────────────────────────────────── */
.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;                /* 压缩：8→6 */
  margin-bottom: 4px;      /* 压缩：6→4 */
  font-size: 11px;         /* 压缩：12→11 */
  color: var(--text-primary, #fff);
}

.legend-dot {
  width: 12px;             /* 压缩：14→12 */
  height: 12px;
  border-radius: 2px;      /* 压缩：3→2 */
  border: 1px solid var(--border-color, rgba(0, 212, 255, 0.2));
  flex-shrink: 0;
}

.legend-divider {
  height: 1px;
  background: var(--border-color, rgba(0, 212, 255, 0.12));
  margin: 5px 0;           /* 压缩：8→5 */
}

/* ── 信息行（紧凑） ──────────────────────────────────────── */
.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;      /* 压缩：6→4 */
  font-size: 11px;         /* 压缩：12→11 */
}

.info-row .label {
  color: var(--text-muted, #7f8c8d);
}

.info-row .value {
  color: var(--text-primary, #fff);
  font-weight: 500;
}

.info-row .value.success {
  color: var(--success-color, #67c23a);
}

.info-row .value.danger {
  color: var(--danger-color, #f56c6c);
}

/* ── RSRP 颜色 ───────────────────────────────────────────── */
.rsrp-excellent { color: #00cc00 !important; font-weight: bold; }
.rsrp-good      { color: #aacc00 !important; }
.rsrp-fair      { color: #ff8800 !important; }
.rsrp-poor      { color: #ff3333 !important; font-weight: bold; }

/* ── 操作按钮 ────────────────────────────────────────────── */
.action-buttons {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

.close-btn {
  margin-left: auto;
  color: var(--text-primary, #fff);
}

/* ── 底部站点列表 ────────────────────────────────────────── */
.bottom-panel {
  position: absolute;
  bottom: 10px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1000;
  background: var(--bg-glass, rgba(10, 15, 26, 0.92));
  border: 1px solid var(--border-color, rgba(0, 212, 255, 0.12));
  border-radius: var(--radius-md, 8px);
  box-shadow: var(--shadow-md, 0 4px 16px rgba(0, 0, 0, 0.3));
  width: min(650px, calc(100vw - var(--panel-left-width) - var(--panel-right-width) - 40px));
  max-height: var(--panel-bottom-height);
  backdrop-filter: blur(8px);
}

.bottom-panel .panel-title {
  padding: 6px 12px;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.list-controls {
  display: flex;
  gap: 4px;
}

.site-list-container {
  display: flex;
  align-items: center;
  padding: 8px;
  gap: 4px;
}

.scroll-btn {
  width: 30px;
  height: 60px;
  padding: 0;
  flex-shrink: 0;
}

.scroll-left  { border-radius: 4px 0 0 4px; }
.scroll-right { border-radius: 0 4px 4px 0; }

.site-list-scroll {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  max-height: 100px;
  flex: 1;
  scroll-behavior: smooth;
}

.site-list-scroll::-webkit-scrollbar { height: 6px; }
.site-list-scroll::-webkit-scrollbar-thumb {
  background: var(--border-color, rgba(0, 212, 255, 0.2));
  border-radius: 3px;
}
.site-list-scroll::-webkit-scrollbar-track {
  background: var(--bg-secondary, #0d1b2a);
  border-radius: 3px;
}

.site-card {
  min-width: 120px;
  padding: 6px 10px;
  background: var(--bg-secondary, #0d1b2a);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid var(--border-color, rgba(0, 212, 255, 0.1));
}

.site-card:hover {
  background: var(--bg-tertiary, #1a2a4a);
  border-color: var(--primary-color, #00d4ff);
  box-shadow: var(--shadow-glow, 0 0 8px rgba(0, 212, 255, 0.2));
}

.site-card.active {
  background: var(--bg-tertiary, #1a2a4a);
  border-color: var(--primary-color, #00d4ff);
  box-shadow: var(--shadow-glow, 0 0 12px rgba(0, 212, 255, 0.3));
}

.site-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.site-id {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary, #fff);
}

.site-card-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.rsrp {
  font-size: 11px;
  font-weight: 500;
}

.coords {
  font-size: 10px;
  color: var(--text-muted, #7f8c8d);
}

/* ── 布局辅助类 ──────────────────────────────────────────── */
.form-full-width { width: 100%; }
.form-mt-8 { margin-top: 6px; }   /* 压缩：8→6 */
.search-input { width: 200px; }
.filter-select { width: 80px; }
.slider-width { width: 100px; }
.location-dropdown { margin-left: 10px; }

/* ── Cesium容器 ──────────────────────────────────────────── */
.cesium-container {
  width: 100%;
  height: 100%;
}

/* ── 响应式（:root 变量已移至非scoped style块） ─────────── */
@media (max-width: 1024px) {
  .left-panel, .right-panel { display: none; }
}
</style>
