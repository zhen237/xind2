<template>
  <div class="design-page">
    <el-card class="toolbar-card">
      <div class="toolbar">
        <div class="left-tools">
          <el-button :type="addMode ? 'primary' : 'default'" @click="toggleAddMode">
            {{ addMode ? '退出添加' : '添加模式' }}
          </el-button>
          <el-button :type="mapMode === '3D' ? 'primary' : 'default'" @click="toggleMapMode('3D')">3D视图</el-button>
          <el-button :type="mapMode === 'STATION' ? 'primary' : 'default'" @click="toggleMapMode('STATION')">基站环境</el-button>
          <el-button v-if="mapMode === '3D'" @click="zoomIn">放大</el-button>
          <el-button v-if="mapMode === '3D'" @click="zoomOut">缩小</el-button>
          <el-button v-if="mapMode === '3D'" @click="resetView">复位</el-button>
          <el-button v-if="mapMode === 'STATION'" @click="backToMap">返回地图</el-button>
        </div>
        <div class="center-tools" v-if="addMode">
          <el-tag type="warning">添加模式：点击地图选择位置，可多次点击调整</el-tag>
        </div>
        <div class="center-tools" v-if="mapMode === 'STATION' && selectedStation">
          <el-tag type="success">当前基站：{{ selectedStation.name }}</el-tag>
        </div>
      </div>
    </el-card>

    <div class="main-content">
      <div v-if="mapMode === '3D'" class="map-container" ref="mapContainer"></div>
      
      <div v-else-if="mapMode === 'STATION'" class="station-container" ref="stationContainer">
        <div class="station-3d" id="cesiumContainer"></div>
      </div>
      
      <div class="side-panel">
        <el-card title="设备列表" class="device-list-card">
          <div class="search-bar">
            <el-input 
              v-model="searchKeyword" 
              placeholder="搜索设备名称" 
              prefix-icon="search"
            />
          </div>
          <div class="device-list">
            <div 
              v-for="device in filteredDevices" 
              :key="device.id" 
              class="device-item"
            >
              <div class="device-info">
                <span class="device-name">{{ device.name }}</span>
                <span class="device-coord">
                  {{ device.lng.toFixed(5) }}, {{ device.lat.toFixed(5) }}
                </span>
              </div>
              <div class="device-actions">
                <el-button v-if="mapMode === '3D'" size="small" @click="locateDevice(device)">定位</el-button>
                <el-button v-if="mapMode === '3D'" size="small" type="primary" @click="enterStation(device)">进入基站</el-button>
                <el-button v-if="mapMode === '3D'" size="small" type="danger" @click="deleteDevice(device)">删除</el-button>
              </div>
            </div>
            <div v-if="filteredDevices.length === 0" class="empty-state">
              暂无设备数据
            </div>
          </div>
        </el-card>

        <el-card title="天线设备列表" v-if="mapMode === 'STATION'" class="antenna-card">
          <div class="antenna-list">
            <div 
              v-for="antenna in stationAntennas" 
              :key="antenna.id" 
              class="antenna-item"
            >
              <div class="antenna-info">
                <span class="antenna-name">{{ antenna.name }}</span>
                <span class="antenna-type">{{ antenna.type }}</span>
              </div>
              <div class="antenna-actions">
                <el-button size="small" @click="locateAntenna(antenna)">查看</el-button>
                <el-button size="small" type="primary" @click="editAntenna(antenna)">编辑</el-button>
                <el-button size="small" type="danger" @click="deleteAntenna(antenna)">删除</el-button>
              </div>
            </div>
            <div v-if="stationAntennas.length === 0" class="empty-state">
              暂无天线设备
            </div>
          </div>
          <el-button type="primary" class="add-antenna-btn" @click="handleAddAntennaClick">
            + 添加天线设备
          </el-button>
        </el-card>

        <el-card title="3D模式说明" v-if="mapMode === '3D'">
          <div class="tips">
            <p><strong>3D模式操作：</strong></p>
            <ul>
              <li>鼠标左键拖拽：旋转视角</li>
              <li>鼠标滚轮：缩放</li>
              <li>鼠标右键拖拽：平移</li>
              <li>点击"进入基站"查看基站环境</li>
            </ul>
          </div>
        </el-card>

        <el-card title="基站环境说明" v-if="mapMode === 'STATION'">
          <div class="tips">
            <p><strong>基站环境操作：</strong></p>
            <ul>
              <li>鼠标左键拖拽：旋转视角</li>
              <li>鼠标滚轮：缩放</li>
              <li>鼠标右键拖拽：平移</li>
              <li>点击"添加天线设备"添加新设备</li>
            </ul>
          </div>
        </el-card>
      </div>
    </div>

    <div v-if="addMode" class="add-device-panel">
      <el-card title="添加设备" class="add-card">
        <el-form :model="pendingDevice" label-width="70px">
          <el-form-item label="设备名称">
            <el-input v-model="pendingDevice.name" placeholder="请输入设备名称" />
          </el-form-item>
          <el-form-item label="经度">
            <el-input v-model.number="pendingDevice.lng" :disabled="true" />
          </el-form-item>
          <el-form-item label="纬度">
            <el-input v-model.number="pendingDevice.lat" :disabled="true" />
          </el-form-item>
          <div class="form-actions">
            <el-button @click="cancelAddDevice">取消添加</el-button>
            <el-button type="primary" @click="confirmAddDevice">保存设备</el-button>
          </div>
        </el-form>
        <div class="tips-text">
          <p>💡 提示：点击地图上的位置可以移动红色标记点</p>
        </div>
      </el-card>
    </div>

    <div v-if="showAntennaDialog" class="custom-modal-overlay" @click.self="showAntennaDialog = false">
      <div class="custom-modal">
        <div class="custom-modal-header">
          <span class="custom-modal-title">{{ antennaForm.id ? '编辑天线设备' : '添加天线设备' }}</span>
          <button class="custom-modal-close" @click="showAntennaDialog = false">×</button>
        </div>
        <div class="custom-modal-body">
          <div class="form-item">
            <label>天线名称</label>
            <input v-model="antennaForm.name" class="form-input" placeholder="请输入天线名称" />
          </div>
          <div class="form-item">
            <label>天线类型</label>
            <select v-model="antennaForm.type" class="form-select">
              <option value="全向天线">全向天线</option>
              <option value="定向天线">定向天线</option>
              <option value="智能天线">智能天线</option>
            </select>
          </div>
          <div class="form-item">
            <label>天线高度</label>
            <input type="number" v-model="antennaForm.height" class="form-input" min="1" max="100" />
          </div>
          <div class="form-item">
            <label>位置X</label>
            <input type="number" v-model="antennaForm.x" class="form-input" step="0.5" />
          </div>
          <div class="form-item">
            <label>位置Y</label>
            <input type="number" v-model="antennaForm.y" class="form-input" step="0.5" />
          </div>
          <div class="form-item">
            <label>位置Z</label>
            <input type="number" v-model="antennaForm.z" class="form-input" step="0.5" />
          </div>
          <div class="form-item">
            <label>模型缩放</label>
            <input type="number" v-model="antennaForm.scale" class="form-input" min="0.1" max="10" step="0.1" />
          </div>
          <div class="form-item">
            <label>模型文件</label>
            <div>
              <button class="file-upload-btn" @click="triggerFileUpload">选择本地 glb 文件</button>
              <input 
                type="file" 
                ref="fileInput" 
                accept=".glb" 
                style="display: none" 
                @change="handleFileUpload"
              />
            </div>
            <input v-model="antennaForm.modelFile" class="form-input" placeholder="已选模型文件" style="margin-top: 10px;" />
            <div class="model-tips">
              <p>🎯 已下载模型：</p>
              <ul>
                <li>old_antenna.glb</li>
                <li>low_poly_building.glb</li>
              </ul>
            </div>
          </div>
        </div>
        <div class="custom-modal-footer">
          <button class="modal-btn modal-btn-cancel" @click="showAntennaDialog = false">取消</button>
          <button class="modal-btn modal-btn-primary" @click="confirmAddAntenna">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import request from '../../utils/request';

const mapContainer = ref(null);
const stationContainer = ref(null);
const addMode = ref(false);
const searchKeyword = ref('');
const devices = ref([]);
const markers = ref([]);
const mapMode = ref('3D');
const showAntennaDialog = ref(false);
const selectedStation = ref(null);
const stationAntennas = ref([]);
const cesiumViewer = ref(null);
const cesiumEntities = ref([]);
const fileInput = ref(null);
const uploadedModels = ref([]);

const pendingDevice = ref({
  name: '',
  lng: 116.397428,
  lat: 39.90923
});

const antennaForm = ref({
  name: '',
  type: '全向天线',
  height: 10,
  x: 0,
  y: 0,
  z: 5,
  scale: 1,
  modelFile: 'old_antenna.glb'
});

let map = null;
let tempMarker = null;
const AMap_KEY = '508bd9aba42a7f37dc25e8be995d10fc';

const filteredDevices = computed(() => {
  if (!searchKeyword.value) return devices.value;
  return devices.value.filter(device => 
    device.name.toLowerCase().includes(searchKeyword.value.toLowerCase())
  );
});

const initMap = () => {
  if (!mapContainer.value) return;
  
  const script = document.createElement('script');
  script.src = `https://webapi.amap.com/maps?v=2.0&key=${AMap_KEY}&callback=initAMap`;
  script.type = 'text/javascript';
  document.head.appendChild(script);
  
  window.initAMap = () => {
    map = new AMap.Map(mapContainer.value, {
      zoom: 14,
      center: [116.397428, 39.90923],
      viewMode: '3D',
      resizeEnable: true,
      toolbar: true,
      pitch: 45,
      rotation: 0,
      terrain: false
    });

    AMap.plugin(['AMap.Scale', 'AMap.HawkEye', 'AMap.ControlBar'], () => {
      map.addControl(new AMap.Scale());
      map.addControl(new AMap.HawkEye());
      map.addControl(new AMap.ControlBar({
        showZoomBar: true,
        showControlButton: true
      }));
    });

    map.on('click', handleMapClick);
    loadDevices();
  };
};

const loadDevices = async () => {
  try {
    const response = await request.get('/m03/device/list');
    devices.value = response.data || response;
    updateMarkers();
  } catch (e) {
    console.error('加载设备失败:', e);
    devices.value = [
      { id: 1, name: '测试基站A', lng: 116.397428, lat: 39.90923, type: 'station' },
      { id: 2, name: '测试基站B', lng: 116.407428, lat: 39.91923, type: 'station' },
      { id: 3, name: '测试基站C', lng: 116.387428, lat: 39.89923, type: 'station' }
    ];
    updateMarkers();
  }
};

const updateMarkers = () => {
  if (!map) return;
  markers.value.forEach(marker => {
    map.remove(marker);
  });
  markers.value = [];
  devices.value.forEach(device => {
    addMarker(device);
  });
};

const addMarker = (device) => {
  if (!map) return;
  const marker = new AMap.Marker({
    position: [device.lng, device.lat],
    title: device.name,
    icon: 'https://webapi.amap.com/theme/v1.3/markers/n/mark_b.png',
    elevation: 10
  });
  
  marker.on('mouseover', () => {
    marker.setLabel({
      content: `<div style="padding: 4px 8px; background: white; border: 1px solid #ccc; border-radius: 4px; font-size: 12px;">${device.name}</div>`,
      offset: new AMap.Pixel(0, -30)
    });
  });
  
  marker.on('mouseout', () => {
    marker.setLabel(null);
  });
  
  marker.on('click', () => {
    if (!addMode.value) {
      locateDevice(device);
    }
  });
  
  map.add(marker);
  markers.value.push(marker);
};

const removeTempMarker = () => {
  if (tempMarker && map) {
    map.remove(tempMarker);
    tempMarker = null;
  }
};

const updateTempMarker = (lng, lat) => {
  removeTempMarker();
  if (!map) return;
  
  tempMarker = new AMap.Marker({
    position: [lng, lat],
    title: '待添加设备',
    icon: 'https://webapi.amap.com/theme/v1.3/markers/n/mark_r.png',
    elevation: 15,
    animation: 'AMAP_ANIMATION_DROP'
  });
  
  tempMarker.setLabel({
    content: `<div style="padding: 4px 8px; background: #409EFF; color: white; border-radius: 4px; font-size: 12px;">点击确认位置</div>`,
    offset: new AMap.Pixel(0, -35)
  });
  
  map.add(tempMarker);
};

const handleMapClick = (e) => {
  const lnglat = e.lnglat;
  
  if (addMode.value) {
    const lng = lnglat.getLng();
    const lat = lnglat.getLat();
    
    pendingDevice.value = {
      ...pendingDevice.value,
      lng: lng,
      lat: lat
    };
    
    updateTempMarker(lng, lat);
  }
};

const toggleAddMode = () => {
  addMode.value = !addMode.value;
  
  if (addMode.value) {
    const center = map.getCenter();
    pendingDevice.value = {
      name: '',
      lng: center.lng,
      lat: center.lat
    };
    updateTempMarker(center.lng, center.lat);
  } else {
    removeTempMarker();
  }
};

const cancelAddDevice = () => {
  if (addMode.value) {
    const center = map.getCenter();
    pendingDevice.value = {
      name: '',
      lng: center.lng,
      lat: center.lat
    };
    updateTempMarker(center.lng, center.lat);
  }
};

const confirmAddDevice = async () => {
  if (!pendingDevice.value.name) {
    ElMessage.warning('请输入设备名称');
    return;
  }
  
  try {
    const response = await request.post('/m03/device', {
      name: pendingDevice.value.name,
      lng: pendingDevice.value.lng,
      lat: pendingDevice.value.lat,
      type: 'station'
    });
    const newDevice = response.data || { 
      ...pendingDevice.value, 
      id: Date.now(),
      type: 'station'
    };
    devices.value.push(newDevice);
    updateMarkers();
    pendingDevice.value = { name: '', lng: 116.397428, lat: 39.90923 };
    removeTempMarker();
    addMode.value = false;
    ElMessage.success('设备添加成功');
  } catch (e) {
    console.error('添加设备失败:', e);
    devices.value.push({
      id: Date.now(),
      name: pendingDevice.value.name,
      lng: pendingDevice.value.lng,
      lat: pendingDevice.value.lat,
      type: 'station'
    });
    updateMarkers();
    pendingDevice.value = { name: '', lng: 116.397428, lat: 39.90923 };
    removeTempMarker();
    addMode.value = false;
    ElMessage.success('设备添加成功（本地模拟）');
  }
};

const locateDevice = (device) => {
  if (!map) return;
  map.setZoom(18);
  map.setCenter([device.lng, device.lat]);
  
  const marker = markers.value.find(m => {
    const pos = m.getPosition();
    return pos && pos.getLng() === device.lng && pos.getLat() === device.lat;
  });
  
  if (marker) {
    marker.setAnimation('AMAP_ANIMATION_BOUNCE');
    setTimeout(() => {
      marker.setAnimation(null);
    }, 1500);
  }
};

const enterStation = (device) => {
  selectedStation.value = device;
  mapMode.value = 'STATION';
  nextTick(() => {
    initCesium();
    loadStationAntennas();
  });
};

const backToMap = () => {
  selectedStation.value = null;
  mapMode.value = '3D';
  if (cesiumViewer.value) {
    cesiumViewer.value.destroy();
    cesiumViewer.value = null;
  }
};

const deleteDevice = async (device) => {
  ElMessage.confirm('确定删除该设备吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await request.delete(`/m03/device/${device.id}`);
      const index = devices.value.findIndex(d => d.id === device.id);
      if (index > -1) {
        devices.value.splice(index, 1);
      }
      updateMarkers();
      ElMessage.success('删除成功');
    } catch (e) {
      console.error('删除设备失败:', e);
      const index = devices.value.findIndex(d => d.id === device.id);
      if (index > -1) {
        devices.value.splice(index, 1);
      }
      updateMarkers();
      ElMessage.success('删除成功（本地模拟）');
    }
  }).catch(() => {
    ElMessage.info('已取消删除');
  });
};

const zoomIn = () => {
  if (map) {
    map.zoomIn();
  }
};

const zoomOut = () => {
  if (map) {
    map.zoomOut();
  }
};

const resetView = () => {
  if (map) {
    map.setZoom(14);
    map.setCenter([116.397428, 39.90923]);
    map.setPitch(45);
    map.setRotation(0);
  }
};

const toggleMapMode = (mode) => {
  if (mapMode.value === mode) return;
  
  if (mode === 'STATION') {
    ElMessage.warning('请先在地图上选择一个基站，点击"进入基站"按钮');
    return;
  }
  
  mapMode.value = mode;
  if (mode === '3D') {
    selectedStation.value = null;
    if (cesiumViewer.value) {
      cesiumViewer.value.destroy();
      cesiumViewer.value = null;
    }
    nextTick(() => {
      if (!map) {
        initMap();
      }
    });
  }
};

const addGridBackground = (lng, lat) => {
  if (!cesiumViewer.value) return;
  
  const gridSize = 100;
  const step = 10;
  
  for (let i = -gridSize; i <= gridSize; i += step) {
    // 创建水平网格线
    const hStart = Cesium.Cartesian3.fromDegrees(
      lng - gridSize * 0.00005,
      lat + i * 0.00005,
      0
    );
    const hEnd = Cesium.Cartesian3.fromDegrees(
      lng + gridSize * 0.00005,
      lat + i * 0.00005,
      0
    );
    const hColor = i === 0 ? Cesium.Color.YELLOW.withAlpha(0.8) : Cesium.Color.WHITE.withAlpha(0.2);
    
    cesiumViewer.value.entities.add({
      polyline: {
        positions: [hStart, hEnd],
        width: 1,
        material: hColor
      }
    });
    
    // 创建垂直网格线
    const vStart = Cesium.Cartesian3.fromDegrees(
      lng + i * 0.00005,
      lat - gridSize * 0.00005,
      0
    );
    const vEnd = Cesium.Cartesian3.fromDegrees(
      lng + i * 0.00005,
      lat + gridSize * 0.00005,
      0
    );
    const vColor = i === 0 ? Cesium.Color.YELLOW.withAlpha(0.8) : Cesium.Color.WHITE.withAlpha(0.2);
    
    cesiumViewer.value.entities.add({
      polyline: {
        positions: [vStart, vEnd],
        width: 1,
        material: vColor
      }
    });
  }
};

const initCesium = () => {
  const container = document.getElementById('cesiumContainer');
  if (!container) return;
  
  if (!selectedStation.value) {
    ElMessage.error('请先选择基站');
    return;
  }
  
  const lng = selectedStation.value.lng || 116.397428;
  const lat = selectedStation.value.lat || 39.90923;
  
  try {
    cesiumViewer.value = new Cesium.Viewer('cesiumContainer', {
      terrainProvider: new Cesium.EllipsoidTerrainProvider(),
      animation: false,
      timeline: false,
      baseLayerPicker: false,
      geocoder: false,
      homeButton: false,
      sceneModePicker: false,
      navigationHelpButton: false,
      fullscreenButton: false
    });
    
    // 隐藏默认图层
    cesiumViewer.value.imageryLayers.removeAll();
    
    // 设置背景颜色为黑色
    cesiumViewer.value.scene.backgroundColor = Cesium.Color.BLACK;
    
    // 添加格子背景（简化版）
    addGridBackground(lng, lat);
    
    // 设置相机位置
    const center = Cesium.Cartesian3.fromDegrees(lng, lat, 100);
    
    cesiumViewer.value.camera.setView({
      destination: center,
      orientation: {
        heading: 0,
        pitch: Cesium.Math.toRadians(-45),
        roll: 0
      }
    });
    
    // 添加基站模型
    addStationModel();
  } catch (e) {
    console.error('Cesium初始化失败:', e);
    ElMessage.warning('Cesium加载失败，使用模拟视图');
  }
};

const addStationModel = () => {
  if (!cesiumViewer.value) return;
  
  if (!selectedStation.value) {
    console.error('selectedStation is undefined');
    return;
  }
  
  const lng = selectedStation.value.lng || 116.397428;
  const lat = selectedStation.value.lat || 39.90923;
  
  const center = Cesium.Cartesian3.fromDegrees(lng, lat, 0);
  
  // 创建建筑模型实体
  const buildingEntity = cesiumViewer.value.entities.add({
    position: center,
    orientation: Cesium.Transforms.headingPitchRollQuaternion(
      center,
      new Cesium.HeadingPitchRoll(0, 0, 0)
    ),
    model: {
      uri: '/models/low_poly_building.glb',
      scale: 15,
      minimumPixelSize: 100,
      maximumScale: 400,
      show: true
    }
  });
  
  // 监听模型加载事件
  const modelPromise = buildingEntity.model?.readyPromise;
  if (modelPromise && typeof modelPromise.then === 'function') {
    modelPromise.then((model) => {
      console.log('建筑模型加载成功:', model);
      const boundingSphere = model.boundingSphere;
      if (boundingSphere) {
        const radius = boundingSphere.radius;
        const cameraHeight = radius * 3;
        const cameraPosition = Cesium.Cartesian3.fromDegrees(lng, lat, cameraHeight);
        cesiumViewer.value.camera.setView({
          destination: cameraPosition,
          orientation: {
            heading: 0,
            pitch: Cesium.Math.toRadians(-30),
            roll: 0
          }
        });
      }
    }).catch((error) => {
      console.error('建筑模型加载失败:', error);
      addFallbackBuilding(center);
    });
  } else {
    // readyPromise 不可用，使用备用几何体
    console.warn('readyPromise 不可用，使用备用几何体');
    addFallbackBuilding(center);
  }
};

const addFallbackBuilding = (center) => {
  if (!cesiumViewer.value || !selectedStation.value) return;
  
  ElMessage.warning('建筑模型加载失败，使用默认几何体');
  
  cesiumViewer.value.entities.add({
    position: center,
    box: {
      dimensions: new Cesium.Cartesian3(300, 300, 400),
      material: Cesium.Color.GRAY.withAlpha(0.9),
      outline: true,
      outlineColor: Cesium.Color.BLACK
    }
  });
  
  const roofPosition = Cesium.Cartesian3.fromDegrees(
    selectedStation.value.lng,
    selectedStation.value.lat,
    400
  );
  cesiumViewer.value.entities.add({
    position: roofPosition,
    cylinder: {
      length: 30,
      topRadius: 0,
      bottomRadius: 150,
      material: Cesium.Color.RED.withAlpha(0.9),
      outline: true,
      outlineColor: Cesium.Color.BLACK
    }
  });
};

const loadStationAntennas = () => {
  // 使用下载的模型文件，天线位于建筑顶部（建筑缩放15倍后，顶部高度约为600）
  stationAntennas.value = [
    { id: 1, name: '主天线A', type: '全向天线', height: 10, x: 0, y: 0, z: 610, scale: 0.5, modelFile: 'old_antenna.glb' },
    { id: 2, name: '定向天线B', type: '定向天线', height: 8, x: 40, y: 40, z: 605, scale: 0.4, modelFile: 'old_antenna.glb' },
    { id: 3, name: '智能天线C', type: '智能天线', height: 12, x: -40, y: 40, z: 608, scale: 0.6, modelFile: 'old_antenna.glb' },
    { id: 4, name: '备用天线D', type: '全向天线', height: 10, x: 0, y: -35, z: 612, scale: 0.5, modelFile: 'old_antenna.glb' }
  ];
  
  // 在Cesium中添加天线
  stationAntennas.value.forEach(antenna => {
    addAntennaToScene(antenna);
  });
};

const updateAntennaInScene = (antenna) => {
  if (!cesiumViewer.value) return;
  
  // 找到对应的实体并更新
  cesiumViewer.value.entities.values.forEach(entity => {
    if (entity.antennaId === antenna.id) {
      const newPosition = Cesium.Cartesian3.fromDegrees(
        selectedStation.value.lng + (antenna.x * 0.0001),
        selectedStation.value.lat + (antenna.y * 0.0001),
        antenna.z
      );
      
      entity.position = newPosition;
      entity.orientation = Cesium.Transforms.headingPitchRollQuaternion(
        newPosition,
        new Cesium.HeadingPitchRoll(0, 0, 0)
      );
      
      if (entity.model) {
        entity.model.scale = antenna.scale || antenna.height / 10;
        entity.model.color = getAntennaColor(antenna.type);
      }
      
      if (entity.label) {
        entity.label.text = antenna.name;
      }
    }
  });
};

const addAntennaToScene = (antenna) => {
  if (!cesiumViewer.value) return;
  
  const antennaPosition = Cesium.Cartesian3.fromDegrees(
    selectedStation.value.lng + (antenna.x * 0.0001),
    selectedStation.value.lat + (antenna.y * 0.0001),
    antenna.z
  );
  
  // 查找是否有上传的模型
  const uploadedModel = uploadedModels.value.find(m => m.name === antenna.modelFile);
  
  // 构建 glTF 模型 URI
  const modelUri = uploadedModel 
    ? uploadedModel.url 
    : `/models/${antenna.modelFile}`;
  
  // 加载 glTF 模型
  const entity = cesiumViewer.value.entities.add({
    antennaId: antenna.id,
    position: antennaPosition,
    orientation: Cesium.Transforms.headingPitchRollQuaternion(
      antennaPosition,
      new Cesium.HeadingPitchRoll(
        Cesium.Math.toRadians(0),
        Cesium.Math.toRadians(0),
        Cesium.Math.toRadians(0)
      )
    ),
    model: {
      uri: modelUri,
      scale: antenna.scale || antenna.height / 10, // 使用自定义缩放或根据高度计算
      minimumPixelSize: 20,
      maximumScale: 200,
      color: getAntennaColor(antenna.type)
    },
    label: {
      text: antenna.name,
      font: '14px sans-serif',
      fillColor: Cesium.Color.WHITE,
      outlineColor: Cesium.Color.BLACK,
      outlineWidth: 2,
      style: Cesium.LabelStyle.FILL_AND_OUTLINE,
      verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
      pixelOffset: new Cesium.Cartesian2(0, -50),
      disableDepthTestDistance: Number.POSITIVE_INFINITY
    }
  });
  
  cesiumEntities.value.push(entity);
};

const getAntennaColor = (type) => {
  switch (type) {
    case '全向天线': return Cesium.Color.BLUE.withAlpha(0.9);
    case '定向天线': return Cesium.Color.GREEN.withAlpha(0.9);
    case '智能天线': return Cesium.Color.PURPLE.withAlpha(0.9);
    default: return Cesium.Color.GRAY.withAlpha(0.9);
  }
};

const triggerFileUpload = () => {
  fileInput.value?.click();
};

const handleFileUpload = (event) => {
  const file = event.target.files[0];
  if (!file) return;
  
  if (!file.name.toLowerCase().endsWith('.glb')) {
    ElMessage.error('请选择 .glb 格式的文件');
    return;
  }
  
  const reader = new FileReader();
  reader.onload = (e) => {
    const arrayBuffer = e.target.result;
    
    // 将文件保存到临时 URL
    const blob = new Blob([arrayBuffer], { type: 'model/gltf-binary' });
    const tempUrl = URL.createObjectURL(blob);
    
    // 保存上传的模型信息
    const modelInfo = {
      id: Date.now(),
      name: file.name,
      url: tempUrl,
      blob: blob
    };
    uploadedModels.value.push(modelInfo);
    
    // 更新表单
    antennaForm.value.modelFile = file.name;
    
    ElMessage.success(`已选择模型文件: ${file.name}`);
  };
  
  reader.readAsArrayBuffer(file);
  event.target.value = ''; // 清空文件输入
};

const handleAddAntennaClick = () => {
  console.log('添加天线设备按钮被点击');
  showAddAntennaDialog();
};

const showAddAntennaDialog = () => {
  antennaForm.value = {
    name: '',
    type: '全向天线',
    height: 10,
    x: 0,
    y: 0,
    z: 25,
    modelFile: 'old_antenna.glb'
  };
  nextTick(() => {
    showAntennaDialog.value = true;
  });
};

const confirmAddAntenna = () => {
  if (!antennaForm.value.name) {
    ElMessage.warning('请输入天线名称');
    return;
  }
  
  const antennaData = { ...antennaForm.value };
  
  // 检查是否是编辑模式（有 id 且已存在）
  const existingIndex = stationAntennas.value.findIndex(a => a.id === antennaData.id);
  
  if (existingIndex >= 0) {
    // 更新现有天线
    stationAntennas.value[existingIndex] = antennaData;
    updateAntennaInScene(antennaData);
    showAntennaDialog.value = false;
    ElMessage.success('天线设备更新成功');
  } else {
    // 添加新天线
    const newAntenna = {
      id: Date.now(),
      ...antennaData
    };
    stationAntennas.value.push(newAntenna);
    addAntennaToScene(newAntenna);
    showAntennaDialog.value = false;
    ElMessage.success('天线设备添加成功');
  }
};

const locateAntenna = (antenna) => {
  if (!cesiumViewer.value) return;
  
  const antennaPosition = Cesium.Cartesian3.fromDegrees(
    selectedStation.value.lng + (antenna.x * 0.0001),
    selectedStation.value.lat + (antenna.y * 0.0001),
    antenna.z + 10
  );
  
  cesiumViewer.value.camera.setView({
    destination: antennaPosition,
    orientation: {
      heading: 0,
      pitch: Cesium.Math.toRadians(-30),
      roll: 0
    }
  });
};

const editAntenna = (antenna) => {
  console.log('编辑按钮被点击:', antenna);
  console.log('antennaForm before:', { ...antennaForm.value });
  antennaForm.value = { ...antenna };
  console.log('antennaForm after:', { ...antennaForm.value });
  showAntennaDialog.value = true;
  console.log('showAntennaDialog:', showAntennaDialog.value);
};

const deleteAntenna = (antenna) => {
  ElMessage.confirm('确定删除该天线设备吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    const index = stationAntennas.value.findIndex(a => a.id === antenna.id);
    if (index > -1) {
      stationAntennas.value.splice(index, 1);
    }
    ElMessage.success('删除成功');
  }).catch(() => {
    ElMessage.info('已取消删除');
  });
};

watch(pendingDevice, (newVal) => {
  if (addMode.value && newVal.lng && newVal.lat) {
    updateTempMarker(newVal.lng, newVal.lat);
  }
}, { deep: true });

onMounted(() => {
  initMap();
});

onUnmounted(() => {
  if (map) {
    map.destroy();
  }
  if (cesiumViewer.value) {
    cesiumViewer.value.destroy();
  }
  delete window.initAMap;
});
</script>

<style scoped>
.design-page {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #f5f5f5;
}

.toolbar-card {
  margin: 10px;
  padding: 10px;
  flex-shrink: 0;
  z-index: 100;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.left-tools, .center-tools {
  display: flex;
  gap: 10px;
  align-items: center;
}

.main-content {
  flex: 1;
  display: flex;
  margin: 0 10px 10px;
  gap: 10px;
  min-height: 0;
}

.map-container {
  flex: 1;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  background: #fff;
}

.station-container {
  flex: 1;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  background: #000;
  overflow: hidden;
}

.station-3d {
  width: 100%;
  height: 100%;
}

.side-panel {
  width: 320px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow-y: auto;
  z-index: 100;
}

.device-list-card, .antenna-card {
  flex-shrink: 0;
}

.search-bar {
  margin-bottom: 12px;
}

.device-list, .antenna-list {
  max-height: 300px;
  overflow-y: auto;
}

.device-item, .antenna-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px;
  border-bottom: 1px solid #f0f0f0;
}

.device-item:last-child, .antenna-item:last-child {
  border-bottom: none;
}

.device-info, .antenna-info {
  flex: 1;
  min-width: 0;
}

.device-name, .antenna-name {
  display: block;
  font-weight: 500;
  font-size: 14px;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.device-coord {
  display: block;
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.antenna-type {
  display: block;
  font-size: 12px;
  color: #409EFF;
  margin-top: 4px;
}

.device-actions, .antenna-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

.empty-state {
  text-align: center;
  padding: 20px;
  color: #909399;
  font-size: 14px;
}

.add-antenna-btn {
  width: 100%;
  margin-top: 10px;
}

.add-device-panel {
  position: fixed;
  top: 100px;
  right: 10px;
  width: 320px;
  z-index: 200;
}

.add-card {
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.form-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 15px;
}

.tips-text {
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px dashed #e4e7ed;
  font-size: 13px;
  color: #67c23a;
}

.model-tips {
  margin-top: 8px;
  padding: 8px;
  background: #f5f7fa;
  border-radius: 4px;
  font-size: 12px;
  color: #606266;
}

.model-tips p {
  margin: 0 0 6px 0;
  font-weight: 500;
}

.model-tips ul {
  margin: 0;
  padding-left: 16px;
}

.model-tips li {
  margin: 4px 0;
}

.tips {
  font-size: 13px;
  color: #666;
}

.tips ul {
  margin: 0;
  padding-left: 20px;
}

.tips li {
  margin: 5px 0;
}

.antenna-dialog {
  z-index: 9999 !important;
  position: fixed !important;
  top: 50% !important;
  left: 50% !important;
  transform: translate(-50%, -50%) !important;
}

.antenna-dialog::v-deep .el-dialog__wrapper {
  z-index: 9998 !important;
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  bottom: 0 !important;
}

.antenna-dialog::v-deep .el-dialog {
  z-index: 9999 !important;
  position: relative !important;
}

#cesiumContainer {
  position: relative;
  z-index: 1;
}

.custom-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999 !important;
  pointer-events: auto;
}

.custom-modal {
  background: white;
  border-radius: 8px;
  width: 500px;
  max-width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  position: relative;
  z-index: 10000 !important;
}

.custom-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #eee;
  background: #409EFF;
  color: white;
  border-radius: 8px 8px 0 0;
}

.custom-modal-title {
  font-size: 16px;
  font-weight: 600;
}

.custom-modal-close {
  background: none;
  border: none;
  font-size: 24px;
  color: white;
  cursor: pointer;
  line-height: 1;
  opacity: 0.8;
  transition: opacity 0.2s;
}

.custom-modal-close:hover {
  opacity: 1;
}

.custom-modal-body {
  padding: 20px;
}

.custom-modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 20px;
  border-top: 1px solid #eee;
  background: #fafafa;
  border-radius: 0 0 8px 8px;
}

.form-item {
  margin-bottom: 16px;
}

.form-item label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: #303133;
  font-size: 14px;
}

.form-input, .form-select {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  font-size: 14px;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.form-input:focus, .form-select:focus {
  outline: none;
  border-color: #409EFF;
}

.file-upload-btn {
  background: #409EFF;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s;
}

.file-upload-btn:hover {
  background: #67b1ff;
}

.modal-btn {
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.modal-btn-cancel {
  background: #f5f7fa;
  color: #606266;
}

.modal-btn-cancel:hover {
  background: #e4e7ed;
}

.modal-btn-primary {
  background: #409EFF;
  color: white;
}

.modal-btn-primary:hover {
  background: #67b1ff;
}
</style>
