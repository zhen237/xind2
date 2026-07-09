/**
 * 工作流引导组件
 * 为新用户提供交互式操作引导
 */

<template>
  <teleport to="body">
    <div 
      v-if="isVisible" 
      class="workflow-guide-overlay"
      @click.self="handleNext"
    >
      <!-- 引导遮罩 -->
      <div class="guide-mask" :style="maskStyle" />
      
      <!-- 引导提示框 -->
      <div 
        class="guide-tooltip"
        :class="{ 'guide-enter': isAnimating }"
        :style="tooltipStyle"
      >
        <!-- 步骤指示器 -->
        <div class="guide-steps">
          <el-badge
            v-for="(step, index) in steps"
            :key="index"
            :value="index + 1"
            :max="9"
            :class="{ 
              'step-active': currentStep === index,
              'step-completed': index < currentStep
            }"
          />
        </div>
        
        <!-- 引导内容 -->
        <div class="guide-content">
          <h3 class="guide-title">
            <el-icon><Reading /></el-icon>
            {{ currentStepData.title }}
          </h3>
          <p class="guide-description">{{ currentStepData.content }}</p>
          
          <!-- 高亮目标元素 -->
          <div 
            v-if="currentStepData.target"
            class="guide-highlight"
            :ref="setHighlightRef"
          />
        </div>
        
        <!-- 操作按钮 -->
        <div class="guide-actions">
          <el-button 
            v-if="currentStep > 0"
            @click="handlePrev"
            :icon="ArrowLeft"
          >
            上一步
          </el-button>
          
          <el-button 
            type="primary"
            @click="handleNext"
            :icon="ArrowRight"
            :loading="isProcessing"
          >
            {{ currentStep === steps.length - 1 ? '完成' : '下一步' }}
          </el-button>
          
          <el-button 
            text
            @click="skipGuide"
          >
            跳过引导
          </el-button>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script>
export default { name: 'WorkflowGuide' }
</script>
<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { Reading, ArrowLeft, ArrowRight } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

// 定时器追踪
const _timers = []
const _safeTimeout = (fn, delay) => {
  const id = setTimeout(() => {
    const idx = _timers.indexOf(id)
    if (idx > -1) _timers.splice(idx, 1)
    fn()
  }, delay)
  _timers.push(id)
  return id
}
import { ElMessage } from 'element-plus'

const props = defineProps({
  steps: {
    type: Array,
    required: true,
    validator: (steps) => {
      return steps.every(step => 
        step.title && step.content && step.target
      )
    }
  },
  autoStart: {
    type: Boolean,
    default: true
  },
  onComplete: {
    type: Function,
    default: null
  }
})

const isVisible = ref(false)
const currentStep = ref(0)
const isAnimating = ref(false)
const isProcessing = ref(false)
const highlightRef = ref(null)

// 当前步骤数据
const currentStepData = computed(() => {
  return props.steps[currentStep.value] || {}
})

// 遮罩样式
const maskStyle = computed(() => {
  const target = currentStepData.value.target
  if (!target) return {}
  
  const element = document.querySelector(target)
  if (!element) return {}
  
  const rect = element.getBoundingClientRect()
  
  return {
    clipPath: `polygon(
      0% 0%, 
      100% 0%, 
      100% 100%, 
      0% 100%
    )`
  }
})

// 提示框样式
const tooltipStyle = computed(() => {
  const target = currentStepData.value.target
  if (!target) return {}
  
  const element = document.querySelector(target)
  if (!element) return {}
  
  const rect = element.getBoundingClientRect()
  
  return {
    top: `${rect.bottom + 20}px`,
    left: `${rect.left}px`,
    width: `${Math.min(rect.width * 2, 400)}px`
  }
})

// 设置高亮引用
const setHighlightRef = (el) => {
  highlightRef.value = el
}

// 显示引导
const showGuide = () => {
  // 检查是否已完成引导
  const completed = localStorage.getItem('m03_guide_completed')
  if (completed && !props.autoStart) {
    return
  }
  
  isVisible.value = true
  currentStep.value = 0
  
  if (props.autoStart) {
    startAutoPlay()
  }
}

// 隐藏引导
const hideGuide = () => {
  isVisible.value = false
  localStorage.setItem('m03_guide_completed', 'true')
  
  if (props.onComplete) {
    props.onComplete()
  }
}

// 下一步
const handleNext = async () => {
  if (currentStep.value >= props.steps.length - 1) {
    hideGuide()
    return
  }
  
  isAnimating.value = true
  isProcessing.value = true
  
  // 执行步骤动作
  const step = currentStepData.value
  if (step.action === 'click') {
    const element = document.querySelector(step.target)
    if (element) {
      element.click()
      await sleep(500)
    }
  }
  
  currentStep.value++
  isProcessing.value = false
  
  _safeTimeout(() => {
    isAnimating.value = false
  }, 300)
  
  // 自动播放下一步
  if (currentStep.value < props.steps.length - 1) {
    _safeTimeout(() => handleNext(), 1000)
  }
}

// 上一步
const handlePrev = () => {
  if (currentStep.value > 0) {
    currentStep.value--
  }
}

// 跳过引导
const skipGuide = () => {
  hideGuide()
  ElMessage.info('已跳过引导，可随时点击 "?" 查看快捷键')
}

// 自动播放
const startAutoPlay = () => {
  _safeTimeout(() => {
    handleNext()
  }, 1500)
}
}

// 睡眠函数
const sleep = (ms) => {
  return new Promise(resolve => setTimeout(resolve, ms))
}

// 暴露方法给父组件
defineExpose({
  showGuide,
  hideGuide
})

// 组件挂载时检查
onMounted(() => {
  if (props.autoStart) {
    const completed = localStorage.getItem('m03_guide_completed')
    if (!completed) {
      showGuide()
    }
  }
})

// 组件卸载时清理所有定时器
onUnmounted(() => {
  _timers.forEach(id => clearTimeout(id))
  _timers.length = 0
})
</script>

<style scoped>
.workflow-guide-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 9999;
  pointer-events: none;
}

.guide-mask {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.6);
  pointer-events: auto;
}

.guide-tooltip {
  position: absolute;
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  pointer-events: auto;
  z-index: 10000;
  max-width: 400px;
}

.guide-enter {
  animation: guideEnter 0.3s ease-out;
}

@keyframes guideEnter {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.guide-steps {
  display: flex;
  gap: 8px;
  margin-bottom: 15px;
}

.step-active {
  color: #409eff;
  font-weight: bold;
}

.step-completed {
  color: #67c23a;
}

.guide-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 10px 0;
  font-size: 16px;
  color: #303133;
}

.guide-description {
  margin: 0 0 15px 0;
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
}

.guide-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 15px;
}
</style>
