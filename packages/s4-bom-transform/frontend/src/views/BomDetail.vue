<template>
  <div class="bom-detail">
    <!-- 返回 + 状态提示 -->
    <el-page-header @back="$router.push('/bom')" title="返回 BOM 列表" />

    <!-- 运行中状态横幅 -->
    <el-alert v-if="status === 'running' || status === 'pending'" type="warning"
      :closable="false" show-icon class="status-alert">
      <template #title>
        BOM 正在生成中，请稍候...
        <span style="margin-left:12px;color:#666">已等待 {{ pollCount * 1.5 }}s</span>
      </template>
    </el-alert>
    <el-alert v-if="status === 'failed'" type="error" :closable="false" show-icon class="status-alert">
      <template #title>BOM 生成失败，请返回重新生成</template>
    </el-alert>

    <!-- 状态统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header><span>主设备</span></template>
          <div class="stat-value c-blue">{{ detail.mainDeviceQty || 0 }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header><span>辅材</span></template>
          <div class="stat-value c-orange">{{ detail.auxiliaryQty || 0 }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header><span>线缆</span></template>
          <div class="stat-value c-green">{{ detail.cableQty || 0 }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header><span>物料类目</span></template>
          <div class="stat-value c-purple">{{ detail.totalCategories || 0 }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 任务信息 -->
    <el-card class="info-card">
      <el-descriptions :column="3" size="small" border>
        <el-descriptions-item label="任务 ID">{{ detail.taskId }}</el-descriptions-item>
        <el-descriptions-item label="设计任务">{{ detail.designTaskId }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="status === 'done' ? 'success' : status === 'running' ? 'warning' : 'danger'">
            {{ status }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ detail.createdAt }}</el-descriptions-item>
        <el-descriptions-item label="完成时间">{{ detail.finishedAt || '-' }}</el-descriptions-item>
        <el-descriptions-item label="操作">
          <el-button size="small" type="success" @click="doExport" :disabled="status !== 'done'">
            导出 Excel
          </el-button>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- ────── 物料清单（三类 Tab） ────── -->
    <el-card class="material-card" v-if="status === 'done'">
      <template #header><span>物料清单</span></template>
      <el-tabs v-model="activeTab" type="card">
        <el-tab-pane label="主设备" name="main_device">
          <el-table :data="mainDevices" stripe size="small" max-height="520">
            <el-table-column prop="materialCode" label="物料编码" width="120" />
            <el-table-column prop="materialName" label="物料名称" min-width="160" />
            <el-table-column prop="spec" label="规格型号" width="140" />
            <el-table-column prop="deviceName" label="关联设备" width="140" />
            <el-table-column prop="qty" label="数量" width="70" />
            <el-table-column prop="unit" label="单位" width="60" />
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="辅材" name="auxiliary">
          <el-table :data="auxiliaries" stripe size="small" max-height="520">
            <el-table-column prop="materialCode" label="物料编码" width="120" />
            <el-table-column prop="materialName" label="物料名称" min-width="160" />
            <el-table-column prop="spec" label="规格型号" width="140" />
            <el-table-column prop="deviceName" label="关联设备" width="140" />
            <el-table-column prop="qty" label="数量" width="70" />
            <el-table-column prop="unit" label="单位" width="60" />
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="线缆" name="cable">
          <el-table :data="cables" stripe size="small" max-height="520">
            <el-table-column prop="materialCode" label="物料编码" width="120" />
            <el-table-column prop="materialName" label="物料名称" min-width="160" />
            <el-table-column prop="spec" label="规格型号" width="140" />
            <el-table-column prop="deviceName" label="关联设备" width="140" />
            <el-table-column prop="qty" label="根数" width="60" />
            <el-table-column label="单根长度(m)" width="100">
              <template #default="{ row }">{{ row.singleLength ?? '-' }}</template>
            </el-table-column>
            <el-table-column label="总长度(m)" width="100">
              <template #default="{ row }">{{ row.totalLength ?? '-' }}</template>
            </el-table-column>
            <el-table-column prop="unit" label="单位" width="60" />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- ────── 关键工序工艺 ────── -->
    <el-card class="process-card" v-if="processSteps.length && status === 'done'">
      <template #header><span>关键工序工艺要求</span></template>
      <el-collapse accordion>
        <el-collapse-item v-for="(step, idx) in processSteps" :key="idx"
          :title="`${step['序号'] || (idx + 1)}. ${step['适用设备类型'] || ''} — ${step['工序名称'] || ''}`">
          <el-descriptions :column="2" size="small" border>
            <el-descriptions-item label="工艺要求">{{ step['工艺要求'] || '' }}</el-descriptions-item>
            <el-descriptions-item label="验收标准">{{ step['验收标准'] || '' }}</el-descriptions-item>
          </el-descriptions>
        </el-collapse-item>
      </el-collapse>
    </el-card>

    <!-- ────── 纤芯分配表 ────── -->
    <el-card class="fiber-card" v-if="fiberData && fiberData.allocations && fiberData.allocations.length && status === 'done'">
      <template #header><span>纤芯分配表</span></template>

      <!-- 汇总 -->
      <el-descriptions :column="5" size="small" border class="fiber-summary">
        <el-descriptions-item label="总芯数">{{ fiberData.summary?.total_cores_assigned || 0 }}</el-descriptions-item>
        <el-descriptions-item label="ODF容量">{{ fiberData.summary?.odf_capacity || 0 }}</el-descriptions-item>
        <el-descriptions-item label="使用率">{{ fiberData.summary?.odf_usage_rate || '0%' }}</el-descriptions-item>
        <el-descriptions-item label="预留">{{ fiberData.summary?.reserve_cores || 0 }}</el-descriptions-item>
        <el-descriptions-item label="空余">{{ (fiberData.summary?.odf_capacity || 0) - (fiberData.summary?.total_cores_assigned || 0) }}</el-descriptions-item>
      </el-descriptions>

      <el-table :data="fiberData.allocations" stripe size="small" style="margin-top:12px">
        <el-table-column prop="起始设备" label="起始设备" width="140" />
        <el-table-column prop="起始端口" label="起始端口" width="120" />
        <el-table-column prop="终止设备" label="目的设备" width="140" />
        <el-table-column prop="终止端口" label="目的端口" width="120" />
        <el-table-column prop="纤芯类型" label="光纤类型" width="110" />
        <el-table-column prop="纤芯号" label="纤芯号" width="70" />
        <el-table-column prop="长度(m)" label="长度(m)" width="100" />
        <el-table-column prop="纤芯用途" label="备注" min-width="160" />
      </el-table>
    </el-card>

    <!-- 运行中时显示骨架占位 -->
    <el-card v-if="status === 'running' || status === 'pending'" class="loading-card">
      <el-skeleton :rows="6" animated />
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { getBomFull, getTaskStatus } from '../api/bom'

const route = useRoute()
const taskId = route.params.taskId

const detail = ref({})
const processSteps = ref([])
const fiberData = ref(null)
const status = ref('loading')
const loading = ref(true)
const activeTab = ref('main_device')
const pollCount = ref(0)

let pollTimer = null

// 按类别过滤
const mainDevices = computed(() => (detail.value.items || []).filter(i => i.category === 'main_device'))
const auxiliaries = computed(() => (detail.value.items || []).filter(i => i.category === 'auxiliary'))
const cables = computed(() => (detail.value.items || []).filter(i => i.category === 'cable'))

const doExport = () => {
  window.open(`/api/s4/bom/${taskId}/export`, '_blank')
}

const loadFullData = async () => {
  try {
    const data = await getBomFull(taskId)
    detail.value = data
    status.value = data.status || 'unknown'
    processSteps.value = data.processRequirements || []
    fiberData.value = data.fiberAllocation || null

    if (data.status === 'done') {
      clearPoll()
    } else if (data.status === 'running' || data.status === 'pending') {
      // 还在运行中，启动轮询
      startPoll()
    }
    // failed → 停止
    if (data.status === 'failed') {
      clearPoll()
    }
  } catch (e) {
    status.value = 'error'
    console.error('加载 BOM 详情失败', e)
  } finally {
    loading.value = false
  }
}

const startPoll = () => {
  if (pollTimer) return
  pollTimer = setInterval(async () => {
    pollCount.value++
    try {
      const st = await getTaskStatus(taskId)
      if (st.status === 'done') {
        clearPoll()
        // 重新加载全量数据
        await loadFullData()
      } else if (st.status === 'failed') {
        status.value = 'failed'
        detail.value.status = 'failed'
        clearPoll()
      }
    } catch (e) {
      console.error('轮询状态失败', e)
    }
  }, 1500)
}

const clearPoll = () => {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

onMounted(loadFullData)
onUnmounted(clearPoll)
</script>

<style scoped>
.bom-detail { padding: 0; }

.el-page-header { margin-bottom: 20px; }
.status-alert { margin-bottom: 20px; }

/* stats */
.stats-row { margin-bottom: 20px; }
.stat-value { font-size: 32px; font-weight: 700; }
.c-blue   { color: #1f3a5f; }
.c-orange { color: #e67e22; }
.c-green  { color: #27ae60; }
.c-purple { color: #8e44ad; }

/* cards spacing */
.info-card, .material-card, .process-card, .fiber-card, .loading-card { margin-bottom: 20px; }

.fiber-summary { margin-bottom: 4px; }
</style>
