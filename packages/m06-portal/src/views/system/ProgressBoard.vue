<template>
  <div class="progress-board">
    <!-- Header -->
    <div class="board-header">
      <div class="header-left">
        <h2>{{ data.project }}</h2>
        <p class="subtitle">{{ data.subtitle }}</p>
      </div>
      <div class="header-right">
        <el-tag type="info" size="large">更新于 {{ data.updatedAt }}</el-tag>
      </div>
    </div>

    <!-- Shared Base -->
    <div class="section shared-base">
      <h3 class="section-title">
        <el-icon><Box /></el-icon> 共享基座
        <el-tag size="small" :type="data.shared.completion >= 80 ? 'success' : 'warning'">
          {{ data.shared.completion }}%
        </el-tag>
      </h3>
      <div class="feature-list">
        <div v-for="f in data.shared.features" :key="f.name" class="feature-item">
          <span class="state-dot" :class="'state-' + f.state"></span>
          <span>{{ f.name }}</span>
        </div>
      </div>
    </div>

    <!-- Member Modules -->
    <div class="members-grid">
      <div v-for="m in data.members" :key="m.id" class="member-card" :class="'card-' + m.id.toLowerCase()">
        <div class="card-header">
          <div class="card-title">
            <span class="module-id">{{ m.id }}</span>
            <span class="owner-tag" :class="'tag-' + m.id.toLowerCase()">{{ m.owner }}</span>
          </div>
          <el-progress
            :percentage="m.completion"
            :stroke-width="10"
            :color="progressColor(m.completion)"
            style="width: 120px"
          />
        </div>
        <p class="topic">{{ m.topic }}</p>

        <!-- Services -->
        <div class="services-row">
          <el-tag v-for="s in m.services" :key="s.name" size="small" type="info" effect="plain">
            {{ s.name }} :{{ s.port }}
          </el-tag>
        </div>

        <!-- Features -->
        <div class="features-grid">
          <div v-for="f in m.features" :key="f.name" class="feature-check">
            <el-icon v-if="f.state === 'done'" color="#22c55e"><CircleCheckFilled /></el-icon>
            <el-icon v-else-if="f.state === 'doing'" color="#f59e0b"><Loading /></el-icon>
            <el-icon v-else color="#94a3b8"><CircleClose /></el-icon>
            <span :class="{ 'text-done': f.state === 'done', 'text-doing': f.state === 'doing', 'text-todo': f.state === 'todo' }">
              {{ f.name }}
            </span>
          </div>
        </div>

        <div class="card-footer">
          <span class="note">{{ m.note }}</span>
        </div>
      </div>
    </div>

    <p class="source-note">{{ data.source }}</p>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Box, CircleCheckFilled, CircleClose, Loading } from '@element-plus/icons-vue'
// 进度数据唯一来源：packages/m06-portal/progress-board/progress.json
// （构建时打包进 bundle；dev 模式改完文件 Vite 自动热更新）
import progressData from '../../../progress-board/progress.json'

const data = ref(progressData)

const progressColor = (val) => {
  if (val >= 80) return '#22c55e'
  if (val >= 50) return '#f59e0b'
  return '#ef4444'
}
</script>

<style scoped>
.progress-board {
  padding: 24px;
  min-height: 100%;
  background: #f8fafc;
}

.board-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}
.board-header h2 {
  font-size: 22px;
  font-weight: 700;
  color: #1e293b;
  margin: 0 0 4px 0;
}
.subtitle {
  color: #64748b;
  font-size: 14px;
  margin: 0;
}

.section {
  background: white;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  border: 1px solid #e2e8f0;
}
.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #334155;
  margin: 0 0 12px 0;
}
.feature-list {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}
.feature-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #475569;
}

.members-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: 16px;
}

.member-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  border: 1px solid #e2e8f0;
  border-top: 3px solid #2563eb;
  transition: transform 0.2s, box-shadow 0.2s;
}
.member-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}
.card-s1 { border-top-color: #3b82f6; }
.card-s2 { border-top-color: #10b981; }
.card-s3 { border-top-color: #f59e0b; }
.card-s4 { border-top-color: #8b5cf6; }
.card-s5 { border-top-color: #ec4899; }

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
}
.module-id {
  font-size: 18px;
  font-weight: 700;
  color: #1e293b;
}
.owner-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
}
.tag-s1 { background: rgba(59,130,246,0.15); color: #2563eb; }
.tag-s2 { background: rgba(16,185,129,0.15); color: #059669; }
.tag-s3 { background: rgba(245,158,11,0.15); color: #d97706; }
.tag-s4 { background: rgba(139,92,246,0.15); color: #7c3aed; }
.tag-s5 { background: rgba(236,72,153,0.15); color: #db2777; }

.topic {
  font-size: 13px;
  color: #64748b;
  margin: 0 0 12px 0;
  line-height: 1.4;
}

.services-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 14px;
}

.features-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 6px;
}
.feature-check {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}
.text-done { color: #16a34a; text-decoration: line-through; opacity: 0.7; }
.text-doing { color: #d97706; font-weight: 500; }
.text-todo { color: #94a3b8; }

.card-footer {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #f1f5f9;
}
.note {
  font-size: 12px;
  color: #94a3b8;
  line-height: 1.5;
  margin: 0;
}

.state-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
  flex-shrink: 0;
}
.state-done { background: #22c55e; }
.state-doing { background: #f59e0b; animation: pulse 1.5s infinite; }
.state-todo { background: #cbd5e1; }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.source-note {
  text-align: center;
  font-size: 12px;
  color: #94a3b8;
  margin-top: 20px;
}
</style>
