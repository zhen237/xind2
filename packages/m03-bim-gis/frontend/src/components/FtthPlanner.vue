<template>
  <div class="planner">
    <!-- 参数面板 -->
    <div class="param-panel">
      <div class="param-title">
        智能规划参数（拖动即时重算）
      </div>
      <div class="param-grid">
        <div class="param-item">
          <label>单 PBO 目标户数 · {{ params.pboMaxHomes }}</label>
          <el-slider
            :model-value="params.pboMaxHomes"
            :min="12"
            :max="48"
            :step="4"
            @update:model-value="(v) => onParam('pboMaxHomes', v)"
          />
        </div>
        <div class="param-item">
          <label>单 BPE 挂接 PBO 数 · {{ params.bpeFanout }}</label>
          <el-slider
            :model-value="params.bpeFanout"
            :min="3"
            :max="12"
            :step="1"
            @update:model-value="(v) => onParam('bpeFanout', v)"
          />
        </div>
        <div class="param-item">
          <label>覆盖率判定半径 · {{ params.coverageRadius }}m</label>
          <el-slider
            :model-value="params.coverageRadius"
            :min="100"
            :max="800"
            :step="50"
            @update:model-value="(v) => onParam('coverageRadius', v)"
          />
        </div>
        <div class="param-item">
          <label>汇聚比</label>
          <el-radio-group
            :model-value="params.splitRatio"
            @update:model-value="(v) => onParam('splitRatio', v)"
          >
            <el-radio-button :value="4">
              1:4
            </el-radio-button>
            <el-radio-button :value="8">
              1:8
            </el-radio-button>
            <el-radio-button :value="16">
              1:16
            </el-radio-button>
          </el-radio-group>
        </div>
      </div>
      <div class="param-actions">
        <el-switch
          v-model="showReal"
          inline-prompt
          active-text="叠加真实竣工"
          inactive-text="仅看规划"
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

    <!-- 对比卡片 -->
    <div
      v-if="comparison"
      class="compare-row"
    >
      <div
        v-for="c in cmpCards"
        :key="c.label"
        class="cmp-card"
      >
        <div class="cmp-value">
          <span class="plan">{{ c.plan }}</span>
          <span class="vs">/</span>
          <span class="real">{{ c.real }}</span>
        </div>
        <div class="cmp-label">
          {{ c.label }}
        </div>
        <div class="cmp-bar">
          <i
            class="fill"
            :style="{ width: c.pct + '%' }"
          />
        </div>
      </div>
    </div>

    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="legend">
        <span class="legend-item"><i class="dot pbo" />规划 PBO</span>
        <span class="legend-item"><i class="dot bpe" />规划 BPE</span>
        <span class="legend-item"><i class="dot site" />站点</span>
        <span class="legend-item"><i class="dot demand" />住户需求点</span>
        <span class="legend-item"><i class="bar dist" />配线缆</span>
        <span class="legend-item"><i class="bar trans" />主干缆</span>
        <span
          v-if="showReal"
          class="legend-item"
        ><i class="dot realdot" />真实竣工</span>
      </div>
      <div class="hint">
        算法自动选址 · 容量 · 树形路由，与真实竣工叠加对比
      </div>
    </div>

    <!-- Cesium -->
    <div
      ref="mapEl"
      class="map-canvas"
    >
      <div
        v-if="viewerReady"
        class="coord-bar"
      >
        <span>经度 {{ currentLng.toFixed(5) }}</span>
        <span>纬度 {{ currentLat.toFixed(5) }}</span>
      </div>
      <div
        v-if="selected"
        class="info-card"
      >
        <div class="info-head">
          <span class="info-code">{{ selected.code }}</span>
          <el-tag
            size="small"
            :type="selected.type === 'PBO' ? 'success' : selected.type === 'BPE' ? 'warning' : 'danger'"
          >
            {{ selected.type }}
          </el-tag>
          <button
            class="info-close"
            @click="selected = null"
          >
            ×
          </button>
        </div>
        <div class="info-row">
          <span>覆盖户数</span><b>{{ selected.homes }}</b>
        </div>
        <div
          v-if="selected.capacityPorts"
          class="info-row"
        >
          <span>端口</span><b>{{ selected.capacityPorts }}</b>
        </div>
        <div
          v-if="selected.capacityCores"
          class="info-row"
        >
          <span>芯数</span><b>{{ selected.capacityCores }} FO</b>
        </div>
        <div class="info-row">
          <span>挂靠站点</span><b>{{ selected.parentSite }}</b>
        </div>
        <div
          v-if="selected.parentBpe"
          class="info-row"
        >
          <span>上级 BPE</span><b>{{ selected.parentBpe }}</b>
        </div>
        <div class="info-row">
          <span>坐标</span><b>{{ selected.x.toFixed(5) }}, {{ selected.y.toFixed(5) }}</b>
        </div>
        <el-button
          size="small"
          type="primary"
          class="info-fly"
          @click="flyTo(selected)"
        >
          飞向该箱
        </el-button>
      </div>
      <div
        v-if="loading"
        class="loading-mask"
      >
        规划计算中…
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as Cesium from 'cesium'
import { createViewer } from '@/composables/useCesiumCore.js'
import { DEFAULT_PARAMS, runPlan, evaluatePlan } from '@/utils/ftthPlanner.js'
import { useFtthDataset } from '@/composables/useFtthDataset.js'

const { currentTag, loadIndex, path } = useFtthDataset()

const mapEl = ref(null)
const viewer = ref(null)
const viewerReady = ref(false)
const currentLng = ref(0)
const currentLat = ref(0)
const selected = ref(null)
const loading = ref(true)
const showReal = ref(true)

const params = ref({ ...DEFAULT_PARAMS })
const demand = ref([])
const sites = ref([])
const realStats = ref({ pboReal: 0, bpeReal: 0, cableLenReal: 0 })
const realBoites = ref([])
const realCables = ref([])
const plan = ref(null)

const comparison = computed(() => {
  if (!plan.value) return null
  return evaluatePlan(plan.value, demand.value, realStats.value, params.value)
})

const cmpCards = computed(() => {
  const c = comparison.value
  if (!c) return []
  const mk = (label, planV, realV, higherBetter = false) => {
    const max = Math.max(planV, realV, 1)
    const pct = Math.round((planV / max) * 100)
    return { label, plan: planV, real: realV, pct: higherBetter ? pct : 100 - pct }
  }
  return [
    mk('PBO 终端箱', c.pboPlanned, c.pboReal),
    mk('BPE 分支箱', c.bpePlanned, c.bpeReal),
    mk('光缆总长(m)', c.cableLenPlannedM, c.cableLenRealM),
    { label: '需求覆盖率', plan: Math.round(c.coverageRate * 100) + '%', real: '—', pct: Math.round(c.coverageRate * 100) },
    { label: '聚类纯度', plan: Math.round(c.clusterPurity * 100) + '%', real: '—', pct: Math.round(c.clusterPurity * 100) },
  ]
})

const C = {
  PBO: Cesium.Color.fromCssColorString('#22d3ee'),
  BPE: Cesium.Color.fromCssColorString('#fb923c'),
  SITE: Cesium.Color.fromCssColorString('#fbbf24'),
  DEMAND: Cesium.Color.fromCssColorString('#94a3b8'),
  DIST: Cesium.Color.fromCssColorString('#60a5fa'),
  TRANS: Cesium.Color.fromCssColorString('#34d399'),
  REAL: Cesium.Color.fromCssColorString('#64748b'),
}
const PILLAR_H = { PBO: 420, BPE: 900, SITE: 1700 }

function onParam(key, val) {
  params.value[key] = val
  recompute()
}

function recompute() {
  if (!demand.value.length) return
  plan.value = runPlan(demand.value, sites.value, params.value)
  renderScene()
}

function renderScene() {
  if (!viewer.value || !plan.value) return
  const v = viewer.value
  v.entities.removeAll()
  const p = plan.value

  // 需求点（灰）
  for (const d of demand.value) {
    v.entities.add({
      position: Cesium.Cartesian3.fromDegrees(d.x, d.y, 0),
      point: { pixelSize: 5, color: C.DEMAND.withAlpha(0.9), outlineColor: Cesium.Color.WHITE, outlineWidth: 1 },
    })
  }

  // 规划箱体 + 立柱
  for (const b of [...p.siteList, ...p.bpeList, ...p.pboList]) {
    const color = C[b.type] || Cesium.Color.WHITE
    const h = PILLAR_H[b.type] || 500
    v.entities.add({
      position: Cesium.Cartesian3.fromDegrees(b.x, b.y, h / 2),
      cylinder: { length: h, topRadius: 6, bottomRadius: 10, material: color.withAlpha(0.3), outline: false },
    })
    v.entities.add({
      position: Cesium.Cartesian3.fromDegrees(b.x, b.y, h),
      point: { pixelSize: 9, color, outlineColor: Cesium.Color.WHITE, outlineWidth: 1.5 },
      boiteData: b,
    })
  }

  // 规划缆（发光）
  for (const c of p.cables) {
    const col = c.type === 'TRANSPORT' ? C.TRANS : C.DIST
    v.entities.add({
      polyline: {
        positions: [Cesium.Cartesian3.fromDegrees(c.from[0], c.from[1], 0), Cesium.Cartesian3.fromDegrees(c.to[0], c.to[1], 0)],
        width: c.type === 'TRANSPORT' ? 4 : 2.5,
        material: new Cesium.PolylineGlowMaterialProperty({ glowPower: 0.25, color: col.withAlpha(0.85) }),
        arcType: Cesium.ArcType.GEODESIC,
      },
    })
  }

  // 真实竣工叠加（灰）
  if (showReal.value) {
    for (const b of realBoites.value) {
      v.entities.add({
        position: Cesium.Cartesian3.fromDegrees(b.x, b.y, 600),
        point: { pixelSize: 7, color: C.REAL.withAlpha(0.55) },
      })
    }
    for (const c of realCables.value) {
      if (!c.from || !c.to) continue
      v.entities.add({
        polyline: {
          positions: [Cesium.Cartesian3.fromDegrees(c.from[0], c.from[1], 0), Cesium.Cartesian3.fromDegrees(c.to[0], c.to[1], 0)],
          width: 1.2,
          material: C.REAL.withAlpha(0.4),
          arcType: Cesium.ArcType.GEODESIC,
        },
      })
    }
  }
}

function flyTo(b) {
  if (!viewer.value || b.x == null) return
  viewer.value.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(b.x, b.y, 2500),
    orientation: { heading: 0, pitch: Cesium.Math.toRadians(-45), roll: 0 },
    duration: 1.2,
  })
}

function fitAll() {
  if (!viewer.value || !plan.value) return
  const pts = []
  for (const b of [...plan.value.pboList, ...plan.value.bpeList, ...plan.value.siteList])
    pts.push(Cesium.Cartesian3.fromDegrees(b.x, b.y))
  if (!pts.length) return
  viewer.value.camera.flyTo({ destination: Cesium.Rectangle.fromCartesianArray(pts).expand(1.3), duration: 1.5 })
}

function resetView() {
  if (viewer.value) viewer.value.camera.flyTo({ destination: Cesium.Cartesian3.fromDegrees(-8.529, 33.223, 4000), duration: 1.0 })
}

async function loadAll() {
  try {
    const [planRes, dataRes] = await Promise.all([
      fetch(path('ftth-plan.json')),
      fetch(path('ftth-data.json')),
    ])
    const planJson = await planRes.json()
    const dataJson = await dataRes.json()
    demand.value = planJson.demand_points || []
    sites.value = (planJson.planned_boites || []).filter((b) => b.type === 'SITE')
    const comp = planJson.comparison || {}
    realStats.value = { pboReal: comp.pbo_real, bpeReal: comp.bpe_real, cableLenReal: comp.cable_len_real_m }
    realBoites.value = dataJson.boites || []
    realCables.value = dataJson.cables || []
    loading.value = false
    await nextTick()
    await initViewer()
    recompute()
    fitAll()
  } catch (e) {
    console.error('规划数据加载失败', e)
    loading.value = false
  }
}

async function initViewer() {
  viewer.value = await createViewer(mapEl.value)
  viewerReady.value = true
  viewer.value.screenSpaceEventHandler.setInputAction((event) => {
    const picked = viewer.value.scene.pick(event.position)
    if (picked && picked.id && picked.id.boiteData) selected.value = picked.id.boiteData
    else selected.value = null
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK)
  viewer.value.screenSpaceEventHandler.setInputAction((movement) => {
    const cart = viewer.value.camera.pickEllipsoid(movement.endPosition, viewer.value.scene.globe.ellipsoid)
    if (cart) {
      const c = Cesium.Cartographic.fromCartesian(cart)
      currentLng.value = Cesium.Math.toDegrees(c.longitude)
      currentLat.value = Cesium.Math.toDegrees(c.latitude)
    }
  }, Cesium.ScreenSpaceEventType.MOUSE_MOVE)
}

let initialized = false
async function initAll() {
  await loadIndex()
  await loadAll()
  initialized = true
}

// 在 Ftth.vue 顶部切换数据集时，规划页若已加载则同步重载真实竣工叠加
watch(currentTag, () => {
  if (initialized) loadAll()
})

onMounted(initAll)
onUnmounted(() => {
  if (viewer.value && !viewer.value.isDestroyed()) viewer.value.destroy()
})
</script>

<style scoped>
.planner {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.param-panel {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 14px 16px;
}
.param-title {
  font-weight: 600;
  margin-bottom: 10px;
  font-size: 14px;
}
.param-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 28px;
}
.param-item label {
  font-size: 12px;
  color: #475569;
}
.param-actions {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 10px;
}
.compare-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
}
.cmp-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px 12px;
  text-align: center;
}
.cmp-value {
  font-size: 18px;
  font-weight: 600;
}
.cmp-value .plan {
  color: #0ea5e9;
}
.cmp-value .real {
  color: #94a3b8;
}
.cmp-value .vs {
  color: #cbd5e1;
  margin: 0 4px;
}
.cmp-label {
  font-size: 12px;
  color: #64748b;
  margin: 4px 0 6px;
}
.cmp-bar {
  height: 4px;
  background: #e2e8f0;
  border-radius: 2px;
  overflow: hidden;
}
.cmp-bar .fill {
  display: block;
  height: 100%;
  background: #0ea5e9;
}
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 12px;
  color: #475569;
}
.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}
.dot.pbo { background: #22d3ee; }
.dot.bpe { background: #fb923c; }
.dot.site { background: #fbbf24; }
.dot.demand { background: #94a3b8; }
.dot.realdot { background: #64748b; }
.bar {
  width: 16px;
  height: 4px;
  border-radius: 2px;
  display: inline-block;
}
.bar.dist { background: #60a5fa; }
.bar.trans { background: #34d399; }
.hint {
  font-size: 12px;
  color: #94a3b8;
}
.map-canvas {
  position: relative;
  height: 560px;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #e2e8f0;
}
.coord-bar {
  position: absolute;
  left: 10px;
  bottom: 10px;
  background: rgba(15, 23, 42, 0.7);
  color: #e2e8f0;
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 4px;
  display: flex;
  gap: 12px;
  z-index: 10;
}
.info-card {
  position: absolute;
  right: 10px;
  top: 10px;
  width: 240px;
  background: rgba(15, 23, 42, 0.88);
  color: #e2e8f0;
  border-radius: 8px;
  padding: 12px;
  z-index: 10;
}
.info-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.info-code {
  font-weight: 600;
  font-size: 13px;
}
.info-close {
  margin-left: auto;
  background: none;
  border: none;
  color: #94a3b8;
  font-size: 18px;
  cursor: pointer;
  line-height: 1;
}
.info-row {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  padding: 2px 0;
}
.info-row span {
  color: #94a3b8;
}
.info-fly {
  margin-top: 8px;
  width: 100%;
}
.loading-mask {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(248, 250, 252, 0.6);
  color: #475569;
  font-size: 14px;
  z-index: 20;
}
</style>
