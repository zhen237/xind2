import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useM03Store = defineStore('m03', () => {
  // ── 状态 ──────────────────────────────────────────────────
  const currentProject = ref(null)
  const deviceList = ref([])
  const modelList = ref([])
  const regionList = ref([])
  const designStatus = ref('idle')  // idle | generating | success | error
  const lastError = ref(null)

  // ── 计算属性 ──────────────────────────────────────────────
  const deviceCount = computed(() => deviceList.value.length)
  const modelCount = computed(() => modelList.value.length)
  const hasActiveProject = computed(() => currentProject.value !== null)

  // ── 操作 ──────────────────────────────────────────────────
  function setCurrentProject(project) {
    currentProject.value = project
  }

  function clearProject() {
    currentProject.value = null
    deviceList.value = []
    modelList.value = []
    regionList.value = []
    designStatus.value = 'idle'
    lastError.value = null
  }

  function setDeviceList(list) {
    deviceList.value = list
  }

  function addDevice(device) {
    deviceList.value.push(device)
  }

  function removeDevice(id) {
    const idx = deviceList.value.findIndex(d => d.id === id)
    if (idx > -1) deviceList.value.splice(idx, 1)
  }

  function setModelList(list) {
    modelList.value = list
  }

  function setRegionList(list) {
    regionList.value = list
  }

  function setDesignStatus(status, error = null) {
    designStatus.value = status
    lastError.value = error
  }

  function reset() {
    clearProject()
  }

  return {
    // state
    currentProject,
    deviceList,
    modelList,
    regionList,
    designStatus,
    lastError,
    // getters
    deviceCount,
    modelCount,
    hasActiveProject,
    // actions
    setCurrentProject,
    clearProject,
    setDeviceList,
    addDevice,
    removeDevice,
    setModelList,
    setRegionList,
    setDesignStatus,
    reset,
  }
})
