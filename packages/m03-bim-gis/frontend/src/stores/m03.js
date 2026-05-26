import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useM03Store = defineStore('m03', () => {
  const currentProject = ref(null)
  const deviceList = ref([])
  const modelList = ref([])

  function setCurrentProject(project) {
    currentProject.value = project
  }

  function setDeviceList(list) {
    deviceList.value = list
  }

  function setModelList(list) {
    modelList.value = list
  }

  return {
    currentProject,
    deviceList,
    modelList,
    setCurrentProject,
    setDeviceList,
    setModelList
  }
})
