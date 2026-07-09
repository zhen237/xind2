/**
 * useCrudTable — 通用 CRUD 表格 Composable
 *
 * 封装 Models/Regions 等管理页面共 95% 的重复逻辑:
 *   - 列表加载/保存状态管理
 *   - 创建/编辑对话框生命周期
 *   - 表单验证 + API 调用 + 错误处理 + 消息提示
 *   - 前端搜索过滤计算属性
 *   - 分页状态（预留）
 *
 * 使用示例:
 *   const {
 *     items, loading, saving, searchQuery,
 *     dialogVisible, isEditing, formRef, form,
 *     filteredItems, handleSave, handleDelete, fetchItems,
 *     showCreateDialog, showEditDialog, resetForm
 *   } = useCrudTable({
 *     api: modelAPI,
 *     entityName: '模型',
 *     initialForm: { modelName: '', modelCode: '', modelType: '' },
 *     searchFields: ['modelName', 'modelCode', 'modelType'],
 *     onFetchSuccess: (items) => { ... },
 *   })
 */

import { ref, computed, onMounted, isRef } from 'vue'
import { ElMessage } from 'element-plus'

/**
 * @param {Object} options
 * @param {Object} options.api          - 包含 list/create/update/delete 方法的 API 对象
 * @param {string} options.entityName   - 实体名称（用于消息提示，如 "模型"、"区域"）
 * @param {Object|Function} options.initialForm - 表单初始值对象，或在重置时调用的函数
 * @param {string[]} options.searchFields      - 用于前端搜索的字段名列表
 * @param {Function} [options.onFetchSuccess]  - 每次 fetchItems 成功后的回调
 * @param {Object} [options.formRules]         - 可选的表单验证规则（也可在组件中定义）
 * @param {Object} [options.extraState]        - 额外的响应式状态（如 modelTypes）
 * @param {boolean} [options.autoFetch=true]   - 是否在 onMounted 时自动拉取数据
 */
export function useCrudTable(options) {
  const {
    api,
    entityName,
    initialForm,
    searchFields = [],
    onFetchSuccess,
    autoFetch = true,
  } = options

  if (!api) throw new Error('[useCrudTable] api is required')
  if (!entityName) throw new Error('[useCrudTable] entityName is required')
  if (!initialForm) throw new Error('[useCrudTable] initialForm is required')

  // ── 响应式状态 ────────────────────────────────────────────
  const loading = ref(false)
  const saving = ref(false)
  const items = ref([])
  const searchQuery = ref('')

  // 对话框状态
  const dialogVisible = ref(false)
  const isEditing = ref(false)
  const editingId = ref(null)
  const formRef = ref(null)

  const form = ref(
    typeof initialForm === 'function' ? initialForm() : { ...initialForm }
  )

  // 分页状态（预留）
  const pagination = ref({
    current: 1,
    pageSize: 20,
    total: 0,
  })

  // ── 计算属性 ──────────────────────────────────────────────

  /** 前端搜索过滤 */
  const filteredItems = computed(() => {
    let result = items.value
    const query = searchQuery.value.trim().toLowerCase()
    if (!query) return result

    if (searchFields.length > 0) {
      result = result.filter(item =>
        searchFields.some(field => {
          const val = item[field]
          return val != null && String(val).toLowerCase().includes(query)
        })
      )
    }
    return result
  })

  // ── 方法 ──────────────────────────────────────────────────

  /** 重置表单到初始状态 */
  function resetForm() {
    form.value = typeof initialForm === 'function'
      ? initialForm()
      : { ...initialForm }
    formRef.value?.clearValidate?.()
    isEditing.value = false
    editingId.value = null
  }

  /** 打开创建对话框 */
  function showCreateDialog() {
    resetForm()
    dialogVisible.value = true
  }

  /** 打开编辑对话框（用行数据填充表单） */
  function showEditDialog(row) {
    resetForm()
    isEditing.value = true
    editingId.value = row.id
    // 浅合并: 只填充 initialForm 中定义的字段
    const keys = Object.keys(form.value)
    const data = {}
    for (const key of keys) {
      data[key] = row[key] ?? form.value[key]
    }
    form.value = data
    dialogVisible.value = true
  }

  /** 保存（创建/更新） */
  async function handleSave() {
    const valid = await formRef.value?.validate().catch(() => false)
    if (!valid) return

    saving.value = true
    try {
      if (isEditing.value) {
        await api.update(editingId.value, form.value)
        ElMessage.success(`${entityName}已更新`)
      } else {
        await api.create(form.value)
        ElMessage.success(`${entityName}已添加`)
      }
      dialogVisible.value = false
      await fetchItems()
    } catch (e) {
      ElMessage.error(`操作失败: ${e?.message || '未知错误'}`)
    } finally {
      saving.value = false
    }
  }

  /** 删除 */
  async function handleDelete(id) {
    try {
      await api.delete(id)
      ElMessage.success('已删除')
      items.value = items.value.filter(item => item.id !== id)
    } catch (e) {
      ElMessage.error('删除失败')
    }
  }

  /** 拉取列表 */
  async function fetchItems() {
    loading.value = true
    try {
      const res = await api.list()
      items.value = res?.data || res?.items || []
      if (onFetchSuccess) {
        onFetchSuccess(items.value)
      }
    } catch (e) {
      ElMessage.error(`获取${entityName}列表失败`)
    } finally {
      loading.value = false
    }
  }

  // ── 生命周期 ──────────────────────────────────────────────
  if (autoFetch) {
    onMounted(() => {
      fetchItems()
    })
  }

  // ── 返回 ──────────────────────────────────────────────────
  return {
    // 状态
    loading,
    saving,
    items,
    searchQuery,
    pagination,

    // 对话框
    dialogVisible,
    isEditing,
    editingId,
    formRef,
    form,

    // 计算属性
    filteredItems,

    // 方法
    resetForm,
    showCreateDialog,
    showEditDialog,
    handleSave,
    handleDelete,
    fetchItems,
  }
}

export default useCrudTable
