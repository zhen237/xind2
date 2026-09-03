<template>
  <div class="s1s3-flow">
    <!-- 顶部全生命周期数据流：S2 → S1 → S3 → S4 → S5（S2 为数据底座，融合后喂入 S1 做设计） -->
    <div class="flow-head">
      <div class="pipeline">
        <div
          v-for="(step, idx) in pipeline"
          :key="step.code"
          class="pipeline-step"
        >
          <div
            class="flow-endpoint"
            :class="step.code"
            @click="emit('navigate', step.menuCode)"
            :title="step.title"
          >
            <span class="ep-icon">{{ step.label }}</span>
            <span class="ep-name">{{ step.name }}</span>
            <span class="ep-sub">{{ step.sub }}</span>
          </div>
          <div v-if="idx < pipeline.length - 1" class="flow-arrow">
            <div class="arrow-line">
              <span class="dot"></span>
              <span class="dot"></span>
              <span class="dot"></span>
            </div>
            <span class="arrow-text">{{ step.arrowText }}</span>
          </div>
        </div>
      </div>
      <div class="flow-stat">
        <span class="stat-num">{{ tasks.length }}</span>
        <span class="stat-label">S1 已推送审查任务</span>
        <span class="stat-num done">{{ doneCount }}</span>
        <span class="stat-label">审查完成</span>
      </div>
    </div>

    <!-- 最近 S1→S3 任务列表 -->
    <div class="flow-body">
      <div class="fb-title">
        <span>最近 S1 → S3 设计审查记录</span>
        <span class="fb-update">每 15s 自动刷新 · {{ lastUpdated }}</span>
      </div>

      <div v-if="loading" class="fb-empty">加载中…</div>
      <div v-else-if="tasks.length === 0" class="fb-empty">
        暂无 S1 推送的审查任务（可在左侧「智能设计」生成方案后自动推送）
      </div>

      <div v-else class="fb-list">
        <div
          v-for="t in tasks"
          :key="t.id"
          class="fb-row"
        >
          <div class="fb-id">
            <span class="tag-s1">来自S1</span>
            <span class="id-text">{{ t.designTaskId }}</span>
          </div>
          <div class="fb-name" :title="t.taskName">{{ t.taskName }}</div>
          <div class="fb-status">
            <span
              class="status-dot"
              :style="{ background: statusColor(t.taskStatus) }"
            ></span>
            {{ statusLabel(t.taskStatus) }}
          </div>
          <div class="fb-cov">覆盖率 {{ formatCov(t.coverageRate) }}</div>
        <div class="fb-time">{{ t.createTime }}</div>
      </div>
    </div>

    <!-- 数据完整度预检：拉取最新 S1 任务的规则结果，呈现可比对 / 待核查 -->
    <div class="completeness" v-if="completeness !== null">
      <div class="cp-title">
        <span>数据完整度预检 · 最新 S1 任务 <b>{{ latestTaskId }}</b></span>
        <span class="cp-pct" :class="pctClass">{{ completenessPct }}%</span>
      </div>
      <el-progress :percentage="completenessPct" :stroke-width="10" :color="pctColor" />
      <div class="cp-legend">
        <span><i class="lg ok"></i>已具备数据 {{ evaluatedCount }}</span>
        <span><i class="lg pend"></i>待核查 {{ pendingCount }}</span>
        <span><i class="lg vio"></i>已审出违规 {{ violationCount }}</span>
      </div>

      <div v-if="pendingGroups.length" class="cp-pending">
        <div class="cp-sub">待补全参数（按类别）。在 S1 加载的 GeoJSON 的 properties 中补上这些字段并重新送审，S3 即可自动审出合规 / 违规：</div>
        <div v-for="g in pendingGroups" :key="g.category" class="cp-group">
          <div class="cp-cat">{{ g.category }}（{{ g.items.length }}）</div>
          <div v-for="r in g.items" :key="r.rule_code" class="cp-item" :title="r.suggestion">
            <span class="cp-rc">{{ r.rule_code }}</span>
            <span class="cp-rn">{{ r.rule_name }}</span>
            <span class="cp-need">缺：{{ r.needParams }}</span>
          </div>
        </div>
      </div>
      <div v-else class="cp-ok-note">
        当前任务数据已覆盖全部 24 条规则所需参数，S3 已完成真实比对（无待核查项）。
      </div>
    </div>
  </div>
</div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { getS1ReviewTasks, getTaskResults, statusLabel, statusColor } from '@/api/s3Review'

const emit = defineEmits(['navigate'])

// 通信基建全生命周期数据流：数据融合(S2) → 智能设计(S1) → 审查(S3) → 施工指令(S4) → 施工监管(S5)
// 说明：S2 是 S1 的上游数据底座，有 CAD 图时先走 S2 融合再喂给 S1；无 CAD 图时 S1 直接基于现网底图设计。
const pipeline = [
  {
    code: 's2',
    label: 'S2',
    name: '数据融合',
    sub: 'CAD/BIM 融合',
    title: '点击进入 S2 数据融合',
    menuCode: 'fusion_upload',
    arrowText: '融合后方案'
  },
  {
    code: 's1',
    label: 'S1',
    name: '智能设计',
    sub: 'M03 三维场景',
    title: '点击进入 S1 智能设计',
    menuCode: 'design',
    arrowText: '设计数据'
  },
  {
    code: 's3',
    label: 'S3',
    name: '智能审查',
    sub: '规则引擎校验',
    title: '点击进入 S3 智能审查',
    menuCode: 'review_safety',
    arrowText: '审查通过'
  },
  {
    code: 's4',
    label: 'S4',
    name: '施工指令',
    sub: 'BOM/工艺/指令',
    title: '点击进入 S4 施工指令',
    menuCode: 'instruction_bom',
    arrowText: '下发指令'
  },
  {
    code: 's5',
    label: 'S5',
    name: '施工监管',
    sub: '实时监控/验收',
    title: '点击进入 S5 施工监管',
    menuCode: 'supervision_monitor'
  }
]

const tasks = ref([])
const loading = ref(true)
const lastUpdated = ref('')
const results = ref([])
const completeness = ref(null)
let timer = null

async function load() {
  try {
    tasks.value = await getS1ReviewTasks(6)
    await loadCompleteness()
  } catch (e) {
    // 后端未启动或无权限时静默，保留上次数据
    console.warn('[S1→S3] 拉取审查任务失败', e)
  } finally {
    loading.value = false
    const d = new Date()
    lastUpdated.value = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`
  }
}

// 拉取最新 S1 任务的规则结果明细，计算数据完整度（真实比对 / 待核查）
async function loadCompleteness() {
  const top = tasks.value[0]
  if (!top || top.id == null) {
    completeness.value = null
    return
  }
  try {
    results.value = await getTaskResults(top.id)
  } catch (e) {
    console.warn('[S1→S3] 拉取规则结果失败', e)
    results.value = []
  }
}

const doneCount = computed(
  () => tasks.value.filter((t) => t.taskStatus === 'COMPLETED').length
)

function formatCov(v) {
  if (v == null) return '—'
  // 后端 coverageRate 已按 *100 存储（如 20.83 表示 20.83%），这里直接格式化即可
  return `${Number(v).toFixed(1)}%`
}

// ===== 数据完整度预检计算 =====
const latestTaskId = computed(
  () => (tasks.value[0] && tasks.value[0].designTaskId) || ''
)
// 总规则数（取任务对象的 totalCount；pending 行数 == 缺数据的规则数，
// 完全通过但无结果行的规则也视为"已具备数据"）
const totalRules = computed(
  () => (tasks.value[0] && tasks.value[0].totalCount) || results.value.length
)
const pendingCount = computed(
  () => results.value.filter((r) => r.riskLevel === 'pending').length
)
const violationCount = computed(
  () => results.value.filter((r) => ['critical', 'error', 'warning'].includes(r.riskLevel)).length
)
// 已具备数据（可真实比对）的规则数 = 总规则数 - 待核查数
const evaluatedCount = computed(() => Math.max(0, totalRules.value - pendingCount.value))
const completenessPct = computed(() => {
  const total = totalRules.value
  if (!total) return 0
  return Math.round((evaluatedCount.value / total) * 100)
})
const pctColor = computed(() =>
  completenessPct.value >= 80 ? '#22c55e' : completenessPct.value >= 40 ? '#fbbf24' : '#38bdf8'
)
const pctClass = computed(() =>
  completenessPct.value >= 80 ? 'good' : completenessPct.value >= 40 ? 'mid' : 'low'
)
const pendingGroups = computed(() => {
  const map = {}
  for (const r of results.value) {
    if (r.riskLevel !== 'pending') continue
    const cat = r.category || '其他'
    if (!map[cat]) map[cat] = []
    const m = (r.suggestion || '').match(/（如\s*([^）]+)）/)
    const need = m ? m[1] : r.standardParam || '—'
    map[cat].push({
      rule_code: r.ruleCode,
      rule_name: r.ruleName,
      needParams: need,
      suggestion: r.suggestion
    })
  }
  return Object.entries(map).map(([category, items]) => ({ category, items }))
})

onMounted(() => {
  load()
  timer = setInterval(load, 15000)
})
onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.s1s3-flow {
  margin: 8px 0 24px;
  padding: 18px 20px;
  border-radius: 14px;
  background: #0f1b2e;
  border: 1px solid #233247;
  color: #e2e8f0;
}
.flow-head {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}
.pipeline {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0;
}
.pipeline-step {
  display: flex;
  align-items: center;
}
.flow-endpoint {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 92px;
  padding: 10px 14px;
  border-radius: 12px;
  border: 1px solid;
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.flow-endpoint:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
}
.flow-endpoint.s1 {
  background: rgba(37, 99, 235, 0.12);
  border-color: rgba(37, 99, 235, 0.5);
}
.flow-endpoint.s2 {
  background: rgba(5, 150, 105, 0.12);
  border-color: rgba(5, 150, 105, 0.5);
}
.flow-endpoint.s3 {
  background: rgba(217, 119, 6, 0.12);
  border-color: rgba(217, 119, 6, 0.5);
}
.flow-endpoint.s4 {
  background: rgba(124, 58, 237, 0.12);
  border-color: rgba(124, 58, 237, 0.5);
}
.flow-endpoint.s5 {
  background: rgba(219, 39, 119, 0.12);
  border-color: rgba(219, 39, 119, 0.5);
}
.ep-icon {
  font-weight: 700;
  font-size: 18px;
  color: #fff;
}
.flow-endpoint.s1 .ep-icon { color: #60a5fa; }
.flow-endpoint.s2 .ep-icon { color: #34d399; }
.flow-endpoint.s3 .ep-icon { color: #fbbf24; }
.flow-endpoint.s4 .ep-icon { color: #a78bfa; }
.flow-endpoint.s5 .ep-icon { color: #f472b6; }
.ep-name {
  font-size: 14px;
  margin-top: 2px;
  color: #e2e8f0;
}
.ep-sub {
  font-size: 11px;
  color: #94a3b8;
}
.flow-arrow {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 90px;
}
.arrow-line {
  display: flex;
  align-items: center;
  gap: 6px;
}
.arrow-line .dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #38bdf8;
  animation: pulse 1.2s infinite;
}
.arrow-line .dot:nth-child(2) { animation-delay: 0.2s; }
.arrow-line .dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes pulse {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 1; }
}
.arrow-text {
  font-size: 11px;
  color: #7dd3fc;
  margin-top: 4px;
}
.flow-stat {
  margin-left: auto;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}
.stat-num {
  font-size: 22px;
  font-weight: 700;
  color: #60a5fa;
}
.stat-num.done { color: #22c55e; }
.stat-label {
  font-size: 11px;
  color: #94a3b8;
}
.flow-body {
  margin-top: 16px;
}
.fb-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: #cbd5e1;
  margin-bottom: 8px;
}
.fb-update {
  font-size: 11px;
  color: #64748b;
}
.fb-empty {
  padding: 18px;
  text-align: center;
  font-size: 13px;
  color: #64748b;
  background: #0b1526;
  border-radius: 10px;
}
.fb-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.fb-row {
  display: grid;
  grid-template-columns: 230px 1fr 90px 100px 170px;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: #0b1526;
  border: 1px solid #1e2d44;
  border-radius: 10px;
}
.fb-id {
  display: flex;
  align-items: center;
  gap: 8px;
}
.tag-s1 {
  flex: none;
  font-size: 10px;
  color: #1e293b;
  background: #38bdf8;
  border-radius: 6px;
  padding: 2px 6px;
  font-weight: 700;
}
.id-text {
  font-family: ui-monospace, monospace;
  font-size: 13px;
  color: #e2e8f0;
}
.fb-name {
  font-size: 13px;
  color: #cbd5e1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.fb-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #e2e8f0;
}
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.fb-cov {
  font-size: 12px;
  color: #94a3b8;
}
.fb-time {
  font-size: 12px;
  color: #64748b;
  text-align: right;
}

/* ===== 数据完整度预检 ===== */
.completeness {
  margin-top: 18px;
  padding: 14px 16px;
  border-radius: 12px;
  background: #0b1526;
  border: 1px solid #1e2d44;
}
.cp-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: #cbd5e1;
  margin-bottom: 8px;
}
.cp-title b {
  color: #38bdf8;
  font-family: ui-monospace, monospace;
}
.cp-pct {
  font-size: 20px;
  font-weight: 700;
}
.cp-pct.good { color: #22c55e; }
.cp-pct.mid { color: #fbbf24; }
.cp-pct.low { color: #38bdf8; }
.cp-legend {
  display: flex;
  gap: 16px;
  margin-top: 8px;
  font-size: 12px;
  color: #94a3b8;
}
.cp-legend .lg {
  display: inline-block;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  margin-right: 5px;
  vertical-align: middle;
}
.cp-legend .lg.ok { background: #22c55e; }
.cp-legend .lg.pend { background: #64748b; }
.cp-legend .lg.vio { background: #ef4444; }
.cp-pending {
  margin-top: 12px;
}
.cp-sub {
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 8px;
}
.cp-group {
  margin-bottom: 8px;
}
.cp-cat {
  font-size: 12px;
  color: #7dd3fc;
  margin-bottom: 4px;
}
.cp-item {
  display: grid;
  grid-template-columns: 64px 1fr auto;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  background: #0f1b2e;
  border: 1px solid #1e2d44;
  border-radius: 8px;
  margin-bottom: 4px;
  font-size: 12px;
}
.cp-rc {
  font-family: ui-monospace, monospace;
  color: #fbbf24;
}
.cp-rn {
  color: #cbd5e1;
}
.cp-need {
  color: #f87171;
  font-size: 11px;
  white-space: nowrap;
}
.cp-ok-note {
  margin-top: 12px;
  font-size: 12px;
  color: #22c55e;
}
</style>
