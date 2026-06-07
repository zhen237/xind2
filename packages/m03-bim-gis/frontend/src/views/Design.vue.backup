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
        <el-button type="warning" @click="clearSites" size="small">
          <el-icon><Delete /></el-icon> 清除
        </el-button>
        <el-button type="info" @click="zoomToSites" size="small">
          <el-icon><ZoomIn /></el-icon> 缩放
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
          style="width: 200px;"
        >
          <template #append>
            <el-button @click="searchSite">
              <el-icon><Search /></el-icon>
            </el-button>
          </template>
        </el-input>
      </div>
      <div class="toolbar-right">
        <!-- 留空，让出右上角给Cesium控件 -->
      </div>
    </div>

    <!-- 状态信息（左下角） -->
    <div class="status-info">
      <span class="site-count">站点: {{ siteCount }}</span>
      <span class="status-text">{{ statusText }}</span>
    </div>

    <!-- 左侧面板 -->
    <div class="left-panel">
      <!-- 图层控制 -->
      <div class="panel-section">
        <div class="panel-title">
          <el-icon><Layers /></el-icon> 图层控制
        </div>
        <div class="panel-content">
          <el-checkbox v-model="showSiteMarkers" @change="toggleLayer('site', showSiteMarkers)">站点标记</el-checkbox>
          <el-checkbox v-model="showTowers" @change="toggleLayer('tower', showTowers)">塔桅</el-checkbox>
          <el-checkbox v-model="showCoverage" @change="toggleLayer('coverage', showCoverage)">覆盖范围</el-checkbox>
          <el-checkbox v-model="showLabels" @change="toggleLayer('label', showLabels)">站点标签</el-checkbox>
          <div class="slider-row">
            <span>透明度:</span>
            <el-slider v-model="coverageOpacity" :min="0" :max="100" @change="updateCoverageOpacity" style="width: 100px;" />
          </div>
        </div>
      </div>

      <!-- 图例 -->
      <div class="panel-section">
        <div class="panel-title">
          <el-icon><Info /></el-icon> 图例
        </div>
        <div class="panel-content">
          <div class="legend-item" v-for="(color, index) in legendColors" :key="index">
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
        <el-icon><List /></el-icon> 站点列表 ({{ sites.length }})
      </div>
      <div class="site-list-container">
        <el-button class="scroll-btn scroll-left" @click="scrollList('left')" :disabled="listScrollLeft <= 0">
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <div class="site-list-scroll" ref="siteListRef">
          <div
            v-for="site in sites"
            :key="site.siteId"
            class="site-card"
            :class="{ active: selectedSite?.siteId === site.siteId }"
            @click="selectSite(site)"
          >
            <div class="site-card-header">
              <span class="site-id">{{ site.siteId }}</span>
              <el-tag :type="site.isValid === 1 ? 'success' : 'danger'" size="small">
                {{ site.isValid === 1 ? '正常' : '故障' }}
              </el-tag>
            </div>
            <div class="site-card-body">
              <span class="rsrp" :class="getRsrpClass(site.rsrp)">{{ site.rsrp }} dBm</span>
              <span class="coords">{{ site.longitude.toFixed(2) }}, {{ site.latitude.toFixed(2) }}</span>
            </div>
          </div>
        </div>
        <el-button class="scroll-btn scroll-right" @click="scrollList('right')">
          <el-icon><ArrowRight /></el-icon>
        </el-button>
      </div>
    </div>

    <!-- 站点详情弹窗（可拖动） -->
    <div
      class="site-detail-popup"
      v-if="selectedSite && showDetailPopup"
      :style="{ left: detailPosition.x + 'px', top: detailPosition.y + 'px' }"
      @mousedown="startDrag"
    >
      <div class="popup-header">
        <span>{{ selectedSite.siteId }} - 详细信息</span>
        <el-button type="text" size="small" @click="showDetailPopup = false">
          <el-icon><Close /></el-icon>
        </el-button>
      </div>
      <div class="popup-content">
        <div class="detail-grid">
          <div class="detail-item">
            <span class="label">站点名称:</span>
            <span>{{ selectedSite.siteName || '未命名' }}</span>
          </div>
          <div class="detail-item">
            <span class="label">站点类型:</span>
            <span>{{ selectedSite.siteType || '宏站' }}</span>
          </div>
          <div class="detail-item">
            <span class="label">场景:</span>
            <span>{{ selectedSite.scenario || '城市' }}</span>
          </div>
          <div class="detail-item">
            <span class="label">海拔:</span>
            <span>约20米</span>
          </div>
          <div class="detail-item">
            <span class="label">覆盖半径:</span>
            <span>~1.5公里</span>
          </div>
          <div class="detail-item">
            <span class="label">天线数量:</span>
            <span>3个</span>
          </div>
          <div class="detail-item">
            <span class="label">扇区数:</span>
            <span>3扇区</span>
          </div>
          <div class="detail-item">
            <span class="label">建设时间:</span>
            <span>2026-05-20</span>
          </div>
          <div class="detail-item">
            <span class="label">维护单位:</span>
            <span>烽火通信</span>
          </div>
          <div class="detail-item">
            <span class="label">最后巡检:</span>
            <span>2026-06-01</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Cesium容器 -->
    <div id="cesiumContainer" class="cesium-container"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, reactive } from 'vue'
import * as Cesium from 'cesium'
import axios from 'axios'
import { ElMessage } from 'element-plus'

// 设计信息
const designInfo = ref(null)

// Cesium Viewer
let viewer = null

// 站点数据
const sites = ref([])

// 站点实体集合
let siteEntities = []

// 选中的站点
const selectedSite = ref(null)

// 站点数量
const siteCount = ref(0)

// 站点列表滚动
const siteListRef = ref(null)
const listScrollLeft = ref(0)

// 状态文本
const statusText = ref('就绪')

// 加载状态
const loading = ref(false)

// 搜索文本
const searchText = ref('')

// 动画状态
const animationEnabled = ref(false)

// 图层控制
const showSiteMarkers = ref(true)
const showTowers = ref(true)
const showCoverage = ref(true)
const showLabels = ref(true)

// 覆盖透明度
const coverageOpacity = ref(15)

// 详情弹窗
const showDetailPopup = ref(false)
const detailPosition = reactive({ x: 400, y: 200 })

// 拖动状态
const isDragging = ref(false)
const dragOffset = reactive({ x: 0, y: 0 })

// API地址
const API_BASE_URL = 'http://localhost:8083'

// 颜色数组
const COLORS = [
  Cesium.Color.fromCssColorString('#00ff00'),
  Cesium.Color.fromCssColorString('#0088ff'),
  Cesium.Color.fromCssColorString('#ffff00'),
  Cesium.Color.fromCssColorString('#ff8800'),
  Cesium.Color.fromCssColorString('#ff00ff'),
  Cesium.Color.fromCssColorString('#00ffff'),
  Cesium.Color.fromCssColorString('#ff0000'),
  Cesium.Color.fromCssColorString('#8800ff')
]

// 图例颜色
const legendColors = [
  { color: '#00ff00', label: '站点 1-4' },
  { color: '#0088ff', label: '站点 5-8' },
  { color: '#ffff00', label: '站点 9-12' },
  { color: '#ff8800', label: '站点 13-16' }
]

// 初始化Cesium
onMounted(() => {
  initCesium()
  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
})

onUnmounted(() => {
  if (viewer) {
    viewer.destroy()
    viewer = null
  }
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
})

// 初始化Cesium
const initCesium = () => {
  try {
    // 使用Cesium默认配置，包含Bing Maps底图
    viewer = new Cesium.Viewer('cesiumContainer', {
      animation: false,
      timeline: false,
      baseLayerPicker: true,  // 启用底图选择器
      fullscreenButton: false,
      vrButton: false,
      geocoder: false,
      homeButton: true,
      infoBox: false,
      sceneModePicker: false,  // 禁用场景模式选择器，节省空间
      selectionIndicator: true,
      navigationHelpButton: false,
      navigationInstructionsInitiallyVisible: false
    })

    // 飞到武汉光谷
    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(114.39, 30.506, 50000)
    })

    // 添加点击事件
    viewer.screenSpaceEventHandler.setInputAction((click) => {
      const picked = viewer.scene.pick(click.position)
      if (Cesium.defined(picked) && picked.id) {
        const entity = picked.id
        if (entity.id && entity.id.startsWith('site_')) {
          const siteId = entity.id.replace('site_', '')
          const site = sites.value.find(s => s.siteId === siteId)
          if (site) {
            selectSite(site)
          }
        }
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK)

    statusText.value = '就绪'
  } catch (error) {
    console.error('Cesium初始化失败:', error)
    statusText.value = '初始化失败'
  }
}

// 开始拖动
const startDrag = (e) => {
  isDragging.value = true
  dragOffset.x = e.clientX - detailPosition.x
  dragOffset.y = e.clientY - detailPosition.y
}

// 拖动中
const onDrag = (e) => {
  if (isDragging.value) {
    detailPosition.x = e.clientX - dragOffset.x
    detailPosition.y = e.clientY - dragOffset.y
  }
}

// 停止拖动
const stopDrag = () => {
  isDragging.value = false
}

// 获取RSRP样式类
const getRsrpClass = (rsrp) => {
  if (rsrp > -80) return 'rsrp-excellent'
  if (rsrp > -90) return 'rsrp-good'
  if (rsrp > -100) return 'rsrp-fair'
  return 'rsrp-poor'
}

// 加载设计数据
const loadDesignData = async () => {
  try {
    loading.value = true
    statusText.value = '加载中...'
    const response = await axios.get(`${API_BASE_URL}/api/m03/design/101`)
    if (response.data.code === 200) {
      designInfo.value = response.data.data
      statusText.value = '数据已加载'
      ElMessage.success('设计数据加载成功')
    } else {
      ElMessage.error('加载失败')
    }
  } catch (error) {
    ElMessage.error('加载错误: ' + error.message)
  } finally {
    loading.value = false
  }
}

// 显示站点
const showSites = async () => {
  try {
    loading.value = true
    statusText.value = '加载站点...'
    clearSites()

    const response = await axios.get(`${API_BASE_URL}/api/m03/design/9/sites`)
    if (response.data.code === 200) {
      sites.value = response.data.data
      siteCount.value = sites.value.length
      addSitesToMap()
      statusText.value = `${sites.value.length}个站点`
      ElMessage.success(`显示 ${sites.value.length} 个站点`)

      setTimeout(() => zoomToSites(), 1000)
    } else {
      ElMessage.error('获取站点失败')
    }
  } catch (error) {
    ElMessage.error('错误: ' + error.message)
  } finally {
    loading.value = false
  }
}

// 添加站点到地图
const addSitesToMap = () => {
  sites.value.forEach((site, index) => {
    const color = COLORS[index % COLORS.length]
    const lon = Number(site.longitude)
    const lat = Number(site.latitude)
    const height = Number(site.towerHeight) || 45

    if (isNaN(lon) || isNaN(lat)) return

    // 站点标记
    siteEntities.push(viewer.entities.add({
      id: `site_${site.siteId}`,
      position: Cesium.Cartesian3.fromDegrees(lon, lat, 0),
      point: { pixelSize: 20, color: color, outlineColor: Cesium.Color.WHITE, outlineWidth: 3 }
    }))

    // 标签
    siteEntities.push(viewer.entities.add({
      id: `label_${site.siteId}`,
      position: Cesium.Cartesian3.fromDegrees(lon, lat, 0),
      label: {
        text: site.siteId,
        font: '14px sans-serif',
        fillColor: Cesium.Color.WHITE,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        outlineWidth: 2,
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        pixelOffset: new Cesium.Cartesian2(0, -30),
        disableDepthTestDistance: Number.POSITIVE_INFINITY
      }
    }))

    // 塔桅
    siteEntities.push(viewer.entities.add({
      id: `tower_${site.siteId}`,
      position: Cesium.Cartesian3.fromDegrees(lon, lat, height / 2),
      cylinder: { length: height, topRadius: 1.5, bottomRadius: 3, material: Cesium.Color.GRAY.withAlpha(0.9) }
    }))

    // 覆盖范围
    siteEntities.push(viewer.entities.add({
      id: `coverage_${site.siteId}`,
      position: Cesium.Cartesian3.fromDegrees(lon, lat, height / 2),
      ellipsoid: {
        radii: new Cesium.Cartesian3(1500, 1500, 800),
        material: color.withAlpha(coverageOpacity.value / 100),
        outline: true,
        outlineColor: color.withAlpha(0.5)
      }
    }))
  })
}

// 清除站点
const clearSites = () => {
  siteEntities.forEach(entity => viewer.entities.remove(entity))
  siteEntities = []
  sites.value = []
  siteCount.value = 0
  selectedSite.value = null
  showDetailPopup.value = false
  statusText.value = '已清除'
}

// 缩放到站点
const zoomToSites = () => {
  if (!viewer || siteEntities.length === 0) return

  try {
    const entityCollection = new Cesium.EntityCollection()
    siteEntities.forEach(entity => entityCollection.add(entity))
    viewer.zoomTo(entityCollection)
    statusText.value = '已缩放'
  } catch (error) {
    console.error('缩放失败:', error)
  }
}

// 选择站点
const selectSite = (site) => {
  selectedSite.value = site
  showDetailPopup.value = true
  highlightSite(site.siteId)
}

// 高亮站点
const highlightSite = (siteId) => {
  siteEntities.forEach(entity => {
    if (entity.id?.startsWith('site_')) {
      entity.point.pixelSize = 20
      entity.point.outlineWidth = 3
    }
  })

  const siteEntity = siteEntities.find(e => e.id === `site_${siteId}`)
  if (siteEntity) {
    siteEntity.point.pixelSize = 30
    siteEntity.point.outlineWidth = 5
  }
}

// 飞到站点
const flyToSite = (site) => {
  viewer.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(Number(site.longitude), Number(site.latitude), 5000),
    duration: 2
  })
}

// 显示站点覆盖
const showSiteCoverage = (site) => {
  viewer.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(Number(site.longitude), Number(site.latitude), 10000),
    duration: 2
  })
}

// 搜索站点
const searchSite = () => {
  if (!searchText.value) {
    ElMessage.warning('请输入站点ID')
    return
  }

  const site = sites.value.find(s =>
    s.siteId.toLowerCase().includes(searchText.value.toLowerCase())
  )

  if (site) {
    selectSite(site)
    flyToSite(site)
    ElMessage.success(`找到: ${site.siteId}`)
  } else {
    ElMessage.warning('未找到')
  }
}

// 切换图层
const toggleLayer = (layerType, visible) => {
  siteEntities.forEach(entity => {
    if (entity.id?.startsWith(`${layerType}_`)) {
      entity.show = visible
    }
  })
}

// 更新覆盖透明度
const updateCoverageOpacity = (opacity) => {
  siteEntities.forEach(entity => {
    if (entity.id?.startsWith('coverage_')) {
      entity.ellipsoid.material = entity.ellipsoid.material.color.getValue().withAlpha(opacity / 100)
    }
  })
}

// 切换动画
const toggleAnimation = () => {
  animationEnabled.value = !animationEnabled.value
  if (animationEnabled.value) {
    viewer.clock.onTick.addEventListener(rotateCamera)
    statusText.value = '动画中'
  } else {
    viewer.clock.onTick.removeEventListener(rotateCamera)
    statusText.value = '已停止'
  }
}

// 旋转相机
const rotateCamera = (clock) => {
  viewer.scene.camera.rotateRight(0.01)
}

// 滚动站点列表
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
</script>

<style scoped>
.design-visualization {
  width: 100%;
  height: 100%;
  position: relative;
  font-family: 'Microsoft YaHei', sans-serif;
}

/* 顶部工具栏 */
.top-bar {
  position: absolute;
  top: 0;
  left: 0;
  right: 150px;  /* 右边留出空间给Cesium控件 */
  z-index: 1000;
  background: rgba(30, 30, 30, 0.9);
  padding: 8px 15px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  backdrop-filter: blur(10px);
  border-radius: 0 0 8px 0;
}

.toolbar-left {
  display: flex;
  gap: 8px;
}

.toolbar-center {
  flex: 1;
  display: flex;
  justify-content: center;
}

.toolbar-right {
  display: flex;
  gap: 15px;
  align-items: center;
  color: #fff;
  font-size: 12px;
}

/* 状态信息 */
.status-info {
  position: absolute;
  bottom: 160px;
  left: 10px;
  z-index: 1000;
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 12px;
  display: flex;
  gap: 15px;
}

.site-count {
  background: rgba(102, 126, 234, 0.8);
  padding: 2px 8px;
  border-radius: 4px;
}

.status-text {
  color: #aaa;
}

/* 左侧面板 */
.left-panel {
  position: absolute;
  top: 50px;
  left: 10px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 180px;
}

/* 右侧面板 */
.right-panel {
  position: absolute;
  top: 50px;
  right: 10px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 220px;
}

/* 面板通用样式 */
.panel-section {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
  overflow: hidden;
}

.panel-title {
  background: #2c3e50;
  color: white;
  padding: 8px 12px;
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
}

.panel-content {
  padding: 10px 12px;
}

/* 图层控制 */
.panel-content .el-checkbox {
  display: block;
  margin-bottom: 6px;
  font-size: 12px;
}

.slider-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  font-size: 12px;
  color: #666;
}

/* 图例 */
.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 12px;
  color: #333;
}

.legend-dot {
  width: 14px;
  height: 14px;
  border-radius: 3px;
  border: 1px solid #ddd;
  flex-shrink: 0;
}

.legend-divider {
  height: 1px;
  background: #eee;
  margin: 8px 0;
}

/* 信息行 */
.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  font-size: 12px;
}

.info-row .label {
  color: #999;
}

.info-row .value {
  color: #333;
  font-weight: 500;
}

.info-row .value.success {
  color: #67c23a;
}

.info-row .value.danger {
  color: #f56c6c;
}

/* RSRP颜色 */
.rsrp-excellent {
  color: #00cc00 !important;
  font-weight: bold;
}

.rsrp-good {
  color: #cccc00 !important;
}

.rsrp-fair {
  color: #ff8800 !important;
}

.rsrp-poor {
  color: #ff0000 !important;
  font-weight: bold;
}

/* 操作按钮 */
.action-buttons {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

.close-btn {
  margin-left: auto;
  color: white;
}

/* 底部站点列表 */
.bottom-panel {
  position: absolute;
  bottom: 10px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1000;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
  width: 650px;
  max-height: 150px;
}

.bottom-panel .panel-title {
  padding: 6px 12px;
  font-size: 12px;
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

.scroll-left {
  border-radius: 4px 0 0 4px;
}

.scroll-right {
  border-radius: 0 4px 4px 0;
}

.site-list-scroll {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  max-height: 100px;
  flex: 1;
  scroll-behavior: smooth;
}

.site-list-scroll::-webkit-scrollbar {
  height: 6px;
}

.site-list-scroll::-webkit-scrollbar-thumb {
  background: #ccc;
  border-radius: 3px;
}

.site-list-scroll::-webkit-scrollbar-track {
  background: #f0f0f0;
  border-radius: 3px;
}

.site-card {
  min-width: 120px;
  padding: 6px 10px;
  background: #f5f7fa;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  border: 2px solid transparent;
}

.site-card:hover {
  background: #e8eaed;
  border-color: #667eea;
}

.site-card.active {
  background: #e8eaff;
  border-color: #667eea;
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
  color: #333;
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
  color: #999;
}

/* 站点详情弹窗 */
.site-detail-popup {
  position: absolute;
  z-index: 1001;
  background: rgba(255, 255, 255, 0.98);
  border-radius: 10px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
  width: 280px;
  cursor: move;
}

.popup-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 10px 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
  font-weight: 600;
  border-radius: 10px 10px 0 0;
}

.popup-header .el-button {
  color: white;
}

.popup-content {
  padding: 12px;
}

.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  font-size: 12px;
}

.detail-item .label {
  color: #999;
  font-size: 11px;
}

/* Cesium容器 */
.cesium-container {
  width: 100%;
  height: 100%;
}
</style>
