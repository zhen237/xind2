<template>
  <div class="stage-status-bar">
    <div class="ssb-title">
      <span>全流程各阶段实时状态</span>
      <span class="ssb-update">每 15s 刷新 · {{ lastUpdated }}</span>
    </div>
    <div class="ssb-cards">
      <div
        v-for="s in stages"
        :key="s.code"
        class="ssb-card"
        :class="[s.code, dotClass(s.count)]"
        @click="$emit('navigate', s.menuCode)"
      >
        <div class="ssb-dot"></div>
        <div class="ssb-body">
          <div class="ssb-name">
            <span class="ssb-code">{{ s.code.toUpperCase() }}</span>
            {{ s.name }}
          </div>
          <div class="ssb-sub">{{ s.sub }}</div>
        </div>
        <div class="ssb-count">
          <span class="num">{{ display(s.count) }}</span>
          <span class="unit">{{ s.unit }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { fetchStageCounts } from '@/api/stageStatus'

const emit = defineEmits(['navigate'])

const stages = ref([
  { code: 's2', name: '数据融合', sub: '融合任务', unit: '项', menuCode: 'fusion_upload', count: null },
  { code: 's1', name: '智能设计', sub: '设计方案', unit: '个', menuCode: 'design', count: null },
  { code: 's3', name: '智能审查', sub: '审查任务', unit: '个', menuCode: 'review_safety', count: null },
  { code: 's4', name: '施工指令', sub: 'BOM/指令', unit: '条', menuCode: 'instruction_bom', count: null },
  { code: 's5', name: '施工监管', sub: '监测设备', unit: '台', menuCode: 'supervision_monitor', count: null }
])

const lastUpdated = ref('')
let timer = null

function display(c) {
  return c == null ? '—' : c
}
function dotClass(c) {
  if (c == null) return 'offline'
  return c > 0 ? 'active' : 'empty'
}

async function load() {
  const counts = await fetchStageCounts()
  if (counts) {
    stages.value.forEach((s) => {
      s.count = counts[s.code]
    })
    lastUpdated.value = new Date().toLocaleTimeString('zh-CN', { hour12: false })
  }
}

onMounted(() => {
  load()
  timer = setInterval(load, 15000)
})
onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.stage-status-bar {
  margin: 0 0 16px;
  padding: 14px 16px;
  border-radius: 14px;
  background: #0f1b2e;
  border: 1px solid #233247;
  color: #e2e8f0;
}
.ssb-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: #cbd5e1;
  margin-bottom: 12px;
}
.ssb-update {
  font-size: 11px;
  color: #64748b;
}
.ssb-cards {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 10px;
}
.ssb-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border-radius: 10px;
  background: #16263c;
  border: 1px solid #233247;
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.ssb-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.3);
}
.ssb-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  flex: 0 0 auto;
}
.ssb-card.active .ssb-dot {
  background: #22c55e;
  box-shadow: 0 0 8px #22c55e;
}
.ssb-card.empty .ssb-dot {
  background: #64748b;
}
.ssb-card.offline .ssb-dot {
  background: #ef4444;
}
.ssb-body {
  flex: 1 1 auto;
  min-width: 0;
}
.ssb-name {
  font-size: 13px;
  font-weight: 600;
  color: #e2e8f0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ssb-code {
  display: inline-block;
  font-size: 10px;
  font-weight: 700;
  color: #0f1b2e;
  background: #60a5fa;
  border-radius: 4px;
  padding: 1px 5px;
  margin-right: 6px;
}
.ssb-card.s2 .ssb-code { background: #34d399; }
.ssb-card.s3 .ssb-code { background: #fbbf24; }
.ssb-card.s4 .ssb-code { background: #c084fc; }
.ssb-card.s5 .ssb-code { background: #f472b6; }
.ssb-sub {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 2px;
}
.ssb-count {
  flex: 0 0 auto;
  text-align: right;
}
.ssb-count .num {
  font-size: 22px;
  font-weight: 700;
  color: #60a5fa;
}
.ssb-card.active .ssb-count .num { color: #22c55e; }
.ssb-count .unit {
  font-size: 11px;
  color: #94a3b8;
  margin-left: 2px;
}
@media (max-width: 1080px) {
  .ssb-cards { grid-template-columns: repeat(2, 1fr); }
}
</style>
