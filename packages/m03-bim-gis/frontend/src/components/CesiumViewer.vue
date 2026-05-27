<template>
  <div class="cesium-container">
    <div ref="cesiumContainer" class="cesium-viewer"></div>
    
    <div class="cesium-toolbar">
      <button @click="flyToDefault" class="btn btn-primary">
        <span class="icon">📍</span> 初始视角
      </button>
      <button @click="toggleAddMode" class="btn btn-success" :class="{ active: addMode }">
        <span class="icon">📡</span> {{ addMode ? '取消添加' : '添加天线' }}
      </button>
      <button @click="toggleTerrain" class="btn btn-secondary" :class="{ active: terrainEnabled }">
        <span class="icon">🏔️</span> 地形 {{ terrainEnabled ? '开' : '关' }}
      </button>
      <button @click="toggleLabels" class="btn btn-secondary" :class="{ active: labelsEnabled }">
        <span class="icon">🏷️</span> 标签 {{ labelsEnabled ? '开' : '关' }}
      </button>
      <button @click="clearSelection" class="btn btn-danger">
        <span class="icon">🗑️</span> 清除选择
      </button>
    </div>

    <div class="cesium-info" v-if="selectedRegion">
      <h4>{{ selectedRegion.properties.name }}</h4>
      <p>设备数量: {{ getRegionDeviceCount(selectedRegion.properties.id) }}</p>
      <button @click="loadRegion3DTiles" class="btn btn-primary btn-sm">
        加载三维模型
      </button>
    </div>

    <div class="device-modal" v-if="showDeviceModal" @click.self="closeDeviceModal">
      <div class="modal-content">
        <h3>添加天线设备</h3>
        <div class="form-group">
          <label>设备名称</label>
          <input v-model="newDevice.name" type="text" placeholder="输入设备名称" />
        </div>
        <div class="form-group">
          <label>高度 (米)</label>
          <input v-model.number="newDevice.height" type="number" placeholder="设备高度" />
        </div>
        <div class="form-group">
          <label>坐标</label>
          <p>{{ newDevice.longitude.toFixed(6) }}, {{ newDevice.latitude.toFixed(6) }}</p>
        </div>
        <div class="modal-actions">
          <button @click="confirmAddDevice" class="btn btn-primary">确认添加</button>
          <button @click="closeDeviceModal" class="btn btn-secondary">取消</button>
        </div>
      </div>
    </div>

    <div class="region-list">
      <h4>区域列表</h4>
      <ul>
        <li v-for="region in regions" :key="region.properties.id" 
            @click="selectRegion(region)"
            :class="{ active: selectedRegion?.properties.id === region.properties.id }">
          {{ region.properties.name }}
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, reactive } from 'vue'
import * as Cesium from 'cesium'

const props = defineProps({
  devices: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['device-added', 'device-deleted'])

const cesiumContainer = ref(null)
let viewer = null
let deviceEntities = []
let regionEntities = []
let tileset = null

const terrainEnabled = ref(true)
const labelsEnabled = ref(true)
const addMode = ref(false)
const selectedRegion = ref(null)
const showDeviceModal = ref(false)

const newDevice = reactive({
  name: '',
  longitude: 0,
  latitude: 0,
  height: 10
})

// 天地图密钥，如过期请前往 https://console.tianditu.gov.cn/ 重新申请
const TIANDITU_TOKEN = '6b7c32c253463ca594b92b8476662675'

const regions = [
  {
    type: 'Feature',
    properties: {
      id: 'region1',
      name: '北京市朝阳区',
      tilesetUrl: 'https://assets.cesium.com/3836/tileset.json'
    },
    geometry: {
      type: 'Polygon',
      coordinates: [[
        [116.400, 39.900],
        [116.500, 39.900],
        [116.500, 40.000],
        [116.400, 40.000],
        [116.400, 39.900]
      ]]
    }
  },
  {
    type: 'Feature',
    properties: {
      id: 'region2',
      name: '北京市海淀区',
      tilesetUrl: 'https://assets.cesium.com/4086/tileset.json'
    },
    geometry: {
      type: 'Polygon',
      coordinates: [[
        [116.250, 39.950],
        [116.350, 39.950],
        [116.350, 40.050],
        [116.250, 40.050],
        [116.250, 39.950]
      ]]
    }
  },
  {
    type: 'Feature',
    properties: {
      id: 'region3',
      name: '北京市西城区',
      tilesetUrl: 'https://assets.cesium.com/4117/tileset.json'
    },
    geometry: {
      type: 'Polygon',
      coordinates: [[
        [116.350, 39.900],
        [116.450, 39.900],
        [116.450, 39.950],
        [116.350, 39.950],
        [116.350, 39.900]
      ]]
    }
  }
]

const initCesium = () => {
  Cesium.Ion.defaultAccessToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiI3NzUyMjkzMC02OWQyLTQyMjgtODAxNy04MzY0NDI4N2U1ZjIiLCJpZCI6MTM4MDQ4LCJpYXQiOjE2OTUyMzc5NDh9.A921h5tW5bF9hZ9E5cV8h8h8h8h8h8h8h8h8h8h8'

  viewer = new Cesium.Viewer(cesiumContainer.value, {
    terrainProvider: terrainEnabled.value 
      ? new Cesium.EllipsoidTerrainProvider()
      : undefined,
    baseLayerPicker: false,
    geocoder: false,
    homeButton: false,
    sceneModePicker: true,
    navigationHelpButton: false,
    animation: false,
    timeline: false,
    fullscreenButton: false
  })

  addTiandituLayers()
  
  viewer.scene.globe.depthTestAgainstTerrain = true
  
  flyToDefault()
  
  addRegionPolygons()
  
  addDevices()
  
  setupClickHandler()
}

const addTiandituLayers = () => {
  const imageryLayers = viewer.imageryLayers
  
  const baseLayer = new Cesium.UrlTemplateImageryProvider({
    url: `https://t{s}.tianditu.gov.cn/img_w/wmts?service=WMTS&request=GetTile&version=1.0.0&LAYER=img&tileMatrixSet=w&TileMatrix={z}&TileRow={y}&TileCol={x}&style=default&format=tiles&tk=${TIANDITU_TOKEN}`,
    subdomains: ['0', '1', '2', '3', '4', '5', '6', '7'],
    maximumLevel: 18,
    credit: '天地图'
  })
  imageryLayers.addImageryProvider(baseLayer)

  const labelLayer = new Cesium.UrlTemplateImageryProvider({
    url: `https://t{s}.tianditu.gov.cn/cia_w/wmts?service=WMTS&request=GetTile&version=1.0.0&LAYER=cia&tileMatrixSet=w&TileMatrix={z}&TileRow={y}&TileCol={x}&style=default&format=tiles&tk=${TIANDITU_TOKEN}`,
    subdomains: ['0', '1', '2', '3', '4', '5', '6', '7'],
    maximumLevel: 18,
    credit: '天地图注记'
  })
  imageryLayers.addImageryProvider(labelLayer)
}

const flyToDefault = () => {
  if (viewer) {
    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(116.4074, 39.9042, 10000),
      orientation: {
        heading: Cesium.Math.toRadians(0),
        pitch: Cesium.Math.toRadians(-45),
        roll: 0
      },
      duration: 3
    })
  }
}

const addRegionPolygons = () => {
  regionEntities.forEach(entity => {
    viewer.entities.remove(entity)
  })
  regionEntities = []

  regions.forEach(region => {
    const positions = region.geometry.coordinates[0].map(coord => 
      Cesium.Cartesian3.fromDegrees(coord[0], coord[1])
    )

    const polygon = viewer.entities.add({
      name: region.properties.name,
      regionId: region.properties.id,
      polygon: {
        hierarchy: new Cesium.PolygonHierarchy(positions),
        material: Cesium.Color.fromCssColorString(getRegionColor(region.properties.id)).withAlpha(0.3),
        outline: true,
        outlineColor: Cesium.Color.WHITE,
        outlineWidth: 3
      }
    })

    if (labelsEnabled.value) {
      const center = getPolygonCenter(region.geometry.coordinates[0])
      viewer.entities.add({
        position: Cesium.Cartesian3.fromDegrees(center[0], center[1]),
        label: {
          text: region.properties.name,
          font: '16pt sans-serif',
          fillColor: Cesium.Color.WHITE,
          outlineColor: Cesium.Color.BLACK,
          outlineWidth: 3,
          style: Cesium.LabelStyle.FILL_AND_OUTLINE,
          verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
          pixelOffset: new Cesium.Cartesian2(0, -20)
        }
      })
    }

    regionEntities.push(polygon)
  })
}

const getRegionColor = (regionId) => {
  const colors = {
    'region1': '#ff4444',
    'region2': '#4444ff',
    'region3': '#44ff44'
  }
  return colors[regionId] || '#ff4444'
}

const getPolygonCenter = (coordinates) => {
  let minLon = Infinity, maxLon = -Infinity
  let minLat = Infinity, maxLat = -Infinity
  
  coordinates.forEach(coord => {
    minLon = Math.min(minLon, coord[0])
    maxLon = Math.max(maxLon, coord[0])
    minLat = Math.min(minLat, coord[1])
    maxLat = Math.max(maxLat, coord[1])
  })
  
  return [(minLon + maxLon) / 2, (minLat + maxLat) / 2]
}

const addDevices = () => {
  deviceEntities.forEach(entity => {
    viewer.entities.remove(entity)
  })
  deviceEntities = []

  props.devices.forEach(device => {
    if (!device.longitude || !device.latitude) return

    const entity = viewer.entities.add({
      name: device.deviceName || '天线设备',
      deviceId: device.id,
      position: Cesium.Cartesian3.fromDegrees(device.longitude, device.latitude, device.height || 0),
      billboard: {
        image: getAntennaIcon(),
        width: 40,
        height: 40,
        scale: 1.5,
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM
      },
      label: labelsEnabled.value ? {
        text: device.deviceName || '天线',
        font: '12pt sans-serif',
        fillColor: Cesium.Color.WHITE,
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 2,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        pixelOffset: new Cesium.Cartesian2(0, -45)
      } : undefined,
      description: `<div style="padding: 10px;">
        <h4>${device.deviceName || '天线设备'}</h4>
        <p>类型: ${device.deviceType || '天线'}</p>
        <p>高度: ${device.height || 0}米</p>
        <p>状态: ${device.status || '正常'}</p>
      </div>`
    })

    deviceEntities.push(entity)
  })
}

const getAntennaIcon = () => {
  return 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzIiIGhlaWdodD0iMzIiIHZpZXdCb3g9IjAgMCAzMiAzMiIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cGF0aCBkPSJNMTYgMmMtNy43MzIgMC0xNCA2LjI2OC0xNCAxNHM2LjI2OCAxNCAxNCAxNCAxNC02LjI2OCAxNC0xNC02LjI2OC0xNC0xNC0xNHptMCAyNGMtNS41MjMgMC0xMC00LjQ3Ny0xMC0xMHM0LjQ3Ny0xMCAxMC0xMCAxMCA0LjQ3NyAxMCAxMC00LjQ3NyAxMC0xMCAxMHptLTItMTRjLTEuMTEgMC0yLS44OS0yLTJzLjg5LTIgMi0yIDIgLjg5IDIgMi0uODkgMi0yIDJ6Ii8+PC9zdmc+'
}

const setupClickHandler = () => {
  viewer.screenSpaceEventHandler.setInputAction(function(click) {
    const pick = viewer.scene.pick(click.position)
    
    if (addMode.value) {
      const cartesian = viewer.camera.pickEllipsoid(click.position, viewer.scene.globe.ellipsoid)
      if (cartesian) {
        const cartographic = Cesium.Cartographic.fromCartesian(cartesian)
        newDevice.longitude = Cesium.Math.toDegrees(cartographic.longitude)
        newDevice.latitude = Cesium.Math.toDegrees(cartographic.latitude)
        showDeviceModal.value = true
      }
      return
    }

    if (Cesium.defined(pick) && pick.id) {
      const entity = pick.id
      
      if (entity.regionId) {
        selectedRegion.value = regions.find(r => r.properties.id === entity.regionId)
      } else if (entity.deviceId) {
        viewer.selectedEntity = entity
      }
    } else {
      selectedRegion.value = null
      viewer.selectedEntity = undefined
    }
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK)
}

const toggleAddMode = () => {
  addMode.value = !addMode.value
  if (!addMode.value) {
    closeDeviceModal()
  }
}

const closeDeviceModal = () => {
  showDeviceModal.value = false
  newDevice.name = ''
  newDevice.height = 10
}

const confirmAddDevice = async () => {
  if (!newDevice.name.trim()) {
    alert('请输入设备名称')
    return
  }

  const deviceData = {
    deviceCode: `ANT-${Date.now()}`,
    deviceName: newDevice.name,
    deviceType: '天线',
    longitude: newDevice.longitude,
    latitude: newDevice.latitude,
    height: newDevice.height,
    status: 'normal'
  }

  try {
    await fetch('/api/m03/device', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(deviceData)
    })
    
    emit('device-added', deviceData)
    closeDeviceModal()
    addMode.value = false
    
    const entity = viewer.entities.add({
      name: deviceData.deviceName,
      deviceId: Date.now(),
      position: Cesium.Cartesian3.fromDegrees(deviceData.longitude, deviceData.latitude, deviceData.height),
      billboard: {
        image: getAntennaIcon(),
        width: 40,
        height: 40,
        scale: 1.5,
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM
      },
      label: labelsEnabled.value ? {
        text: deviceData.deviceName,
        font: '12pt sans-serif',
        fillColor: Cesium.Color.WHITE,
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 2,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        pixelOffset: new Cesium.Cartesian2(0, -45)
      } : undefined
    })
    deviceEntities.push(entity)
    
    alert('设备添加成功！')
  } catch (error) {
    console.error('添加设备失败:', error)
    alert('添加设备失败，请重试')
  }
}

const loadRegion3DTiles = () => {
  if (!selectedRegion.value) return

  if (tileset) {
    viewer.scene.primitives.remove(tileset)
    tileset = null
  }

  const tilesetUrl = selectedRegion.value.properties.tilesetUrl
  
  viewer.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(
      ...getPolygonCenter(selectedRegion.value.geometry.coordinates[0]),
      5000
    ),
    duration: 2
  })

  setTimeout(() => {
    tileset = viewer.scene.primitives.add(
      new Cesium.Cesium3DTileset({ url: tilesetUrl })
    )
    
    tileset.readyPromise.then(() => {
      viewer.zoomTo(tileset)
    }).catch(error => {
      console.error('加载3D Tiles失败:', error)
      alert('加载三维模型失败，将使用默认模型')
    })
  }, 2000)
}

const selectRegion = (region) => {
  selectedRegion.value = region
  const center = getPolygonCenter(region.geometry.coordinates[0])
  viewer.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(center[0], center[1], 3000),
    duration: 2
  })
}

const getRegionDeviceCount = (regionId) => {
  const bounds = regions.find(r => r.properties.id === regionId)?.geometry.coordinates[0]
  if (!bounds) return 0
  
  let count = 0
  props.devices.forEach(device => {
    if (isPointInPolygon(device.longitude, device.latitude, bounds)) {
      count++
    }
  })
  return count
}

const isPointInPolygon = (lon, lat, polygon) => {
  let inside = false
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const xi = polygon[i][0], yi = polygon[i][1]
    const xj = polygon[j][0], yj = polygon[j][1]
    
    if (((yi > lat) !== (yj > lat)) &&
        (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi)) {
      inside = !inside
    }
  }
  return inside
}

const toggleTerrain = () => {
  terrainEnabled.value = !terrainEnabled.value
  viewer.terrainProvider = terrainEnabled.value
    ? new Cesium.EllipsoidTerrainProvider()
    : undefined
}

const toggleLabels = () => {
  labelsEnabled.value = !labelsEnabled.value
  addDevices()
  addRegionPolygons()
}

const clearSelection = () => {
  selectedRegion.value = null
  viewer.selectedEntity = undefined
  if (tileset) {
    viewer.scene.primitives.remove(tileset)
    tileset = null
  }
}

onMounted(() => {
  initCesium()
})

onUnmounted(() => {
  if (viewer) {
    viewer.destroy()
  }
})
</script>

<style scoped>
.cesium-container {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.cesium-viewer {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

.cesium-toolbar {
  position: absolute;
  top: 20px;
  left: 20px;
  z-index: 1000;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  background: rgba(0, 0, 0, 0.8);
  padding: 12px;
  border-radius: 8px;
  pointer-events: auto;
}

.btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.3s;
  color: white;
}

.btn-primary {
  background: #1e90ff;
}

.btn-primary:hover {
  background: #4169e1;
}

.btn-success {
  background: #22c55e;
}

.btn-success:hover,
.btn-success.active {
  background: #16a34a;
  box-shadow: 0 0 15px rgba(34, 197, 94, 0.5);
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.btn-secondary:hover,
.btn-secondary.active {
  background: rgba(255, 255, 255, 0.3);
}

.btn-danger {
  background: #ef4444;
}

.btn-danger:hover {
  background: #dc2626;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 12px;
}

.icon {
  font-size: 16px;
}

.cesium-info {
  position: absolute;
  bottom: 20px;
  left: 20px;
  z-index: 1000;
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 15px 20px;
  border-radius: 8px;
  pointer-events: auto;
}

.cesium-info h4 {
  margin: 0 0 10px 0;
  font-size: 16px;
}

.cesium-info p {
  margin: 5px 0;
  font-size: 14px;
  opacity: 0.8;
}

.region-list {
  position: absolute;
  top: 20px;
  right: 20px;
  z-index: 1000;
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 15px;
  border-radius: 8px;
  min-width: 150px;
  pointer-events: auto;
}

.region-list h4 {
  margin: 0 0 10px 0;
  font-size: 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
  padding-bottom: 8px;
}

.region-list ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.region-list li {
  padding: 8px 10px;
  cursor: pointer;
  border-radius: 4px;
  transition: background 0.2s;
}

.region-list li:hover {
  background: rgba(255, 255, 255, 0.1);
}

.region-list li.active {
  background: #1e90ff;
}

.device-modal {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 2000;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: auto;
}

.modal-content {
  background: white;
  padding: 30px;
  border-radius: 12px;
  min-width: 350px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
}

.modal-content h3 {
  margin: 0 0 20px 0;
  color: #333;
  font-size: 18px;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: 500;
  color: #555;
}

.form-group input {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  box-sizing: border-box;
}

.form-group input:focus {
  outline: none;
  border-color: #1e90ff;
}

.form-group p {
  margin: 0;
  padding: 10px;
  background: #f5f5f5;
  border-radius: 4px;
  font-family: monospace;
  font-size: 12px;
  color: #666;
}

.modal-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 20px;
}

.modal-actions .btn-primary {
  color: white;
}

.modal-actions .btn-secondary {
  background: #f0f0f0;
  color: #333;
}

.modal-actions .btn-secondary:hover {
  background: #e0e0e0;
}
</style>