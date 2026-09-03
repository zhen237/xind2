<template>
  <div class="pipeline-runner">
    <div class="pr-head">
      <div class="pr-title">
        <span>一键跑通全流程</span>
        <span class="pr-sub">真实串联 S2→S1→S3→S4→S5（每步均为真实接口调用）</span>
      </div>
      <div class="pr-actions">
        <el-button v-if="!running" type="primary" :icon="VideoPlay" @click="runAll">开始一键演示</el-button>
        <el-button v-if="running" type="info" :icon="Loading" :loading="true" disabled>演示进行中…</el-button>
        <el-button v-if="!running && hasRun" :icon="Refresh" @click="runAll">重新运行</el-button>
      </div>
    </div>

    <!-- 步骤条（单行横向） -->
    <div class="pr-steps">
      <template v-for="(s, i) in steps" :key="s.code">
        <div
          class="pr-step"
          :class="[s.status, { 'is-last': i === steps.length - 1 }]"
        >
          <div class="pr-dot">
            <el-icon v-if="s.status === 'success'"><CircleCheck /></el-icon>
            <el-icon v-else-if="s.status === 'failed'"><CircleClose /></el-icon>
            <el-icon v-else-if="s.status === 'running'"><Loading /></el-icon>
            <span v-else>{{ i + 1 }}</span>
          </div>
          <div class="pr-step-body">
            <div class="pr-step-name">{{ s.name }}</div>
            <div class="pr-step-msg">{{ s.msg || '待执行' }}</div>
          </div>
        </div>
        <div v-if="i < steps.length - 1" class="pr-arrow">→</div>
      </template>
    </div>

    <!-- 失败步骤的手动处理入口（横向排布，不挤占步骤条） -->
    <div v-if="failedIndex >= 0" class="pr-failed-actions">
      <el-alert
        type="error"
        :closable="false"
        show-icon
        :title="`${steps[failedIndex].name} 未通过真实接口校验`"
        :description="steps[failedIndex].msg || '该步真实接口调用失败'"
      />
      <div class="pr-failed-btns">
        <el-button size="small" type="warning" plain @click="goModule(steps[failedIndex].menuCode)">去 {{ steps[failedIndex].name }} 手动完成</el-button>
        <el-button size="small" type="primary" plain @click="retryFrom(failedIndex)">从 {{ steps[failedIndex].name }} 重试</el-button>
      </div>
    </div>

    <!-- 运行日志 -->
    <div v-if="log.length" class="pr-log">
      <div v-for="(l, i) in log" :key="i" class="pr-log-line" :class="l.type">
        <span class="pr-log-time">{{ l.time }}</span>
        <span class="pr-log-text">{{ l.text }}</span>
      </div>
    </div>
    <div v-else class="pr-hint">
      点击「开始一键演示」：S2 融合 → S1 设计（自动送审）→ S3 审查（自动转发）→ S4 出 BOM（自动推送）→ S5 监管。任一步真实接口失败会在该步标红并给出前往对应模块手动完成的入口。
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { VideoPlay, Refresh, Loading, CircleCheck, CircleClose } from '@element-plus/icons-vue'
import {
  s2EnsureFusion,
  s1CreateAndGenerate,
  s3WaitAndForward,
  s4GenerateBom,
  s5WaitVerify
} from '@/api/pipelineRun'

const emit = defineEmits(['navigate'])

const running = ref(false)
const hasRun = ref(false)
const log = ref([])

const steps = reactive([
  { code: 's2', name: 'S2 数据融合', menuCode: 'fusion_upload', status: 'pending', msg: '' },
  { code: 's1', name: 'S1 智能设计', menuCode: 'design', status: 'pending', msg: '' },
  { code: 's3', name: 'S3 智能审查', menuCode: 'review_safety', status: 'pending', msg: '' },
  { code: 's4', name: 'S4 施工指令', menuCode: 'instruction_bom', status: 'pending', msg: '' },
  { code: 's5', name: 'S5 施工监管', menuCode: 'supervision_monitor', status: 'pending', msg: '' }
])

// 当前失败步骤的索引（用于下方手动处理入口）
const failedIndex = computed(() => steps.findIndex((s) => s.status === 'failed'))

// 跨步骤传递的上下文（各服务返回的关键 ID）
const ctx = reactive({ fusionId: null, designTaskId: null, taskNo: null, reviewTaskId: null, bomTaskId: null, verifyCount: null })

function now() {
  return new Date().toLocaleTimeString('zh-CN', { hour12: false })
}
function appendLog(text, type = 'info') {
  log.value.push({ time: now(), text, type })
}
function setStep(i, status, msg) {
  steps[i].status = status
  if (msg) steps[i].msg = msg
}

// 每一步对应的真实调用（带 ctx 入参）
const runners = [
  async () => { const r = await s2EnsureFusion(); ctx.fusionId = r.fusionId; return r.summary },
  async () => { const r = await s1CreateAndGenerate(); ctx.designTaskId = r.designTaskId; ctx.taskNo = r.taskNo; return r.summary },
  async () => { const r = await s3WaitAndForward(ctx.designTaskId); ctx.reviewTaskId = r.reviewTaskId; return r.summary },
  async () => { const r = await s4GenerateBom(ctx.taskNo || ctx.designTaskId); ctx.bomTaskId = r.bomTaskId; return r.summary },
  async () => { const r = await s5WaitVerify(); ctx.verifyCount = r.verifyCount; return r.summary }
]

function resetFrom(start) {
  for (let i = start; i < steps.length; i++) {
    setStep(i, 'pending', '')
  }
}

async function runFrom(start) {
  running.value = true
  hasRun.value = true
  appendLog(`▶ 从第 ${start + 1} 步（${steps[start].name}）开始`, 'info')
  for (let i = start; i < steps.length; i++) {
    setStep(i, 'running', '调用真实接口中…')
    try {
      const summary = await runners[i]()
      setStep(i, 'success', summary)
      appendLog(`✓ ${steps[i].name}：${summary}`, 'success')
    } catch (e) {
      const msg = e?.response?.data?.message || e?.message || '未知错误'
      setStep(i, 'failed', msg)
      appendLog(`✗ ${steps[i].name} 失败：${msg}`, 'error')
      appendLog(`  → 可点击「去 ${steps[i].name} 手动完成」在该模块操作后，再「从该步重试」`, 'error')
      running.value = false
      return
    }
  }
  appendLog('🎉 全流程跑通：S2→S1→S3→S4→S5 数据已真实串联', 'success')
  running.value = false
}

function runAll() {
  log.value = []
  ctx.fusionId = ctx.designTaskId = ctx.taskNo = ctx.reviewTaskId = ctx.bomTaskId = ctx.verifyCount = null
  resetFrom(0)
  runFrom(0)
}

function retryFrom(i) {
  resetFrom(i)
  runFrom(i)
}

function goModule(menuCode) {
  emit('navigate', menuCode)
}
</script>

<style scoped>
.pipeline-runner {
  margin: 0 0 16px;
  padding: 14px 16px;
  border-radius: 14px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}
.pr-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
  flex-wrap: wrap;
  gap: 10px;
}
.pr-title {
  display: flex;
  flex-direction: column;
}
.pr-title > span:first-child {
  font-size: 15px;
  font-weight: 700;
  color: #1e293b;
}
.pr-sub {
  font-size: 12px;
  color: #64748b;
  margin-top: 2px;
}
.pr-actions {
  display: flex;
  gap: 8px;
}
.pr-steps {
  display: flex;
  align-items: stretch;
  flex-wrap: nowrap;
  overflow-x: auto;
  padding-bottom: 2px;
}
.pr-step {
  position: relative;
  flex: 1 1 0;
  min-width: 138px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}
.pr-step.success { background: #f0fdf4; border-color: #bbf7d0; }
.pr-step.failed { background: #fef2f2; border-color: #fecaca; }
.pr-step.running { background: #eff6ff; border-color: #bfdbfe; }
.pr-dot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 13px;
  flex: 0 0 auto;
  background: #e2e8f0;
  color: #475569;
}
.pr-step.success .pr-dot { background: #22c55e; color: #fff; }
.pr-step.failed .pr-dot { background: #ef4444; color: #fff; }
.pr-step.running .pr-dot { background: #3b82f6; color: #fff; }
.pr-step-body { flex: 1 1 auto; min-width: 0; }
.pr-step-name { font-size: 13px; font-weight: 600; color: #1e293b; }
.pr-step-msg {
  font-size: 11px;
  color: #64748b;
  margin-top: 2px;
  word-break: break-all;
  line-height: 1.4;
}
.pr-step.success .pr-step-msg { color: #16a34a; }
.pr-step.failed .pr-step-msg { color: #dc2626; }
.pr-arrow {
  flex: 0 0 auto;
  align-self: center;
  color: #cbd5e1;
  font-size: 18px;
  padding: 0 4px;
}
.pr-failed-actions {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.pr-failed-btns {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.pr-log {
  margin-top: 14px;
  padding: 10px 12px;
  border-radius: 8px;
  background: #0f172a;
  max-height: 200px;
  overflow-y: auto;
  font-family: ui-monospace, Menlo, Consolas, monospace;
  font-size: 12px;
}
.pr-log-line { display: flex; gap: 8px; padding: 2px 0; line-height: 1.5; }
.pr-log-time { color: #64748b; flex: 0 0 auto; }
.pr-log-text { color: #e2e8f0; }
.pr-log-line.success .pr-log-text { color: #4ade80; }
.pr-log-line.error .pr-log-text { color: #f87171; }
.pr-hint {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  background: #f1f5f9;
  font-size: 12px;
  color: #64748b;
  line-height: 1.6;
}
</style>
