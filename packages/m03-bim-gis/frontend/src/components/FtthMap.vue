<template>
  <div class="ftth-map">
    <!-- 工具栏 -->
    <div class="map-toolbar">
      <div class="map-title">
        3D 地球 · FTTH 光网络（真实经纬度）
      </div>
      <div class="map-legend">
        <span class="legend-item"><i class="dot pbo" />PBO 入户光节点</span>
        <span class="legend-item"><i class="dot bpe" />BPE 楼栋/路边分光箱</span>
        <span class="legend-item"><i class="dot site" />PM 小区光汇聚点</span>
        <span class="legend-item"><i class="bar c1" />PM-0001 配线光缆</span>
        <span class="legend-item"><i class="bar c2" />PM-0002 配线光缆</span>
        <span class="legend-item"><i class="bar c3" />干线 TRANSPORT（局站↔小区）</span>
        <span class="legend-count">{{ boites.length }} 箱 / {{ cables.length }} 缆</span>
      </div>
      <div class="map-actions">
        <el-switch
          v-model="showLabels"
          inline-prompt
          active-text="名称"
          inactive-text="名称"
          @change="refreshLabels"
        />
        <el-switch
          v-model="showPillars"
          inline-prompt
          active-text="立柱"
          inactive-text="立柱"
          @change="refreshPillars"
        />
        <el-switch
          v-model="showCables"
          inline-prompt
          active-text="光路"
          inactive-text="光路"
          @change="refreshCables"
        />
        <el-button
          size="small"
          @click="fitAll"
        >
          全览
        </el-button>
        <el-button
          size="small"
          @click="resetView"
        >
          复位
        </el-button>
      </div>
    </div>

    <!-- Cesium 容器 -->
    <div
      ref="mapEl"
      class="map-canvas"
    >
      <!-- 坐标实时显示 -->
      <div
        v-if="viewerReady"
        class="coord-bar"
      >
        <span>经度 {{ currentLng.toFixed(5) }}</span>
        <span>纬度 {{ currentLat.toFixed(5) }}</span>
      </div>
      <!-- 点击详情卡 (箱体/光缆/站点) -->
      <div
        v-if="selected"
        class="info-card"
      >
        <div class="info-head">
          <span class="info-code">{{ selected.code }}</span>
          <el-tag
            size="small"
            :type="tagType"
          >
            {{ tagLabel }}
          </el-tag>
          <button
            class="info-close"
            @click="selected = null"
          >
            ×
          </button>
        </div>

        <!-- 箱体 -->
        <template v-if="selected.kind === 'boite'">
          <div class="info-row">
            <span>类型</span><b>{{ humanizeBoiteType(selected.type) }}</b>
          </div>
          <div class="info-row">
            <span>功能</span><b>{{ humanizeFonction(selected.fonction) }}</b>
          </div>
          <div class="info-row">
            <span>容量</span><b>{{ selected.capacite_fo }} 芯光纤</b>
          </div>
          <div
            v-if="selected.logements"
            class="info-row"
          >
            <span>覆盖户数</span><b>{{ selected.logements }} 户</b>
          </div>
          <div class="info-row">
            <span>归属汇聚点</span><b>{{ selected.pm || 'NA' }}</b>
          </div>
          <div class="info-row">
            <span>工程类型</span><b>{{ selected.ptec || 'NA' }}</b>
          </div>
          <div class="info-row">
            <span>地址</span><b>{{ selected.adresse || 'NA' }}</b>
          </div>
          <div class="info-row">
            <span>经纬度</span><b>{{ formatCoord(selected.x, selected.y) }}</b>
          </div>
          <div class="info-tip">
            {{ roleOfBoite(selected.type) }}
          </div>
          <el-button
            size="small"
            type="primary"
            class="info-fly"
            @click="flyToBoite(selected)"
          >
            飞向该箱
          </el-button>
        </template>

        <!-- 光缆 -->
        <template v-else-if="selected.kind === 'cable'">
          <div class="info-row">
            <span>光缆类型</span><b>{{ humanizeCableType(selected.type_cable) }}</b>
          </div>
          <div class="info-row">
            <span>容量</span><b>{{ selected.capacite }} 芯光纤</b>
          </div>
          <div class="info-row">
            <span>长度</span><b>{{ selected.longueur }} m</b>
          </div>
          <div class="info-row">
            <span>归属汇聚点</span><b>{{ selected.pm || 'NA' }}</b>
          </div>
          <div class="info-row">
            <span>起点</span><b>{{ selected.origine }}</b>
          </div>
          <div class="info-row">
            <span>终点</span><b>{{ selected.extremite }}</b>
          </div>
          <div class="info-row">
            <span>经纬度</span><b>{{ formatCableCoord(selected) }}</b>
          </div>
          <div class="info-tip">
            光缆是 FTTH 的“血管”，把局端/汇聚点的光信号送到各个分光箱和入户节点。
          </div>
          <el-button
            size="small"
            type="primary"
            class="info-fly"
            @click="flyToCable(selected)"
          >
            飞向起点
          </el-button>
        </template>

        <!-- 站点(PM) -->
        <template v-else>
          <div class="info-row">
            <span>类型</span><b>PM 小区光汇聚点</b>
          </div>
          <div class="info-row">
            <span>地址</span><b>{{ selected.adresse || 'NA' }}</b>
          </div>
          <div class="info-row">
            <span>经纬度</span><b>{{ formatCoord(selected.x, selected.y) }}</b>
          </div>
          <div class="info-tip">
            PM 是小区级光汇聚点，向上连接局端/干线，向下辐射配线光缆和分光箱。
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import * as Cesium from 'cesium'
import { createViewer } from '@/composables/useCesiumCore.js'

const props = defineProps({
  boites: { type: Array, default: () => [] },
  cables: { type: Array, default: () => [] },
  sites: { type: Array, default: () => [] },
})

const mapEl = ref(null)
const viewer = ref(null)
const viewerReady = ref(false)
const showLabels = ref(false)
const showPillars = ref(true)
const showCables = ref(true)
const selected = ref(null)
const currentLng = ref(0)
const currentLat = ref(0)
let resizeObserver = null
let pillarEntities = []
let cableEntities = []

// 颜色体系：箱体按类型，配线光缆按归属 PM，干线 TRANSPORT 独立色，站点金色
const C = {
  PBO: Cesium.Color.fromCssColorString('#22d3ee'),
  BPE: Cesium.Color.fromCssColorString('#fb923c'),
  SITE: Cesium.Color.fromCssColorString('#fbbf24'),
  CABLE_PM1: Cesium.Color.fromCssColorString('#60a5fa'),
  CABLE_PM2: Cesium.Color.fromCssColorString('#a78bfa'),
  CABLE_TRANS: Cesium.Color.fromCssColorString('#34d399'),
}
// 立柱高度(米)：BPE 分支箱容量大立得高，PBO 终端箱稍矮
const PILLAR_H = { BPE: 900, PBO: 420 }
const SITE_H = 1700

function cableColor(c) {
  if ((c.type_cable || '') === 'TRANSPORT') return C.CABLE_TRANS
  return c.pm === 'JAD-MAR-0002' ? C.CABLE_PM2 : C.CABLE_PM1
}

// 详情卡标签
const tagType = computed(() => {
  if (!selected.value) return 'info'
  if (selected.value.kind === 'boite') return selected.value.type === 'PBO' ? 'success' : 'warning'
  if (selected.value.kind === 'cable') return 'info'
  return 'warning'
})
const tagLabel = computed(() => {
  if (!selected.value) return ''
  const map = {
    boite: humanizeBoiteType(selected.value.type),
    cable: humanizeCableType(selected.value.type_cable),
    site: 'PM 小区光汇聚点',
  }
  return map[selected.value.kind]
})

// ── FTTH 信息面板人话化辅助函数 ────────────────────────
function humanizeBoiteType(type) {
  const t = String(type || '').toUpperCase()
  if (t === 'PBO') return 'PBO 入户光节点'
  if (t === 'BPE') return 'BPE 楼栋/路边分光箱'
  if (t === 'PM') return 'PM 小区光汇聚点'
  return type || '未知箱体'
}
function humanizeFonction(fonction) {
  const f = String(fonction || '').toUpperCase()
  if (f === 'PBO') return '入户光节点（光纤到户最后一公里）'
  if (f === 'BPE') return '楼栋/路边分光箱（把主干分给多个 PBO）'
  if (f === 'PM') return '小区光汇聚点'
  return fonction || 'NA'
}
function humanizeCableType(type) {
  const t = String(type || '').toUpperCase()
  if (t === 'TRANSPORT') return '干线光缆（局站↔小区）'
  if (t === 'DISTRIBUTION') return '配线光缆（PM↔分光箱）'
  if (t === 'DROP') return '入户光缆（分光箱↔用户）'
  return type || '未知光缆'
}
function roleOfBoite(type) {
  const t = String(type || '').toUpperCase()
  if (t === 'PBO') return 'PBO 是光纤入户前的最后节点，直接覆盖终端用户。'
  if (t === 'BPE') return 'BPE 负责把一根主干光缆分给多个 PBO，是楼栋/路边的“分水阀”。'
  return '该箱体是 FTTH 光网络中的接入节点。'
}
function formatCoord(x, y) {
  const lon = Number(x)
  const lat = Number(y)
  if (!Number.isFinite(lon) || !Number.isFinite(lat)) return 'NA'
  return `东经 ${lon.toFixed(5)}°, 北纬 ${lat.toFixed(5)}°`
}
function formatCableCoord(cable) {
  if (!cable || !cable.from || !cable.to) return 'NA'
  return `起 ${cable.from[0].toFixed(5)},${cable.from[1].toFixed(5)} → 终 ${cable.to[0].toFixed(5)},${cable.to[1].toFixed(5)}`
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

    viewer.value.screenSpaceEventHandler.setInputAction((event) => {
      const picked = viewer.value.scene.pick(event.position)
      const id = picked && picked.id
      if (id && id.boiteData) {
        selected.value = { kind: 'boite', ...id.boiteData }
      } else if (id && id.cableData) {
        selected.value = { kind: 'cable', ...id.cableData }
      } else if (id && id.siteData) {
        selected.value = { kind: 'site', ...id.siteData }
      } else {
        selected.value = null
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK)

    viewer.value.screenSpaceEventHandler.setInputAction((event) => {
      const ray = viewer.value.camera.getPickRay(event.endPosition)
      if (!ray) return
      const intersection = viewer.value.scene.globe.pick(ray, viewer.value.scene)
      if (intersection) {
        const carto = Cesium.Cartographic.fromCartesian(intersection)
        currentLng.value = Cesium.Math.toDegrees(carto.longitude)
        currentLat.value = Cesium.Math.toDegrees(carto.latitude)
      }
    }, Cesium.ScreenSpaceEventType.MOUSE_MOVE)

    resizeObserver = new ResizeObserver(() => {
      if (viewer.value) viewer.value.resize()
    })
    resizeObserver.observe(mapEl.value)

    renderScene()
  } catch (e) {
    console.error('[FtthMap] Cesium 初始化失败', e)
  }
}

// 全场景构建：站点 + 箱体点 + (立柱) + (光缆)
function renderScene() {
  if (!viewer.value) return
  viewer.value.entities.removeAll()
  pillarEntities = []
  cableEntities = []

  // 站点 (PM/NRO 局站根节点)
  for (const s of props.sites) {
    if (s.x == null || s.y == null) continue
    viewer.value.entities.add({
      position: Cesium.Cartesian3.fromDegrees(s.x, s.y, SITE_H),
      siteData: s,
      cylinder: {
        length: SITE_H,
        topRadius: 22,
        bottomRadius: 38,
        material: C.SITE.withAlpha(0.4),
        outline: false,
      },
      point: {
        pixelSize: 14,
        color: C.SITE,
        outlineColor: Cesium.Color.WHITE,
        outlineWidth: 2,
      },
      label: {
        text: 'PM ' + s.code,
        font: '13px sans-serif',
        fillColor: C.SITE,
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 4,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        pixelOffset: new Cesium.Cartesian2(0, -16),
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
    })
  }

  // 箱体：发光点(柱顶，可点击) + 立柱(可 toggle)
  for (const b of props.boites) {
    if (b.x == null || b.y == null) continue
    const color = C[b.type] || Cesium.Color.WHITE
    const h = PILLAR_H[b.type] || 500

    // 立柱(立体感)：从地面升起的中空光束，仅在开启时创建
    if (showPillars.value) {
      const pillar = viewer.value.entities.add({
        position: Cesium.Cartesian3.fromDegrees(b.x, b.y, h / 2),
        cylinder: {
          length: h,
          topRadius: 6,
          bottomRadius: 10,
          material: color.withAlpha(0.32),
          outline: false,
        },
      })
      pillarEntities.push(pillar)
    }

    // 柱顶发光点(可点击选中)
    const pt = {
      position: Cesium.Cartesian3.fromDegrees(b.x, b.y, h),
      boiteData: b,
      point: {
        pixelSize: 11,
        color,
        outlineColor: Cesium.Color.WHITE,
        outlineWidth: 1.5,
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
    }
    viewer.value.entities.add(pt)
  }

  // 光缆连线(发光折线，干线 TRANSPORT 独立色，配线按 PM 着色)
  if (showCables.value) {
    for (const c of props.cables) {
      const f = c.from
      const t = c.to
      if (!f || !t) continue
      const ent = viewer.value.entities.add({
        cableData: c,
        polyline: {
          positions: [
            Cesium.Cartesian3.fromDegrees(f[0], f[1], 0),
            Cesium.Cartesian3.fromDegrees(t[0], t[1], 0),
          ],
          width: (c.type_cable || '') === 'TRANSPORT' ? 4 : 2.5,
          material: new Cesium.PolylineGlowMaterialProperty({
            glowPower: 0.25,
            color: cableColor(c).withAlpha(0.85),
          }),
          arcType: Cesium.ArcType.GEODESIC,
        },
      })
      cableEntities.push(ent)
    }
  }

  fitAll()
}

function removeEntities(arr) {
  if (!viewer.value) return
  for (const e of arr) viewer.value.entities.remove(e)
}

function refreshPillars(val) {
  if (!viewer.value) return
  if (val) {
    for (const b of props.boites) {
      if (b.x == null || b.y == null) continue
      const color = C[b.type] || Cesium.Color.WHITE
      const h = PILLAR_H[b.type] || 500
      const pillar = viewer.value.entities.add({
        position: Cesium.Cartesian3.fromDegrees(b.x, b.y, h / 2),
        cylinder: {
          length: h,
          topRadius: 6,
          bottomRadius: 10,
          material: color.withAlpha(0.32),
          outline: false,
        },
      })
      pillarEntities.push(pillar)
    }
  } else {
    removeEntities(pillarEntities)
    pillarEntities = []
  }
}

function refreshCables(val) {
  if (!viewer.value) return
  if (val) {
    for (const c of props.cables) {
      const f = c.from
      const t = c.to
      if (!f || !t) continue
      const ent = viewer.value.entities.add({
        cableData: c,
        polyline: {
          positions: [
            Cesium.Cartesian3.fromDegrees(f[0], f[1], 0),
            Cesium.Cartesian3.fromDegrees(t[0], t[1], 0),
          ],
          width: (c.type_cable || '') === 'TRANSPORT' ? 4 : 2.5,
          material: new Cesium.PolylineGlowMaterialProperty({
            glowPower: 0.25,
            color: cableColor(c).withAlpha(0.85),
          }),
          arcType: Cesium.ArcType.GEODESIC,
        },
      })
      cableEntities.push(ent)
    }
  } else {
    removeEntities(cableEntities)
    cableEntities = []
  }
}

function refreshLabels(val) {
  if (!viewer.value) return
  for (const e of viewer.value.entities.values) {
    if (!e.boiteData) continue
    e.label = val
      ? {
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
      : undefined
  }
}

function fitAll() {
  let minLon = Infinity, minLat = Infinity, maxLon = -Infinity, maxLat = -Infinity
  const consider = (x, y) => {
    if (x == null || y == null) return
    minLon = Math.min(minLon, x); maxLon = Math.max(maxLon, x)
    minLat = Math.min(minLat, y); maxLat = Math.max(maxLat, y)
  }
  for (const b of props.boites) consider(b.x, b.y)
  for (const s of props.sites) consider(s.x, s.y)
  if (!isFinite(minLon)) return
  fitToBounds(minLon, minLat, maxLon, maxLat)
}

function fitToBounds(minLon, minLat, maxLon, maxLat) {
  if (!viewer.value) return
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

function resetView() {
  fitAll()
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

function flyToCable(c) {
  if (!viewer.value || !c.from) return
  viewer.value.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(c.from[0], c.from[1], 2500),
    orientation: {
      heading: 0,
      pitch: Cesium.Math.toRadians(-45),
      roll: 0,
    },
    duration: 1.5,
  })
}

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
  gap: 12px;
  font-size: 12px;
  color: #cbd5e1;
  flex-wrap: wrap;
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
.dot.site { background: #fbbf24; }
.bar {
  width: 14px;
  height: 4px;
  border-radius: 2px;
  display: inline-block;
}
.bar.c1 { background: #60a5fa; }
.bar.c2 { background: #a78bfa; }
.bar.c3 { background: #34d399; }
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
  height: 560px;
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
.info-tip {
  margin-top: 8px;
  padding: 8px 10px;
  font-size: 11px;
  line-height: 1.5;
  color: #bae6fd;
  background: rgba(56, 189, 248, 0.08);
  border-left: 3px solid #38bdf8;
  border-radius: 4px;
}
.info-fly {
  width: 100%;
  margin-top: 10px;
}
</style>
