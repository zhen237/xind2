<template>
  <div class="ftth-map">
    <!-- 工具栏 -->
    <div class="map-toolbar">
      <div class="map-title">3D 地球 · 箱体点位分布（真实经纬度）</div>
      <div class="map-legend">
        <span class="legend-item"><i class="dot pbo"></i>PBO 终端箱</span>
        <span class="legend-item"><i class="dot bpe"></i>BPE 分支箱</span>
        <span class="legend-count">共 {{ boites.length }} 个</span>
      </div>
      <div class="map-actions">
        <el-switch
          v-model="showLabels"
          inline-prompt
          active-text="名称"
          inactive-text="名称"
          @change="refreshLabels"
        />
        <el-button size="small" @click="fitAll">全览</el-button>
        <el-button size="small" @click="resetView">复位</el-button>
      </div>
    </div>

    <!-- Cesium 容器 -->
    <div ref="mapEl" class="map-canvas">
      <!-- 坐标实时显示 -->
      <div class="coord-bar" v-if="viewerReady">
        <span>经度 {{ currentLng.toFixed(5) }}</span>
        <span>纬度 {{ currentLat.toFixed(5) }}</span>
      </div>
      <!-- 点击详情卡 -->
      <div v-if="selected" class="info-card">
        <div class="info-head">
          <span class="info-code">{{ selected.code }}</span>
          <el-tag size="small" :type="selected.type === 'PBO' ? 'success' : 'warning'">
            {{ selected.type }}
          </el-tag>
          <button class="info-close" @click="selected = null">×</button>
        </div>
        <div class="info-row"><span>功能</span><b>{{ selected.fonction }}</b></div>
        <div class="info-row"><span>容量</span><b>{{ selected.capacite_fo }} FO</b></div>
        <div class="info-row" v-if="selected.logements">
          <span>户数</span><b>{{ selected.logements }}</b>
        </div>
        <div class="info-row"><span>归属 PM</span><b>{{ selected.pm }}</b></div>
        <div class="info-row"><span>PTEC</span><b>{{ selected.ptec }}</b></div>
        <div class="info-row"><span>地址</span><b>{{ selected.adresse || 'NA' }}</b></div>
        <div class="info-row"><span>坐标</span><b>{{ selected.x.toFixed(5) }}, {{ selected.y.toFixed(5) }}</b></div>
        <el-button size="small" type="primary" class="info-fly" @click="flyToBoite(selected)">
          飞向该箱
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as Cesium from 'cesium'
import { createViewer } from '@/composables/useCesiumCore.js'

const props = defineProps({
  boites: { type: Array, default: () => [] },
})

const mapEl = ref(null)
const viewer = ref(null)
const viewerReady = ref(false)
const showLabels = ref(false)
const selected = ref(null)
const currentLng = ref(0)
const currentLat = ref(0)
let resizeObserver = null

const COLOR = {
  PBO: Cesium.Color.fromCssColorString('#22d3ee'),
  BPE: Cesium.Color.fromCssColorString('#fb923c'),
}

function initViewer() {
  if (!mapEl.value) return
  try {
    viewer.value = createViewer(mapEl.value, {
      infoBox: false,
      selectionIndicator: false,
    })
    viewer.value.scene.backgroundColor = Cesium.Color.fromCssColorString('#0a1628')
    viewerReady.value = true

    // 点击拾取箱体
    viewer.value.screenSpaceEventHandler.setInputAction((event) => {
      const picked = viewer.value.scene.pick(event.position)
      if (picked && picked.id && picked.id.boiteData) {
        selected.value = picked.id.boiteData
      } else {
        selected.value = null
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK)

    // 实时坐标显示
    viewer.value.screenSpaceEventHandler.setInputAction((event) => {
      const ray = viewer.value.camera.getPickRay(event.endPosition)
      if (!ray) return
      const globe = viewer.value.scene.globe
      const intersection = globe.pick(ray, viewer.value.scene)
      if (intersection) {
        const carto = Cesium.Cartographic.fromCartesian(intersection)
        currentLng.value = Cesium.Math.toDegrees(carto.longitude)
        currentLat.value = Cesium.Math.toDegrees(carto.latitude)
      }
    }, Cesium.ScreenSpaceEventType.MOUSE_MOVE)

    // 容器尺寸变化 → 重算画布
    resizeObserver = new ResizeObserver(() => {
      if (viewer.value) viewer.value.resize()
    })
    resizeObserver.observe(mapEl.value)

    if (props.boites.length) renderPoints()
  } catch (e) {
    console.error('[FtthMap] Cesium 初始化失败', e)
  }
}

function renderPoints() {
  if (!viewer.value || !props.boites.length) return
  viewer.value.entities.removeAll()
  let minLon = Infinity, minLat = Infinity, maxLon = -Infinity, maxLat = -Infinity

  for (const b of props.boites) {
    const lon = b.x
    const lat = b.y
    if (lon == null || lat == null) continue
    minLon = Math.min(minLon, lon)
    maxLon = Math.max(maxLon, lon)
    minLat = Math.min(minLat, lat)
    maxLat = Math.max(maxLat, lat)

    const color = COLOR[b.type] || Cesium.Color.WHITE
    viewer.value.entities.add({
      position: Cesium.Cartesian3.fromDegrees(lon, lat, 0),
      boiteData: b,
      point: {
        pixelSize: 9,
        color,
        outlineColor: Cesium.Color.WHITE,
        outlineWidth: 1.5,
        heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
      },
      label: showLabels.value
        ? {
            text: b.code,
            font: '12px sans-serif',
            fillColor: Cesium.Color.WHITE,
            outlineColor: Cesium.Color.BLACK,
            outlineWidth: 3,
            style: Cesium.LabelStyle.FILL_AND_OUTLINE,
            verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
            pixelOffset: new Cesium.Cartesian2(0, -12),
            disableDepthTestDistance: Number.POSITIVE_INFINITY,
          }
        : undefined,
    })
  }

  fitToBounds(minLon, minLat, maxLon, maxLat)
}

function fitToBounds(minLon, minLat, maxLon, maxLat) {
  if (!isFinite(minLon) || !viewer.value) return
  const padLon = Math.max(maxLon - minLon, 0.01) * 0.15
  const padLat = Math.max(maxLat - minLat, 0.01) * 0.15
  viewer.value.camera.flyTo({
    destination: Cesium.Rectangle.fromDegrees(
      minLon - padLon,
      minLat - padLat,
      maxLon + padLon,
      maxLat + padLat,
    ),
    duration: 1.2,
  })
}

function fitAll() {
  if (!props.boites.length) return
  let minLon = Infinity, minLat = Infinity, maxLon = -Infinity, maxLat = -Infinity
  for (const b of props.boites) {
    if (b.x == null || b.y == null) continue
    minLon = Math.min(minLon, b.x); maxLon = Math.max(maxLon, b.x)
    minLat = Math.min(minLat, b.y); maxLat = Math.max(maxLat, b.y)
  }
  fitToBounds(minLon, minLat, maxLon, maxLat)
}

function resetView() {
  fitAll()
}

function refreshLabels(val) {
  if (!viewer.value) return
  const entities = viewer.value.entities.values
  for (const e of entities) {
    if (!e.boiteData) continue
    if (val) {
      e.label = {
        text: e.boiteData.code,
        font: '12px sans-serif',
        fillColor: Cesium.Color.WHITE,
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 3,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        pixelOffset: new Cesium.Cartesian2(0, -12),
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      }
    } else {
      e.label = undefined
    }
  }
}

function flyToBoite(b) {
  if (!viewer.value || b.x == null || b.y == null) return
  viewer.value.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(b.x, b.y, 2500),
    orientation: {
      heading: 0,
      pitch: Cesium.Math.toRadians(-45),
      roll: 0,
    },
    duration: 1.5,
  })
}

watch(
  () => props.boites,
  (list) => {
    if (list && list.length && viewer.value) {
      renderPoints()
    }
  },
  { immediate: false },
)

onMounted(() => {
  nextTick(() => initViewer())
})

onUnmounted(() => {
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
  if (viewer.value) {
    viewer.value.destroy()
    viewer.value = null
  }
})
</script>

<style scoped>
.ftth-map {
  position: relative;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  overflow: hidden;
}
.map-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: #0a1628;
  color: #e5e7eb;
  gap: 12px;
  flex-wrap: wrap;
}
.map-title {
  font-weight: 600;
  font-size: 14px;
}
.map-legend {
  display: flex;
  align-items: center;
  gap: 14px;
  font-size: 12px;
  color: #cbd5e1;
}
.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
  border: 1.5px solid #fff;
}
.dot.pbo { background: #22d3ee; }
.dot.bpe { background: #fb923c; }
.legend-count {
  color: #94a3b8;
}
.map-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.map-canvas {
  position: relative;
  width: 100%;
  height: 540px;
  background: #0a1628;
}
.coord-bar {
  position: absolute;
  bottom: 12px;
  left: 12px;
  display: flex;
  gap: 12px;
  padding: 6px 12px;
  background: rgba(10, 22, 40, 0.85);
  border-radius: 6px;
  font-family: monospace;
  font-size: 12px;
  color: #e5e7eb;
  z-index: 5;
}
.info-card {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 230px;
  background: rgba(15, 23, 42, 0.92);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 8px;
  padding: 12px 14px;
  color: #e5e7eb;
  z-index: 6;
  backdrop-filter: blur(6px);
}
.info-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.info-code {
  font-weight: 600;
  font-size: 14px;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.info-close {
  background: transparent;
  border: none;
  color: #94a3b8;
  font-size: 18px;
  cursor: pointer;
  line-height: 1;
  padding: 0 2px;
}
.info-close:hover { color: #fff; }
.info-row {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  padding: 4px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.info-row span { color: #94a3b8; }
.info-row b { font-weight: 500; }
.info-fly {
  width: 100%;
  margin-top: 10px;
}
</style>
