<template>
  <div class="coverage-page">
    <!-- 顶部 -->
    <div class="coverage-header">
      <el-button :icon="ArrowLeft" size="small" @click="$router.back()">返回</el-button>
      <span class="page-title">信号覆盖评估</span>
      <div class="header-actions">
        <el-button-group>
          <el-button size="small" :type="viewMode === 'heatmap' ? 'primary' : ''" @click="viewMode = 'heatmap'">热力图</el-button>
          <el-button size="small" :type="viewMode === 'contour' ? 'primary' : ''" @click="viewMode = 'contour'">等值线</el-button>
        </el-button-group>
        <el-button size="small" type="success" :icon="VideoPlay" @click="runSimulation" :loading="simulating">
          {{ simulating ? '计算中...' : '运行仿真' }}
        </el-button>
      </div>
    </div>

    <!-- 主体 -->
    <div class="coverage-body">
      <!-- 左侧参数面板 -->
      <div class="params-panel panel">
        <div class="panel-title">仿真参数</div>
        <el-form :model="params" label-width="100px" size="small">
          <el-form-item label="传播模型">
            <el-select v-model="params.model" style="width: 100%">
              <el-option label="Cost-231 Hata" value="cost231" />
              <el-option label="Okumura-Hata" value="okumura" />
              <el-option label="自由空间" value="freespace" />
            </el-select>
          </el-form-item>
          <el-form-item label="频率 (MHz)">
            <el-input-number v-model="params.frequency" :min="700" :max="5000" :step="100" style="width: 100%" />
          </el-form-item>
          <el-form-item label="发射功率 (dBm)">
            <el-input-number v-model="params.txPower" :min="0" :max="50" :step="1" style="width: 100%" />
          </el-form-item>
          <el-form-item label="天线增益 (dBi)">
            <el-input-number v-model="params.antennaGain" :min="0" :max="30" :step="0.5" style="width: 100%" />
          </el-form-item>
          <el-form-item label="天线高度 (m)">
            <el-input-number v-model="params.antennaHeight" :min="5" :max="100" :step="1" style="width: 100%" />
          </el-form-item>
          <el-form-item label="接收高度 (m)">
            <el-input-number v-model="params.rxHeight" :min="1" :max="10" :step="0.5" style="width: 100%" />
          </el-form-item>
          <el-form-item label="覆盖半径 (km)">
            <el-input-number v-model="params.radius" :min="0.5" :max="10" :step="0.5" style="width: 100%" />
          </el-form-item>
          <el-form-item label="栅格大小 (m)">
            <el-input-number v-model="params.gridSize" :min="10" :max="200" :step="10" style="width: 100%" />
          </el-form-item>
        </el-form>

        <el-divider />

        <div class="panel-title">RSRP 阈值 (dBm)</div>
        <div class="threshold-list">
          <div v-for="item in rsrpThresholds" :key="item.range" class="threshold-row">
            <span class="threshold-color" :style="{ background: item.color }"></span>
            <span class="threshold-range">{{ item.range }}</span>
            <span class="threshold-label">{{ item.label }}</span>
          </div>
        </div>
      </div>

      <!-- 中间地图区域 -->
      <div class="map-container">
        <CesiumViewer
          ref="cesiumViewerRef"
          :center-lng="centerLng"
          :center-lat="centerLat"
          :zoom="15"
          :enable-pick="false"
          @ready="onViewerReady"
        />
        <!-- 仿真进度 -->
        <div v-if="simulating" class="sim-progress panel">
          <el-progress :percentage="simProgress" :status="simProgress === 100 ? 'success' : ''" />
          <span class="sim-status">{{ simStatus }}</span>
        </div>
      </div>

      <!-- 右侧结果面板 -->
      <div class="result-panel panel">
        <div class="panel-title">覆盖统计</div>
        <div v-if="coverageResult" class="result-content">
          <div class="result-item">
            <div class="result-label">总覆盖面积</div>
            <div class="result-value">{{ coverageResult.totalArea }} km²</div>
          </div>
          <div class="result-item">
            <div class="result-label">良好覆盖</div>
            <div class="result-value" style="color: #67C23A">{{ coverageResult.goodArea }} km²</div>
            <div class="result-percent">{{ coverageResult.goodPercent }}%</div>
          </div>
          <div class="result-item">
            <div class="result-label">一般覆盖</div>
            <div class="result-value" style="color: #E6A23C">{{ coverageResult.fairArea }} km²</div>
            <div class="result-percent">{{ coverageResult.fairPercent }}%</div>
          </div>
          <div class="result-item">
            <div class="result-label">弱覆盖</div>
            <div class="result-value" style="color: #F56C6C">{{ coverageResult.weakArea }} km²</div>
            <div class="result-percent">{{ coverageResult.weakPercent }}%</div>
          </div>
          <div class="result-item">
            <div class="result-label">盲区</div>
            <div class="result-value" style="color: #909399">{{ coverageResult.blindArea }} km²</div>
            <div class="result-percent">{{ coverageResult.blindPercent }}%</div>
          </div>
        </div>
        <el-empty v-else description="运行仿真后显示结果" :image-size="80" />

        <el-divider />

        <div class="panel-title">天线列表</div>
        <div class="antenna-list">
          <div v-for="antenna in antennas" :key="antenna.id" class="antenna-row">
            <span class="antenna-dot" :style="{ background: antenna.color || '#F56C6C' }"></span>
            <span class="antenna-name">{{ antenna.deviceName }}</span>
            <span class="antenna-azimuth">{{ antenna.azimuth || 0 }}°</span>
          </div>
          <el-empty v-if="antennas.length === 0" description="无天线设备" :image-size="60" />
        </div>

        <el-divider />

        <el-button type="primary" :icon="Document" @click="generateReport" :disabled="!coverageResult" style="width: 100%">
          生成覆盖报告
        </el-button>
      </div>
    </div>

    <!-- 覆盖报告对话框 -->
    <CoverageReport
      v-model:visible="reportVisible"
      :result="coverageResult"
      :params="params"
      :antennas="antennas"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, shallowRef } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, VideoPlay, Document } from '@element-plus/icons-vue'
import CesiumViewer from '@/components/CesiumViewer.vue'
import CoverageReport from '@/components/CoverageReport.vue'
import deviceApi from '@/api/device'

const route = useRoute()
const projectId = route.params.projectId

const cesiumViewerRef = ref(null)
const viewer = shallowRef(null)
const Cesium = shallowRef(null)
const simulating = ref(false)
const simProgress = ref(0)
const simStatus = ref('')
const viewMode = ref('heatmap')
const reportVisible = ref(false)

const centerLng = ref(114.4263)
const centerLat = ref(30.4925)

const devices = ref([])
const antennas = computed(() => devices.value.filter(d => d.deviceType === 'ANTENNA'))

const params = reactive({
  model: 'cost231',
  frequency: 2600,
  txPower: 46,
  antennaGain: 18,
  antennaHeight: 35,
  rxHeight: 1.5,
  radius: 3,
  gridSize: 50
})

const coverageResult = ref(null)

const rsrpThresholds = [
  { range: '≥ -85', label: '优秀', color: '#00B050' },
  { range: '-85 ~ -95', label: '良好', color: '#92D050' },
  { range: '-95 ~ -105', label: '一般', color: '#FFC000' },
  { range: '-105 ~ -115', label: '较弱', color: '#FF6600' },
  { range: '< -115', label: '盲区', color: '#FF0000' }
]

let coverageEntities = []
let coveragePrimitive = null
let heatmapDataSource = null

/**
 * 加载设备
 */
async function loadDevices() {
  try {
    const res = await deviceApi.listByProject(projectId)
    devices.value = res.data || []
    if (devices.value.length > 0) {
      const first = devices.value[0]
      centerLng.value = parseFloat(first.lng)
      centerLat.value = parseFloat(first.lat)
    }
  } catch (error) {
    ElMessage.error('加载设备失败')
  }
}

/**
 * Viewer 就绪
 */
function onViewerReady({ viewer: v, Cesium: C }) {
  viewer.value = v
  Cesium.value = C
  // 创建专用数据源用于覆盖热力图
  heatmapDataSource = new C.CustomDataSource('coverage-heatmap')
  v.dataSources.add(heatmapDataSource)
}

/**
 * 运行覆盖仿真
 */
async function runSimulation() {
  if (antennas.value.length === 0) {
    ElMessage.warning('项目中无天线设备，无法进行覆盖仿真')
    return
  }

  simulating.value = true
  simProgress.value = 0
  coverageResult.value = null

  try {
    // 清除上次结果
    clearCoverageEntities()

    const gridPoints = []
    const gridsPerAntenna = Math.ceil((params.radius * 2000 / params.gridSize) ** 2)
    const totalGrids = gridsPerAntenna * antennas.value.length
    let processed = 0

    // 为每个天线计算覆盖
    for (const antenna of antennas.value) {
      const antLng = parseFloat(antenna.lng)
      const antLat = parseFloat(antenna.lat)
      const antHeight = parseFloat(antenna.height) || params.antennaHeight
      const azimuth = parseFloat(antenna.azimuth) || 0
      const downtilt = parseFloat(antenna.downtilt) || 0

      // 生成栅格点
      const gridRadius = params.radius * 1000 // m
      const gridStep = params.gridSize
      const latStep = gridStep / 111000
      const lngStep = gridStep / (111000 * Math.cos(antLat * Math.PI / 180))
      const gridCount = Math.ceil(gridRadius / gridStep)

      for (let i = -gridCount; i <= gridCount; i++) {
        for (let j = -gridCount; j <= gridCount; j++) {
          const pointLat = antLat + i * latStep
          const pointLng = antLng + j * lngStep

          // 计算距离
          const dx = (pointLng - antLng) * 111000 * Math.cos(antLat * Math.PI / 180)
          const dy = (pointLat - antLat) * 111000
          const distance = Math.sqrt(dx * dx + dy * dy)

          if (distance > gridRadius) continue

          // 计算方位角差
          const pointAzimuth = Math.atan2(dx, dy) * 180 / Math.PI
          let angleDiff = Math.abs(pointAzimuth - azimuth)
          if (angleDiff > 180) angleDiff = 360 - angleDiff

          // 计算路径损耗
          const pathLoss = calculatePathLoss(distance, antHeight, params.rxHeight, params.frequency, params.model)

          // 计算天线方向图衰减
          const patternLoss = calculateAntennaPatternLoss(angleDiff, downtilt, distance, antHeight)

          // 计算 RSRP
          const rsrp = params.txPower + params.antennaGain - pathLoss - patternLoss

          gridPoints.push({
            lng: pointLng,
            lat: pointLat,
            rsrp: rsrp,
            distance: distance
          })

          processed++
          if (processed % 200 === 0) {
            simProgress.value = Math.min(99, Math.round(processed / totalGrids * 100))
            simStatus.value = `计算覆盖点 ${processed}/${totalGrids}...`
            await new Promise(resolve => setTimeout(resolve, 0))
          }
        }
      }
    }

    simProgress.value = 100
    simStatus.value = '渲染热力图...'

    // 渲染覆盖热力图
    renderCoverageHeatmap(gridPoints)

    // 统计覆盖结果
    coverageResult.value = calculateCoverageStats(gridPoints)

    simStatus.value = '完成'
    ElMessage.success('覆盖仿真完成')
  } catch (error) {
    console.error('覆盖仿真失败:', error)
    ElMessage.error('覆盖仿真失败: ' + error.message)
  } finally {
    simulating.value = false
  }
}

/**
 * 计算路径损耗
 */
function calculatePathLoss(distance, txHeight, rxHeight, frequency, model) {
  const d = Math.max(0.001, distance / 1000) // km
  const f = frequency // MHz

  switch (model) {
    case 'cost231':
      // Cost-231 Hata 模型（城市）
      const a = 46.3 + 33.9 * Math.log10(f) - 13.82 * Math.log10(txHeight)
      const b = 44.9 - 6.55 * Math.log10(txHeight)
      const c = 3.2 * Math.pow(Math.log10(11.75 * rxHeight), 2) - 4.97
      return a + b * Math.log10(d) + c - 3

    case 'okumura':
      // Okumura-Hata 模型
      const aH = (1.1 * Math.log10(f) - 0.7) * rxHeight - (1.56 * Math.log10(f) - 0.8)
      return 69.55 + 26.16 * Math.log10(f) - 13.82 * Math.log10(txHeight)
        + (44.9 - 6.55 * Math.log10(txHeight)) * Math.log10(d) - aH

    case 'freespace':
      // 自由空间路径损耗
      return 32.44 + 20 * Math.log10(f) + 20 * Math.log10(d)

    default:
      return 128 + 37.6 * Math.log10(d)
  }
}

/**
 * 计算天线方向图衰减
 */
function calculateAntennaPatternLoss(angleDiff, downtilt, distance, txHeight) {
  // 水平方向图（简化的余弦模型）
  const horizontalLoss = angleDiff > 65 ? 20 : 12 * Math.pow(Math.sin(angleDiff * Math.PI / 130), 2)

  // 垂直方向图
  const verticalAngle = Math.atan2(txHeight - params.rxHeight, distance) * 180 / Math.PI
  const verticalDiff = Math.abs(verticalAngle - downtilt)
  const verticalLoss = verticalDiff > 15 ? 15 : 10 * Math.pow(Math.sin(verticalDiff * Math.PI / 30), 2)

  return horizontalLoss + verticalLoss
}

/**
 * 渲染覆盖热力图 — 使用 PointPrimitiveCollection 批量渲染
 */
function renderCoverageHeatmap(points) {
  if (!viewer.value || !Cesium.value) return

  const C = Cesium.value
  const v = viewer.value

  // 清除上次渲染
  clearCoverageEntities()

  // 使用 PointPrimitiveCollection 批量绘制（性能远优于逐个 entity）
  const pointCollection = v.scene.primitives.add(new C.PointPrimitiveCollection())
  coveragePrimitive = pointCollection

  // 按颜色分组批量添加
  const colorBuckets = new Map()

  for (const point of points) {
    const colorKey = getRsrpLevel(point.rsrp)
    if (colorKey === null) continue

    if (!colorBuckets.has(colorKey)) {
      colorBuckets.set(colorKey, [])
    }
    colorBuckets.get(colorKey).push(point)
  }

  // 颜色映射
  const colorMap = {
    excellent: C.Color.fromCssColorString('#00B050').withAlpha(0.75),
    good: C.Color.fromCssColorString('#92D050').withAlpha(0.75),
    fair: C.Color.fromCssColorString('#FFC000').withAlpha(0.75),
    weak: C.Color.fromCssColorString('#FF6600').withAlpha(0.75),
    blind: C.Color.fromCssColorString('#FF0000').withAlpha(0.5)
  }

  for (const [level, pts] of colorBuckets) {
    const color = colorMap[level]
    for (const pt of pts) {
      pointCollection.add({
        position: C.Cartesian3.fromDegrees(pt.lng, pt.lat, 0),
        pixelSize: 6,
        color: color,
        scaleByDistance: new C.NearFarScalar(500, 1.5, 50000, 0.5)
      })
    }
  }

  // 同时在天线位置添加标注实体
  for (const antenna of antennas.value) {
    const entity = v.entities.add({
      position: C.Cartesian3.fromDegrees(
        parseFloat(antenna.lng),
        parseFloat(antenna.lat),
        parseFloat(antenna.height) || 35
      ),
      point: {
        pixelSize: 14,
        color: C.Color.WHITE,
        outlineColor: C.Color.fromCssColorString('#F56C6C'),
        outlineWidth: 3
      },
      label: {
        text: antenna.deviceName,
        font: '13px sans-serif',
        fillColor: C.Color.WHITE,
        outlineColor: C.Color.BLACK,
        outlineWidth: 2,
        style: C.LabelStyle.FILL_AND_OUTLINE,
        verticalOrigin: C.VerticalOrigin.BOTTOM,
        pixelOffset: new C.Cartesian2(0, -20),
        showBackground: true,
        backgroundColor: C.Color.fromCssColorString('#F56C6C').withAlpha(0.8)
      }
    })
    coverageEntities.push(entity)
  }
}

/**
 * 根据 RSRP 获取覆盖等级
 */
function getRsrpLevel(rsrp) {
  if (rsrp >= -85) return 'excellent'
  if (rsrp >= -95) return 'good'
  if (rsrp >= -105) return 'fair'
  if (rsrp >= -115) return 'weak'
  return 'blind'
}

/**
 * 计算覆盖统计
 */
function calculateCoverageStats(points) {
  const total = points.length
  let good = 0, fair = 0, weak = 0, blind = 0

  for (const p of points) {
    if (p.rsrp >= -95) good++
    else if (p.rsrp >= -105) fair++
    else if (p.rsrp >= -115) weak++
    else blind++
  }

  const cellArea = (params.gridSize / 1000) ** 2 // km²
  const totalArea = (total * cellArea).toFixed(2)

  return {
    totalArea,
    goodArea: (good * cellArea).toFixed(2),
    fairArea: (fair * cellArea).toFixed(2),
    weakArea: (weak * cellArea).toFixed(2),
    blindArea: (blind * cellArea).toFixed(2),
    goodPercent: ((good / total) * 100).toFixed(1),
    fairPercent: ((fair / total) * 100).toFixed(1),
    weakPercent: ((weak / total) * 100).toFixed(1),
    blindPercent: ((blind / total) * 100).toFixed(1)
  }
}

/**
 * 清除覆盖实体
 */
function clearCoverageEntities() {
  if (!viewer.value) return
  // 清除 entity
  coverageEntities.forEach(e => viewer.value.entities.remove(e))
  coverageEntities = []
  // 清除 primitive collection
  if (coveragePrimitive) {
    viewer.value.scene.primitives.remove(coveragePrimitive)
    coveragePrimitive = null
  }
}

/**
 * 生成报告
 */
function generateReport() {
  reportVisible.value = true
}

/**
 * 组件卸载清理
 */
onBeforeUnmount(() => {
  clearCoverageEntities()
  if (heatmapDataSource && viewer.value) {
    viewer.value.dataSources.remove(heatmapDataSource)
  }
})

onMounted(() => {
  loadDevices()
})
</script>

<style scoped>
.coverage-page {
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.coverage-header {
  height: 48px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 16px;
  flex-shrink: 0;
}

.page-title {
  font-size: 15px;
  font-weight: bold;
  flex: 1;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.coverage-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.params-panel {
  width: 260px;
  padding: 12px;
  overflow-y: auto;
  flex-shrink: 0;
  border-right: 1px solid #e4e7ed;
  border-radius: 0;
}

.map-container {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.result-panel {
  width: 280px;
  padding: 12px;
  overflow-y: auto;
  flex-shrink: 0;
  border-left: 1px solid #e4e7ed;
  border-radius: 0;
}

.panel-title {
  font-size: 13px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 8px;
}

.threshold-list, .antenna-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.threshold-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  padding: 2px 0;
}

.threshold-color {
  width: 16px;
  height: 12px;
  border-radius: 2px;
}

.threshold-range {
  width: 90px;
  color: #606266;
}

.threshold-label {
  color: #909399;
}

.sim-progress {
  position: absolute;
  bottom: 16px;
  left: 50%;
  transform: translateX(-50%);
  width: 300px;
  padding: 12px;
  z-index: 1000;
}

.sim-status {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  display: block;
}

.result-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.result-item {
  padding: 8px;
  border-radius: 4px;
  background: #f5f7fa;
}

.result-label {
  font-size: 12px;
  color: #909399;
}

.result-value {
  font-size: 18px;
  font-weight: bold;
}

.result-percent {
  font-size: 12px;
  color: #909399;
}

.antenna-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  padding: 4px 0;
}

.antenna-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.antenna-name {
  flex: 1;
}

.antenna-azimuth {
  color: #909399;
  font-size: 12px;
}

.el-divider {
  margin: 12px 0;
}
</style>
