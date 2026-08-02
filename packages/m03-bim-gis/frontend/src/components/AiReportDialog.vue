<template>
  <el-dialog
    v-model="visible"
    title="AI 生成设计报告"
    width="760px"
    align-center
    @open="onOpen"
  >
    <div class="ai-report">
      <div
        v-if="!hasData"
        class="ai-report-empty"
      >
        <el-alert
          type="info"
          :closable="false"
          title="暂无可生成报告的设计数据"
          description="请先在左侧「加载数据」并「生成方案」，待设计信息与站点列表就绪后再生成报告。"
        />
      </div>

      <template v-else>
        <div class="ai-report-meta">
          将基于「{{ schemeName }}」共 {{ siteCount }} 个站点生成评审 / 交付报告
        </div>
        <div class="ai-report-actions">
          <el-button
            type="primary"
            :loading="loading"
            @click="doGenerate"
          >
            <el-icon><Document /></el-icon> 生成报告
          </el-button>
        </div>

        <el-alert
          v-if="error"
          :title="error"
          type="warning"
          :closable="false"
          class="ai-report-alert"
        />

        <div
          v-if="report"
          class="ai-report-body"
        >
          <MarkdownView :source="report" />
        </div>
        <el-empty
          v-else-if="!loading"
          description="点击「生成报告」开始"
          :image-size="80"
        />
      </template>
    </div>
  </el-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import { llmAPI } from '@/utils/request.js'
import MarkdownView from '@/components/MarkdownView.vue'

const props = defineProps({
  modelValue: Boolean,
  designInfo: { type: Object, default: null },
  sites: { type: Array, default: () => [] }
})
const emit = defineEmits(['update:modelValue'])

const visible = computed({
  get: () => props.modelValue,
  set: v => emit('update:modelValue', v)
})

const loading = ref(false)
const error = ref('')
const report = ref('')

const hasData = computed(() => !!props.designInfo || (props.sites && props.sites.length))
const schemeName = computed(() => props.designInfo?.schemeName || props.designInfo?.projectId || '未命名方案')
const siteCount = computed(() => props.sites?.length || 0)

function onOpen() {
  error.value = ''
  report.value = ''
}

function buildScheme() {
  const di = props.designInfo || {}
  return {
    projectId: di.projectId,
    schemeName: di.schemeName,
    frequencyBand: di.frequencyBand,
    towerHeight: di.towerHeight,
    totalSites: di.totalSites,
    validSites: di.validSites,
    invalidSites: di.invalidSites,
    siteCount: props.sites?.length || 0,
    sites: (props.sites || []).map(s => ({
      siteId: s.siteId,
      longitude: s.longitude,
      latitude: s.latitude,
      towerHeight: s.towerHeight,
      rsrp: s.rsrp,
      isValid: s.isValid
    }))
  }
}

async function doGenerate() {
  loading.value = true
  error.value = ''
  try {
    const scheme = buildScheme()
    const res = await llmAPI.generateReport(scheme)
    if (res && res.code === 200 && res.data && res.data.report_markdown) {
      report.value = res.data.report_markdown
    } else if (res && res.code === 503) {
      error.value = '大模型服务未配置（缺少 LLM_API_KEY），请在服务器注入密钥后重试'
    } else {
      error.value = (res && res.message) || '报告生成失败，请稍后重试'
    }
  } catch (e) {
    const status = e?.response?.status
    error.value = (status >= 500 || status === 503)
      ? '大模型服务当前不可用，请检查服务端是否已启动并配置 LLM_API_KEY'
      : '生成请求失败：' + (e?.response?.data?.message || e.message || e)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.ai-report-meta {
  font-size: 12px;
  color: var(--text-muted, #7f8c8d);
  margin-bottom: 8px;
}
.ai-report-actions {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 10px;
}
.ai-report-alert {
  margin-bottom: 10px;
}
.ai-report-body {
  max-height: 60vh;
  overflow-y: auto;
  border: 1px solid var(--border-color, rgba(0, 212, 255, 0.12));
  border-radius: 6px;
  padding: 12px 14px;
  background: rgba(0, 0, 0, 0.2);
}
</style>
