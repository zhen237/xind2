<script setup>
/**
 * AI 助手（DeepSeek）——独立菜单页。
 * 对话经后端 /api/s5/ai/chat 代理，DeepSeek Key 只在后端 .env，前端不接触。
 * 助手 system prompt 注入了看板/设备/告警快照，可问"有几台设备报警"等监管数据问题。
 */
import { ref, nextTick, onMounted } from 'vue'
import { marked } from 'marked'
import { sendAiChat } from '../api/s5.js'

const SUPPORT_COUNT = 6 // 随请求携带的历史轮数上限
const EXAMPLES = ['当前有几台设备在报警？', '塔吊设备状态怎么样？', '帮我总结一下看板数据', 'AI 助手能做什么？']

// 简易 HTML 清理：拦截 script 标签与事件属性（demo 级防护，不引重型消毒库）
function sanitizeHtml(html) {
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, '')
    .replace(/\son\w+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, '')
}

function renderMd(text) {
  return sanitizeHtml(marked.parse(text))
}

const messages = ref([]) // { role: 'user' | 'assistant', content }
const input = ref('')
const sending = ref(false)
const listRef = ref(null)

const scrollToBottom = async () => {
  await nextTick()
  const sb = listRef.value
  if (sb) sb.setScrollTop(sb.wrap$.scrollHeight)
}

/** 组装对话历史（去掉 system/error 后最近几轮） */
function buildHistory() {
  return messages.value
    .filter((m) => m.role === 'user' || m.role === 'assistant')
    .slice(-SUPPORT_COUNT * 2)
    .map((m) => ({ role: m.role, content: m.content }))
}

async function send(text) {
  const q = (text ?? input.value).trim()
  if (!q || sending.value) return
  input.value = ''
  messages.value.push({ role: 'user', content: q })
  scrollToBottom()
  sending.value = true
  try {
    const data = await sendAiChat({ message: q, history: buildHistory() })
    messages.value.push({ role: 'assistant', content: data.reply })
  } catch (e) {
    messages.value.push({
      role: 'assistant',
      content: '⚠️ ' + (e?.response?.data?.message || e?.message || '请求失败，请稍后重试'),
      error: true
    })
  } finally {
    sending.value = false
    scrollToBottom()
  }
}

function onEnter(e) {
  if (e.shiftKey) return // Shift+Enter 换行
  e.preventDefault()
  send()
}

onMounted(() => {
  const first = document.querySelector('.assistant-input textarea')
  if (first) first.focus()
})
</script>

<template>
  <div class="assistant">
    <div class="assistant-body">
      <!-- 空态：示例问题 -->
      <div v-if="messages.length === 0" class="empty">
        <el-icon class="empty-icon" :size="52"><ChatDotRound /></el-icon>
        <h3>S5 AI 助手</h3>
        <p>接入 DeepSeek，可查看设备/告警/看板实时数据。试试下面的问题：</p>
        <div class="examples">
          <el-tag
            v-for="q in EXAMPLES"
            :key="q"
            class="example"
            effect="plain"
            size="large"
            @click="send(q)"
          >{{ q }}</el-tag>
        </div>
      </div>

      <!-- 消息列表 -->
      <el-scrollbar ref="listRef" class="msg-scroll" always>
        <div class="msg-list">
          <div v-for="(m, i) in messages" :key="i" class="msg" :class="m.role === 'user' ? 'is-user' : 'is-ai'">
            <div class="bubble" :class="{ 'has-error': m.error }">
              <span v-if="m.role === 'user'">{{ m.content }}</span>
              <span v-else-if="m.error">{{ m.content }}</span>
              <div v-else class="markdown" v-html="renderMd(m.content)"></div>
            </div>
          </div>

          <!-- 思考中占位 -->
          <div v-if="sending" class="msg is-ai">
            <div class="bubble thinking">
              <span class="dot"></span><span class="dot"></span><span class="dot"></span>
              正在思考…
            </div>
          </div>
        </div>
      </el-scrollbar>
    </div>

    <!-- 输入区 -->
    <div class="assistant-input">
      <el-input
        v-model="input"
        type="textarea"
        :rows="2"
        resize="none"
        placeholder="向 AI 助手提问，Enter 发送，Shift+Enter 换行"
        :disabled="sending"
        @keydown.enter="onEnter"
      />
      <el-button type="primary" :icon="'Promotion'" :loading="sending" :disabled="sending" @click="send()">
        发送
      </el-button>
    </div>
  </div>
</template>

<style scoped>
.assistant {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 120px);
  gap: 12px;
}
.assistant-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: #f7f8fa;
  border-radius: 8px;
  overflow: hidden;
}
.empty {
  margin: auto;
  text-align: center;
  padding: 24px;
  max-width: 640px;
}
.empty-icon { color: #1890ff; }
.empty h3 { margin: 12px 0 6px; }
.empty p { color: #909399; margin: 0 0 16px; }
.examples { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; }
.example { cursor: pointer; font-size: 14px; }
.msg-scroll { height: 100%; }
.msg-list { padding: 16px; }
.msg { display: flex; margin-bottom: 14px; }
.msg.is-user { justify-content: flex-end; }
.msg.is-ai { justify-content: flex-start; }
.bubble {
  max-width: 78%;
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 14px;
  line-height: 1.7;
  word-break: break-word;
  white-space: pre-wrap;
}
.is-user .bubble { background: #1890ff; color: #fff; border-top-right-radius: 2px; }
.is-ai .bubble { background: #fff; border: 1px solid #e4e7ed; border-top-left-radius: 2px; }
.bubble.has-error { background: #fef0f0; color: #f56c6c; border-color: #fbc4c4; }
.thinking { color: #909399; display: flex; align-items: center; gap: 6px; }
.dot {
  width: 6px; height: 6px; border-radius: 50%; background: #909399;
  animation: blink 1.2s infinite;
}
.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes blink { 0%, 80%, 100% { opacity: 0.2; } 40% { opacity: 1; } }

/* AI 回复的 markdown 样式 */
.markdown { white-space: normal; }
.markdown :deep(p) { margin: 0 0 8px; }
.markdown :deep(p:last-child) { margin-bottom: 0; }
.markdown :deep(h1), .markdown :deep(h2), .markdown :deep(h3), .markdown :deep(h4) { margin: 10px 0 6px; font-size: 15px; }
.markdown :deep(ul), .markdown :deep(ol) { padding-left: 20px; margin: 4px 0; }
.markdown :deep(li) { margin: 2px 0; }
.markdown :deep(code) {
  background: #f0f2f5; padding: 1px 6px; border-radius: 4px;
  font-family: Consolas, Monaco, monospace; font-size: 13px;
}
.markdown :deep(pre) {
  background: #282c34; color: #abb2bf; padding: 10px 12px; border-radius: 6px;
  overflow-x: auto; margin: 8px 0;
}
.markdown :deep(pre code) { background: transparent; padding: 0; color: inherit; }
.markdown :deep(table) { border-collapse: collapse; margin: 8px 0; }
.markdown :deep(th), .markdown :deep(td) { border: 1px solid #dcdfe6; padding: 4px 10px; font-size: 13px; }
.markdown :deep(blockquote) { border-left: 3px solid #1890ff; margin: 6px 0; padding-left: 10px; color: #606266; }
.markdown :deep(a) { color: #1890ff; }

.assistant-input { display: flex; align-items: flex-end; gap: 10px; }
.assistant-input .el-textarea { flex: 1; }
</style>
