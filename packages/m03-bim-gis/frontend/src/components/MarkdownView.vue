<template>
  <!-- eslint-disable-next-line vue/no-v-html -- 内容经 escapeHtml 转义后仅输出受限标签集，无 XSS 风险 -->
  <div class="md-view" v-html="rendered"></div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  source: { type: String, default: '' }
})

// 先转义 HTML，再只输出我们自己的受限标签集 —— 模型内容绝不会作为原始 HTML 注入。
function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

// 行内：粗体 / 斜体 / 行内代码
function inline(text) {
  let t = escapeHtml(text)
  t = t.replace(/`([^`]+)`/g, '<code>$1</code>')
  t = t.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  t = t.replace(/\*([^*]+)\*/g, '<em>$1</em>')
  return t
}

const rendered = computed(() => {
  const src = props.source || ''
  const lines = src.split(/\r?\n/)
  const out = []
  let inUl = false
  let inOl = false
  let inPre = false
  let paraBuf = []

  const closeLists = () => {
    if (inUl) { out.push('</ul>'); inUl = false }
    if (inOl) { out.push('</ol>'); inOl = false }
  }
  const flushPara = () => {
    if (paraBuf.length) {
      out.push('<p>' + inline(paraBuf.join(' ')) + '</p>')
      paraBuf = []
    }
  }

  for (const raw of lines) {
    const line = raw.replace(/\s+$/, '')

    // 代码围栏 ```
    if (line.trim().startsWith('```')) {
      if (inPre) { out.push('</pre>'); inPre = false }
      else { flushPara(); closeLists(); out.push('<pre>'); inPre = true }
      continue
    }
    if (inPre) { out.push(escapeHtml(line)); continue }

    if (line.trim() === '') { flushPara(); closeLists(); continue }

    // 标题 # ~ ######
    const h = line.match(/^(#{1,6})\s+(.*)$/)
    if (h) {
      flushPara(); closeLists()
      const lvl = h[1].length
      out.push(`<h${lvl}>${inline(h[2])}</h${lvl}>`)
      continue
    }

    // 无序列表 - / *
    if (/^[-*]\s+/.test(line)) {
      flushPara()
      if (inOl) { out.push('</ol>'); inOl = false }
      if (!inUl) { out.push('<ul>'); inUl = true }
      out.push('<li>' + inline(line.replace(/^[-*]\s+/, '')) + '</li>')
      continue
    }

    // 有序列表 1.
    if (/^\d+\.\s+/.test(line)) {
      flushPara()
      if (inUl) { out.push('</ul>'); inUl = false }
      if (!inOl) { out.push('<ol>'); inOl = true }
      out.push('<li>' + inline(line.replace(/^\d+\.\s+/, '')) + '</li>')
      continue
    }

    // 引用 >
    if (/^>\s?/.test(line)) {
      flushPara(); closeLists()
      out.push('<blockquote>' + inline(line.replace(/^>\s?/, '')) + '</blockquote>')
      continue
    }

    // 普通段落行
    if (inUl) { out.push('</ul>'); inUl = false }
    if (inOl) { out.push('</ol>'); inOl = false }
    paraBuf.push(line)
  }
  flushPara(); closeLists()
  if (inPre) out.push('</pre>')
  return out.join('\n')
})
</script>

<style scoped>
.md-view {
  font-size: 13px;
  line-height: 1.7;
  color: var(--text-secondary, #b0bec5);
  word-break: break-word;
}
.md-view :deep(h1),
.md-view :deep(h2),
.md-view :deep(h3),
.md-view :deep(h4) {
  color: var(--primary-color, #00d4ff);
  margin: 14px 0 6px;
  font-weight: 600;
}
.md-view :deep(h1) { font-size: 18px; }
.md-view :deep(h2) {
  font-size: 16px;
  border-bottom: 1px solid var(--border-color, rgba(0, 212, 255, 0.15));
  padding-bottom: 4px;
}
.md-view :deep(h3) { font-size: 14px; }
.md-view :deep(p) { margin: 6px 0; }
.md-view :deep(ul),
.md-view :deep(ol) { margin: 6px 0; padding-left: 22px; }
.md-view :deep(li) { margin: 2px 0; }
.md-view :deep(code) {
  background: rgba(0, 212, 255, 0.12);
  padding: 1px 5px;
  border-radius: 3px;
  font-family: monospace;
  color: #7fe7ff;
}
.md-view :deep(pre) {
  background: rgba(0, 0, 0, 0.35);
  padding: 10px 12px;
  border-radius: 6px;
  overflow-x: auto;
  line-height: 1.5;
}
.md-view :deep(strong) { color: #fff; }
.md-view :deep(blockquote) {
  border-left: 3px solid var(--primary-color, #00d4ff);
  margin: 6px 0;
  padding: 4px 10px;
  color: var(--text-muted, #7f8c8d);
}
</style>
