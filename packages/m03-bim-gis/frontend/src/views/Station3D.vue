<template>
  <div class="station-3d-page">
    <!-- 顶部 -->
    <div class="station-header">
      <el-button :icon="ArrowLeft" size="small" @click="$router.back()">返回</el-button>
      <span class="page-title">基站3D场景</span>
      <div class="header-actions">
        <el-select v-model="selectedDeviceId" placeholder="选择设备定位" size="small" style="width: 180px" @change="locateDevice">
          <el-option
            v-for="device in devices"
            :key="device.id"
            :label="device.deviceName"
            :value="device.id"
          />
        </el-select>
        <el-button size="small" :icon="Aim" @click="resetCamera">重置视角</el-button>
      </div>
    </div>

    <!-- 三维场景 -->
    <CesiumStationScene
      ref="sceneRef"
      :project-id="projectId"
      :center-lng="centerLng"
      :center-lat="centerLat"
      :zoom="17"
      :devices="devices"
      :models="models"
      @ready="onSceneReady"
    />

    <!-- 设备列表面板 -->
    <div class="device-panel panel">
      <div class="panel-title">设备列表 ({{ devices.length }})</div>
      <div class="device-scroll">
        <div
          v-for="device in devices"
          :key="device.id"
          class="device-card"
          @click="focusDevice(device)"
        >
          <div class="device-card-header">
            <span class="device-dot" :style="{ background: getTypeColor(device.deviceType) }"></span>
            <span class="device-card-name">{{ device.deviceName }}</span>
          </div>
          <div class="device-card-info">
            <span>{{ getTypeLabel(device.deviceType) }}</span>
            <span v-if="device.azimuth">{{ device.azimuth }}°</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 碰撞检测面板 -->
    <div class="collision-panel panel">
      <div class="panel-title">
        碰撞检测
        <el-button size="small" type="primary" :icon="Search" @click="runCollisionCheck" :loading="checking" style="margin-left: 8px;">
          检测
        </el-button>
      </div>
      <div v-if="collisionResult" class="collision-result">
        <el-alert
          :title="collisionResult.hasCollision ? `发现 ${collisionResult.collisions.length} 处碰撞` : '未发现碰撞'"
          :type="collisionResult.hasCollision ? 'error' : 'success'"
          :closable="false"
          style="margin-bottom: 8px;"
        />
        <div v-for="(col, idx) in collisionResult.collisions" :key="idx" class="collision-item">
          <el-icon color="#F56C6C"><Warning /></el-icon>
          <span>{{ col.deviceA }} ↔ {{ col.deviceB }}</span>
          <span class="collision-dist">{{ col.distance }}m</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Aim, Search, Warning } from '@element-plus/icons-vue'
import CesiumStationScene from '@/components/CesiumStationScene.vue'
import { DEVICE_TYPE_CONFIG } from '@/utils/cesium-config'
import deviceApi from '@/api/device'
import modelApi from '@/api/model'

const route = useRoute()
const projectId = route.params.projectId

const sceneRef = ref(null)
const devices = ref([])
const models = ref([])
const selectedDeviceId = ref(null)
const checking = ref(false)
const collisionResult = ref(null)

const centerLng = ref(114.4263)
const centerLat = ref(30.4925)

let viewer = null
let Cesium = null

function getTypeColor(type) {
  return DEVICE_TYPE_CONFIG[type]?.color || '#909399'
}

function getTypeLabel(type) {
  return DEVICE_TYPE_CONFIG[type]?.label || type
}

async function loadDevices() {
  try {
    const res = await deviceApi.listByProject(projectId)
    devices.value = res.data || []
    if (devices.value.length > 0) {
      centerLng.value = parseFloat(devices.value[0].lng)
      centerLat.value = parseFloat(devices.value[0].lat)
    }
  } catch (error) {
    ElMessage.error('加载设备失败')
  }
}

async function loadModels() {
  try {
    const res = await modelApi.listByType()
    models.value = res.data || []
  } catch {
    console.warn('加载模型失败')
  }
}

function onSceneReady({ viewer: v, Cesium: C }) {
  viewer = v
  Cesium = C
}

function focusDevice(device) {
  sceneRef.value?.flyToDevice(device.id)
}

function locateDevice(deviceId) {
  if (deviceId) {
    sceneRef.value?.flyToDevice(deviceId)
  }
}

function resetCamera() {
  if (viewer && Cesium) {
    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(centerLng.value, centerLat.value, 800),
      orientation: {
        heading: Cesium.Math.toRadians(0),
        pitch: Cesium.Math.toRadians(-45),
        roll: 0
      },
      duration: 1.5
    })
  }
}

/**
 * 碰撞检测 — 基于设备间距离判断
 */
function runCollisionCheck() {
  if (devices.value.length < 2) {
    ElMessage.warning('设备数量不足，无法检测碰撞')
    return
  }

  checking.value = true

  try {
    const collisions = []
    const minDistances = {
      // 不同设备类型之间的最小安全距离 (m)
      'ANTENNA-ANTENNA': 2.0,
      'ANTENNA-CABINET': 3.0,
      'CABINET-CABINET': 1.0,
      'TOWER-TOWER': 10.0,
      'CABLE-CABLE': 0.5
    }

    for (let i = 0; i < devices.value.length; i++) {
      for (let j = i + 1; j < devices.value.length; j++) {
        const a = devices.value[i]
        const b = devices.value[j]

        const aLng = parseFloat(a.lng)
        const aLat = parseFloat(a.lat)
        const bLng = parseFloat(b.lng)
        const bLat = parseFloat(b.lat)

        // 计算平面距离
        const dx = (bLng - aLng) * 111000 * Math.cos(aLat * Math.PI / 180)
        const dy = (bLat - aLat) * 111000
        const distance = Math.sqrt(dx * dx + dy * dy)

        // 获取最小安全距离
        const typeKey = [a.deviceType, b.deviceType].sort().join('-')
        const minDist = minDistances[typeKey] || 2.0

        if (distance < minDist) {
          collisions.push({
            deviceA: a.deviceName,
            deviceB: b.deviceName,
            distance: distance.toFixed(2),
            minDistance: minDist
          })
        }
      }
    }

    collisionResult.value = {
      hasCollision: collisions.length > 0,
      collisions
    }

    if (collisions.length === 0) {
      ElMessage.success('碰撞检测完成，未发现碰撞')
    } else {
      ElMessage.warning(`发现 ${collisions.length} 处碰撞`)
    }
  } catch (error) {
    ElMessage.error('碰撞检测失败: ' + error.message)
  } finally {
    checking.value = false
  }
}

onMounted(() => {
  loadDevices()
  loadModels()
})
</script>

<style scoped>
.station-3d-page {
  width: 100%;
  height: 100vh;
  position: relative;
  overflow: hidden;
}

.station-header {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 48px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 16px;
  z-index: 1001;
}

.page-title {
  font-size: 15px;
  font-weight: bold;
  flex: 1;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.device-panel {
  position: absolute;
  top: 60px;
  left: 16px;
  width: 240px;
  max-height: 400px;
  padding: 12px;
  z-index: 1000;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.panel-title {
  font-size: 13px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
}

.device-scroll {
  overflow-y: auto;
  flex: 1;
}

.device-card {
  padding: 8px;
  border-radius: 4px;
  cursor: pointer;
  margin-bottom: 4px;
  transition: background 0.2s;
}

.device-card:hover {
  background: #f5f7fa;
}

.device-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.device-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.device-card-name {
  font-size: 13px;
  font-weight: 500;
}

.device-card-info {
  font-size: 11px;
  color: #909399;
  margin-left: 16px;
  display: flex;
  gap: 8px;
}

.collision-panel {
  position: absolute;
  bottom: 16px;
  left: 16px;
  width: 300px;
  max-height: 300px;
  padding: 12px;
  z-index: 1000;
  overflow-y: auto;
}

.collision-result {
  margin-top: 8px;
}

.collision-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  font-size: 13px;
  border-bottom: 1px dashed #ebeef5;
}

.collision-dist {
  margin-left: auto;
  color: #F56C6C;
  font-weight: bold;
}
</style>
