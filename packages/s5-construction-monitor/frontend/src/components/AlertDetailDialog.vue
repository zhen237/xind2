<script setup>
import { computed } from 'vue'
import { alertLevelLabel, alertLevelType, alertStatusLabel, alertStatusType, fmtTime } from '../utils/labels'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  alert: { type: Object, default: null }
})
const emit = defineEmits(['update:modelValue'])

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v)
})
</script>

<template>
  <el-dialog v-model="visible" title="告警详情" width="560px" append-to-body>
    <template v-if="alert">
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="告警内容" :span="2">{{ alert.alertContent || '-' }}</el-descriptions-item>
        <el-descriptions-item label="设备编码">{{ alert.deviceCode || '-' }}</el-descriptions-item>
        <el-descriptions-item label="工单号">{{ alert.orderNo || '-' }}</el-descriptions-item>
        <el-descriptions-item label="级别">
          <el-tag :type="alertLevelType(alert.level)" size="small">{{ alertLevelLabel(alert.level) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="alertStatusType(alert.status)" size="small">{{ alertStatusLabel(alert.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="来源" :span="2">{{ alert.source || '-' }}</el-descriptions-item>
        <el-descriptions-item label="告警时间" :span="2">{{ fmtTime(alert.createTime) }}</el-descriptions-item>
        <el-descriptions-item v-if="alert.updateTime" label="处理时间" :span="2">{{ fmtTime(alert.updateTime) }}</el-descriptions-item>
        <el-descriptions-item label="处置建议" :span="2">
          <div style="line-height:1.6">
            <el-tag size="small" type="warning" effect="plain" style="margin-bottom:4px">{{ alert.suggestionNote || '规则建议' }}</el-tag>
            <div>{{ alert.suggestion || '暂无' }}</div>
          </div>
        </el-descriptions-item>
      </el-descriptions>
    </template>
  </el-dialog>
</template>
