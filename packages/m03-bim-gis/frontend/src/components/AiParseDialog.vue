<template>
  <el-dialog
    v-model="visible"
    title="AI 解析设计需求"
    width="540px"
    align-center
    @open="onOpen"
  >
    <div class="ai-parse">
      <p class="ai-tip">
        用一句话描述你的设计意图，AI 会解析为结构化参数。确认结果后可一步生成三维通信基站方案。
      </p>
      <el-input
        v-model="text"
        type="textarea"
        :rows="4"
        maxlength="4000"
        show-word-limit
        placeholder="例如：在运城学院建一个宏基站，站高30米，覆盖半径500米，频段FDD-LTE-1800，三扇区，城区"
      />
      <div class="ai-actions">
        <el-button
          type="primary"
          :loading="loading"
          @click="doParse"
        >
          <el-icon><MagicStick /></el-icon> 解析为设计参数
        </el-button>
      </div>

      <el-alert
        v-if="error"
        :title="error"
        type="warning"
        :closable="false"
        class="ai-alert"
      />

      <div
        v-if="params"
        class="ai-result"
      >
        <div class="ai-result-title">
          解析结果
        </div>
        <el-descriptions
          :column="1"
          border
          size="small"
        >
          <el-descriptions-item
            v-for="f in fields"
            :key="f.key"
            :label="f.label"
          >
            {{ formatVal(params[f.key]) }}<span
              v-if="isMissing(f.key)"
              class="ai-default-tag"
            >（默认）</span>
          </el-descriptions-item>
        </el-descriptions>
        <p class="ai-default-note">
          标 <b>（默认）</b> 的字段为 AI 未明确识别，将使用系统默认值；可关闭后在左侧表单手动修改。
        </p>
        <div class="ai-fill">
          <el-button @click="fillForm">
            <el-icon><Check /></el-icon> 仅填入表单
          </el-button>
          <el-button
            type="primary"
            @click="parseAndGenerate"
          >
            <el-icon><MagicStick /></el-icon> 解析并生成方案
          </el-button>
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { llmAPI } from '@/utils/request.js'

const props = defineProps({ modelValue: Boolean })
const emit = defineEmits(['update:modelValue', 'apply', 'generate'])

const visible = computed({
  get: () => props.modelValue,
  set: v => emit('update:modelValue', v)
})

const text = ref('')
const loading = ref(false)
const error = ref('')
const params = ref(null)

const fields = [
  { key: 'template_type', label: '基站类型' },
  { key: 'center_longitude', label: '中心经度' },
  { key: 'center_latitude', label: '中心纬度' },
  { key: 'coverage_radius', label: '覆盖半径(m)' },
  { key: 'frequency_band', label: '频段' },
  { key: 'tower_height', label: '铁塔高度(m)' },
  { key: 'antenna_height', label: '天线挂高(m)' },
  { key: 'sector_count', label: '扇区数' },
  { key: 'scenario', label: '场景' },
  { key: 'site_count', label: '站点数' },
  { key: 'notes', label: '补充说明' }
]

function formatVal(v) {
  if (v === null || v === undefined || v === '') return '—'
  return v
}

// AI 未明确识别的字段 → 标注（默认）
function isMissing(key) {
  const v = params.value?.[key]
  return v === null || v === undefined || v === ''
}

function onOpen() {
  error.value = ''
  params.value = null
}

async function doParse() {
  const t = text.value.trim()
  if (!t) {
    ElMessage.warning('请先输入设计需求描述')
    return
  }
  loading.value = true
  error.value = ''
  try {
    const res = await llmAPI.parseDesignParams(t)
    if (res && res.code === 200 && res.data && res.data.params) {
      params.value = res.data.params
    } else if (res && res.code === 503) {
      error.value = '大模型服务未配置（缺少 LLM_API_KEY），请在服务器注入密钥后重试'
    } else {
      error.value = (res && res.message) || '解析失败，请稍后重试'
    }
  } catch (e) {
    const status = e?.response?.status
    error.value = (status >= 500 || status === 503)
      ? '大模型服务当前不可用，请检查服务端是否已启动并配置 LLM_API_KEY'
      : '解析请求失败：' + (e?.response?.data?.message || e.message || e)
  } finally {
    loading.value = false
  }
}

function fillForm() {
  emit('apply', params.value)
  visible.value = false
  ElMessage.success('已填入左侧表单，可点「生成覆盖方案」预览')
}

function parseAndGenerate() {
  emit('generate', params.value)
  visible.value = false
  ElMessage.success('已解析参数，正在生成三维通信基站方案...')
}
</script>

<style scoped>
.ai-tip {
  margin: 0 0 10px;
  font-size: 12px;
  color: var(--text-muted, #7f8c8d);
  line-height: 1.6;
}
.ai-actions {
  margin-top: 10px;
  display: flex;
  justify-content: flex-end;
}
.ai-alert {
  margin-top: 10px;
}
.ai-result {
  margin-top: 12px;
}
.ai-result-title {
  font-size: 12px;
  color: var(--primary-color, #00d4ff);
  margin-bottom: 6px;
  font-weight: 600;
}
.ai-fill {
  margin-top: 10px;
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}
.ai-fill .el-button {
  flex: 1;
}
.ai-default-tag {
  margin-left: 6px;
  color: var(--el-color-warning, #e6a23c);
  font-size: 11px;
}
.ai-default-note {
  margin: 8px 0 0;
  font-size: 11px;
  color: var(--text-muted, #7f8c8d);
  line-height: 1.5;
}
</style>
