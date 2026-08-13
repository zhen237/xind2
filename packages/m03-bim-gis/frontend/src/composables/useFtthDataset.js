// 共享的 FTTH 数据集选择器状态 (单例)
// Ftth.vue 与 FtthPlanner.vue 共用，保证「切换数据集」两处同步。
import { ref } from 'vue'

const base = import.meta.env.BASE_URL

// 当前选中的数据集 tag；空串 '' 表示回退到 public/ 根目录(旧默认)
const currentTag = ref('')
// 数据集清单 [{ tag, label, source, generated_at, summary }]
const datasets = ref([])
const loaded = ref(false)

async function loadIndex() {
  if (loaded.value) return
  try {
    const res = await fetch(base + 'datasets/index.json')
    if (res.ok) {
      const j = await res.json()
      datasets.value = j.datasets || []
      // 默认选中第一个真实数据集(列表按 tag 字典序，竣工数据在前)
      if (!currentTag.value && datasets.value.length) {
        currentTag.value = datasets.value[0].tag
      }
    }
  } catch (e) {
    console.error('数据集索引加载失败', e)
  } finally {
    loaded.value = true
  }
}

// 返回某个交付物文件在当前数据集下的 URL
function path(file) {
  return base + (currentTag.value ? 'datasets/' + currentTag.value + '/' : '') + file
}

export function useFtthDataset() {
  return { base, currentTag, datasets, loaded, loadIndex, path }
}
