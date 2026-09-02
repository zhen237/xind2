<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="$emit('update:visible', $event)"
    title="天线参数化配置"
    width="520px"
  >
    <el-form :model="form" label-width="100px" size="default">
      <el-form-item label="设备名称">
        <el-input :model-value="device?.deviceName" disabled />
      </el-form-item>

      <el-divider content-position="left">天线参数</el-divider>

      <el-form-item label="方位角 (°)">
        <el-slider
          v-model="form.azimuth"
          :min="0"
          :max="360"
          :step="1"
          show-input
          :format-tooltip="v => v + '°'"
        />
      </el-form-item>

      <el-form-item label="下倾角 (°)">
        <el-slider
          v-model="form.downtilt"
          :min="-15"
          :max="15"
          :step="0.5"
          show-input
          :format-tooltip="v => v + '°'"
        />
      </el-form-item>

      <el-divider content-position="left">天线预览</el-divider>

      <div class="antenna-preview">
        <div class="preview-circle">
          <div class="preview-needle" :style="{ transform: `rotate(${form.azimuth}deg)` }">
            <div class="needle-arrow"></div>
            <span class="needle-label">{{ form.azimuth }}°</span>
          </div>
          <div class="circle-labels">
            <span class="label-n">N</span>
            <span class="label-e">E</span>
            <span class="label-s">S</span>
            <span class="label-w">W</span>
          </div>
        </div>
        <div class="preview-info">
          <div class="info-item">
            <span class="info-label">方位角:</span>
            <span class="info-value">{{ form.azimuth }}° ({{ azimuthDirection(form.azimuth) }})</span>
          </div>
          <div class="info-item">
            <span class="info-label">下倾角:</span>
            <span class="info-value">{{ form.downtilt }}° ({{ form.downtilt > 0 ? '下倾' : form.downtilt < 0 ? '上仰' : '水平' }})</span>
          </div>
          <div class="info-item">
            <span class="info-label">天线颜色:</span>
            <span class="info-value">
              <span class="color-dot" :style="{ background: deviceColor }"></span>
              {{ deviceColor }}
            </span>
          </div>
        </div>
      </div>

      <el-divider content-position="left">快速预设</el-divider>

      <div class="preset-buttons">
        <el-button size="small" @click="applyPreset(0, 0)">水平全向</el-button>
        <el-button size="small" @click="applyPreset(0, 6)">微下倾</el-button>
        <el-button size="small" @click="applyPreset(45, 3)">东北微倾</el-button>
        <el-button size="small" @click="applyPreset(90, 3)">正东微倾</el-button>
        <el-button size="small" @click="applyPreset(180, 3)">正南微倾</el-button>
        <el-button size="small" @click="applyPreset(270, 3)">正西微倾</el-button>
      </div>
    </el-form>

    <template #footer>
      <el-button @click="$emit('update:visible', false)">取消</el-button>
      <el-button type="primary" @click="handleSave">保存配置</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { DEVICE_TYPE_CONFIG } from '@/utils/cesium-config'

const props = defineProps({
  visible: { type: Boolean, default: false },
  device: { type: Object, default: null }
})

const emit = defineEmits(['update:visible', 'save'])

const form = ref({
  azimuth: 0,
  downtilt: 0
})

const deviceColor = computed(() => {
  if (!props.device) return '#F56C6C'
  return DEVICE_TYPE_CONFIG[props.device.deviceType]?.color || '#F56C6C'
})

// 监听设备变化
watch(() => props.device, (newDevice) => {
  if (newDevice) {
    form.value.azimuth = parseFloat(newDevice.azimuth) || 0
    form.value.downtilt = parseFloat(newDevice.downtilt) || 0
  }
}, { immediate: true })

// 监听对话框打开
watch(() => props.visible, (visible) => {
  if (visible && props.device) {
    form.value.azimuth = parseFloat(props.device.azimuth) || 0
    form.value.downtilt = parseFloat(props.device.downtilt) || 0
  }
})

function azimuthDirection(angle) {
  const directions = ['正北', '东北', '正东', '东南', '正南', '西南', '正西', '西北']
  const index = Math.round(angle / 45) % 8
  return directions[index]
}

function applyPreset(azimuth, downtilt) {
  form.value.azimuth = azimuth
  form.value.downtilt = downtilt
}

function handleSave() {
  emit('save', {
    ...props.device,
    azimuth: form.value.azimuth,
    downtilt: form.value.downtilt
  })
}
</script>

<style scoped>
.antenna-preview {
  display: flex;
  gap: 20px;
  align-items: center;
}

.preview-circle {
  width: 160px;
  height: 160px;
  border: 2px solid #dcdfe6;
  border-radius: 50%;
  position: relative;
  flex-shrink: 0;
  background: #f5f7fa;
}

.preview-needle {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 2px;
  height: 70px;
  background: #F56C6C;
  transform-origin: bottom center;
  transform: translate(-50%, -100%) rotate(0deg);
  transition: transform 0.3s ease;
}

.needle-arrow {
  position: absolute;
  top: -8px;
  left: 50%;
  transform: translateX(-50%);
  width: 0;
  height: 0;
  border-left: 6px solid transparent;
  border-right: 6px solid transparent;
  border-bottom: 10px solid #F56C6C;
}

.needle-label {
  position: absolute;
  top: -24px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 12px;
  color: #F56C6C;
  font-weight: bold;
  white-space: nowrap;
}

.circle-labels span {
  position: absolute;
  font-size: 12px;
  font-weight: bold;
  color: #909399;
}

.label-n { top: 4px; left: 50%; transform: translateX(-50%); }
.label-e { right: 4px; top: 50%; transform: translateY(-50%); }
.label-s { bottom: 4px; left: 50%; transform: translateX(-50%); }
.label-w { left: 4px; top: 50%; transform: translateY(-50%); }

.preview-info {
  flex: 1;
}

.info-item {
  margin-bottom: 8px;
  font-size: 14px;
}

.info-label {
  color: #909399;
  margin-right: 8px;
}

.info-value {
  color: #303133;
  font-weight: 500;
}

.color-dot {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  vertical-align: middle;
  margin-right: 4px;
}

.preset-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.el-divider {
  margin: 16px 0;
}
</style>
