<template>
  <div class="dashboard-container">
    <div class="dashboard-header">
      <h1 class="welcome-title">欢迎回来，管理员！</h1>
      <p class="welcome-subtitle">通信基建数智化平台总览</p>
    </div>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon project-icon">
          <span class="icon-text">📦</span>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ statistics.projectCount }}</div>
          <div class="stat-label">项目总数</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon order-icon">
          <span class="icon-text">📋</span>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ statistics.orderCount }}</div>
          <div class="stat-label">工单数量</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon acceptance-icon">
          <span class="icon-text">✅</span>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ statistics.acceptanceCount }}</div>
          <div class="stat-label">验收任务</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon package-icon">
          <span class="icon-text">📁</span>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ statistics.packageCount }}</div>
          <div class="stat-label">交付包数</div>
        </div>
      </div>
    </div>

    <div class="charts-row">
      <div class="chart-card">
        <h3 class="chart-title">项目进度统计</h3>
        <div ref="projectChart" class="chart-container"></div>
      </div>
      <div class="chart-card">
        <h3 class="chart-title">工单状态分布</h3>
        <div ref="orderChart" class="chart-container"></div>
      </div>
    </div>

    <div class="quick-actions">
      <h3 class="section-title">快捷操作</h3>
      <div class="action-buttons">
        <button class="action-btn project-btn" @click="goTo('/m04/project')">
          <span class="action-icon">➕</span>
          <span class="action-text">新增项目</span>
        </button>
        <button class="action-btn order-btn" @click="goTo('/m04/work-order')">
          <span class="action-icon">📝</span>
          <span class="action-text">创建工单</span>
        </button>
        <button class="action-btn acceptance-btn" @click="goTo('/m04/project')">
          <span class="action-icon">✅</span>
          <span class="action-text">发起验收</span>
        </button>
        <button class="action-btn document-btn" @click="goTo('/m04/project')">
          <span class="action-icon">📤</span>
          <span class="action-text">上传文档</span>
        </button>
      </div>
    </div>

    <div class="bottom-row">
      <div class="info-card">
        <h3 class="card-title">📋 待办工单</h3>
        <div class="todo-list">
          <div v-for="item in todoList" :key="item.id" class="todo-item">
            <div class="todo-icon">🚨</div>
            <div class="todo-content">
              <div class="todo-title">{{ item.title }}</div>
              <div class="todo-time">{{ item.time }}</div>
            </div>
            <div class="todo-status" :class="item.statusClass">{{ item.status }}</div>
          </div>
        </div>
      </div>
      <div class="info-card">
        <h3 class="card-title">📝 最近动态</h3>
        <div class="activity-list">
          <div v-for="item in activityList" :key="item.id" class="activity-item">
            <div class="activity-dot"></div>
            <div class="activity-content">
              <div class="activity-text">{{ item.text }}</div>
              <div class="activity-time">{{ item.time }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'

const statistics = ref({
  projectCount: 128,
  orderCount: 35,
  acceptanceCount: 24,
  packageCount: 56
})

const todoList = ref([
  { id: 1, title: '工单#WO2024001 - 站点设备故障维修', time: '10分钟前', status: '紧急', statusClass: 'urgent' },
  { id: 2, title: '工单#WO2024002 - 项目验收申请处理', time: '25分钟前', status: '待处理', statusClass: 'pending' },
  { id: 3, title: '工单#WO2024003 - 材料采购审批', time: '1小时前', status: '待处理', statusClass: 'pending' },
  { id: 4, title: '工单#WO2024004 - 施工进度汇报', time: '2小时前', status: '处理中', statusClass: 'processing' }
])

const activityList = ref([
  { id: 1, text: '项目「通信基站建设项目A」已完成验收', time: '10分钟前' },
  { id: 2, text: '创建新工单「设备巡检任务」', time: '30分钟前' },
  { id: 3, text: '上传交付文档「项目设计方案.pdf」', time: '1小时前' },
  { id: 4, text: '项目「5G覆盖优化项目」进入施工阶段', time: '2小时前' },
  { id: 5, text: '验收任务「基站设备验收」已通过', time: '3小时前' }
])

const projectChart = ref(null)
const orderChart = ref(null)

const goTo = (path) => {
  window.location.href = path
}

const initCharts = () => {
  if (projectChart.value) {
    const chart = echarts.init(projectChart.value)
    chart.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: {
        type: 'category',
        data: ['项目A', '项目B', '项目C', '项目D', '项目E'],
        axisLine: { lineStyle: { color: '#6b7280' } },
        axisLabel: { color: '#9ca3af' }
      },
      yAxis: {
        type: 'value',
        axisLine: { lineStyle: { color: '#6b7280' } },
        axisLabel: { color: '#9ca3af' },
        splitLine: { lineStyle: { color: '#1f2937' } }
      },
      series: [{
        type: 'bar',
        data: [85, 72, 90, 65, 88],
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#8b5cf6' },
            { offset: 1, color: '#3b82f6' }
          ]),
          borderRadius: [8, 8, 0, 0]
        },
        emphasis: {
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#a78bfa' },
              { offset: 1, color: '#60a5fa' }
            ])
          }
        }
      }]
    })
  }

  if (orderChart.value) {
    const chart = echarts.init(orderChart.value)
    chart.setOption({
      tooltip: { trigger: 'item' },
      legend: {
        orient: 'vertical',
        right: '5%',
        top: 'center',
        textStyle: { color: '#9ca3af' }
      },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#111827',
          borderWidth: 2
        },
        label: {
          show: true,
          color: '#9ca3af'
        },
        emphasis: {
          label: { show: true, fontSize: 18, fontWeight: 'bold' }
        },
        data: [
          { value: 12, name: '待处理', itemStyle: { color: '#ef4444' } },
          { value: 15, name: '处理中', itemStyle: { color: '#f59e0b' } },
          { value: 8, name: '已完成', itemStyle: { color: '#10b981' } }
        ]
      }]
    })
  }
}

onMounted(() => {
  nextTick(() => {
    initCharts()
    window.addEventListener('resize', initCharts)
  })
})
</script>

<style scoped>
.dashboard-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
  padding: 30px;
  color: white;
}

.dashboard-header {
  margin-bottom: 30px;
}

.welcome-title {
  font-size: 32px;
  font-weight: bold;
  background: linear-gradient(90deg, #a78bfa, #60a5fa);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  text-shadow: 0 0 30px rgba(167, 139, 250, 0.5);
  margin: 0 0 10px 0;
}

.welcome-subtitle {
  color: #9ca3af;
  font-size: 16px;
  margin: 0;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 30px;
}

.stat-card {
  background: linear-gradient(145deg, rgba(30, 41, 59, 0.8), rgba(15, 23, 42, 0.9));
  border: 1px solid rgba(139, 92, 246, 0.3);
  border-radius: 16px;
  padding: 24px;
  display: flex;
  align-items: center;
  gap: 20px;
  transition: all 0.3s ease;
  box-shadow: 0 4px 30px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.stat-card:hover {
  transform: translateY(-5px);
  border-color: rgba(139, 92, 246, 0.6);
  box-shadow: 0 8px 40px rgba(139, 92, 246, 0.2);
}

.stat-icon {
  width: 64px;
  height: 64px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.project-icon {
  background: linear-gradient(135deg, #8b5cf6, #6366f1);
}

.order-icon {
  background: linear-gradient(135deg, #f59e0b, #f97316);
}

.acceptance-icon {
  background: linear-gradient(135deg, #10b981, #06b6d4);
}

.package-icon {
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
}

.icon-text {
  font-size: 28px;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 36px;
  font-weight: bold;
  background: linear-gradient(90deg, #fff, #9ca3af);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0;
}

.stat-label {
  color: #9ca3af;
  font-size: 14px;
  margin: 5px 0 0 0;
}

.charts-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin-bottom: 30px;
}

.chart-card {
  background: linear-gradient(145deg, rgba(30, 41, 59, 0.8), rgba(15, 23, 42, 0.9));
  border: 1px solid rgba(139, 92, 246, 0.3);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 4px 30px rgba(0, 0, 0, 0.3);
}

.chart-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 20px 0;
  color: #e5e7eb;
}

.chart-container {
  height: 250px;
}

.quick-actions {
  margin-bottom: 30px;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 20px 0;
  color: #e5e7eb;
}

.action-buttons {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.action-btn {
  background: linear-gradient(145deg, rgba(30, 41, 59, 0.8), rgba(15, 23, 42, 0.9));
  border: 1px solid rgba(139, 92, 246, 0.3);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
}

.action-btn:hover {
  transform: translateY(-3px);
  border-color: rgba(139, 92, 246, 0.6);
  box-shadow: 0 8px 30px rgba(139, 92, 246, 0.2);
}

.action-icon {
  font-size: 28px;
}

.action-text {
  font-size: 14px;
  color: #e5e7eb;
  font-weight: 500;
}

.bottom-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.info-card {
  background: linear-gradient(145deg, rgba(30, 41, 59, 0.8), rgba(15, 23, 42, 0.9));
  border: 1px solid rgba(139, 92, 246, 0.3);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 4px 30px rgba(0, 0, 0, 0.3);
}

.card-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 20px 0;
  color: #e5e7eb;
}

.todo-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.todo-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 15px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 10px;
  transition: all 0.3s ease;
}

.todo-item:hover {
  background: rgba(255, 255, 255, 0.08);
}

.todo-icon {
  font-size: 20px;
}

.todo-content {
  flex: 1;
}

.todo-title {
  font-size: 14px;
  color: #e5e7eb;
  margin: 0 0 5px 0;
}

.todo-time {
  font-size: 12px;
  color: #6b7280;
  margin: 0;
}

.todo-status {
  font-size: 12px;
  padding: 4px 12px;
  border-radius: 20px;
  font-weight: 500;
}

.todo-status.urgent {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.todo-status.pending {
  background: rgba(245, 158, 11, 0.2);
  color: #f59e0b;
}

.todo-status.processing {
  background: rgba(59, 130, 246, 0.2);
  color: #3b82f6;
}

.activity-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.activity-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.activity-item:last-child {
  border-bottom: none;
}

.activity-dot {
  width: 8px;
  height: 8px;
  background: linear-gradient(135deg, #8b5cf6, #3b82f6);
  border-radius: 50%;
  margin-top: 6px;
  flex-shrink: 0;
}

.activity-content {
  flex: 1;
}

.activity-text {
  font-size: 14px;
  color: #d1d5db;
  margin: 0 0 5px 0;
}

.activity-time {
  font-size: 12px;
  color: #6b7280;
  margin: 0;
}

@media (max-width: 1200px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .charts-row {
    grid-template-columns: 1fr;
  }
  .action-buttons {
    grid-template-columns: repeat(2, 1fr);
  }
  .bottom-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
  .action-buttons {
    grid-template-columns: 1fr;
  }
}
</style>