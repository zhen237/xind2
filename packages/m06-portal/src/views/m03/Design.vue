<template>
  <div class="design-page">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <div class="mode-switch">
        <el-button 
          :type="addMode ? 'primary' : 'default'" 
          @click="toggleAddMode"
          class="mode-btn"
        >
          <span class="btn-icon">➕</span>
          <span>{{ addMode ? '退出添加' : '添加模式' }}</span>
        </el-button>
        <el-button 
          :type="mapMode === '3D' ? 'primary' : 'default'" 
          @click="toggleMapMode('3D')"
          class="mode-btn"
        >
          <span class="btn-icon">🗺️</span>
          <span>3D视图</span>
        </el-button>
        <el-button 
          :type="mapMode === 'STATION' ? 'primary' : 'default'" 
          @click="toggleMapMode('STATION')"
          class="mode-btn"
        >
          <span class="btn-icon">🏗️</span>
          <span>基站环境</span>
        </el-button>
      </div>
      
      <div class="scene-info">
        <el-tag type="success" class="info-tag" v-if="selectedStation">
          <span class="tag-icon">📍</span>
          {{ selectedStation.name }}
        </el-tag>
        <el-tag type="info" class="info-tag" v-if="mapMode === 'STATION'">
          <span class="tag-icon">📶</span>
          天线: {{ stationAntennas.length }} 个
        </el-tag>
        <el-tag class="info-tag">
          <span class="tag-icon">🎯</span>
          {{ mapMode === '3D' ? '地图' : '基站环境' }}
        </el-tag>
      </div>
      
      <div class="view-controls">
        <el-button v-if="mapMode === '3D'" @click="zoomIn" icon="ZoomIn" class="control-btn">放大</el-button>
        <el-button v-if="mapMode === '3D'" @click="zoomOut" icon="ZoomOut" class="control-btn">缩小</el-button>
        <el-button v-if="mapMode === '3D'" @click="resetView" icon="Refresh" class="control-btn">复位</el-button>
        <el-button v-if="mapMode === 'STATION'" @click="backToMap" icon="ArrowLeft" class="control-btn">返回地图</el-button>
      </div>
    </div>

    <div class="main-content">
      <!-- 3D地图容器 -->
      <div v-if="mapMode === '3D'" class="map-container" ref="mapContainer">
        <!-- 添加模式提示 -->
        <div class="add-mode-hint" v-if="addMode">
          <el-tag type="warning" size="large">
            <span>⚠️ 添加模式：点击地图选择位置，可多次点击调整</span>
          </el-tag>
        </div>
      </div>
      
      <!-- 基站环境容器 -->
      <div v-else-if="mapMode === 'STATION'" class="station-container">
        <div class="cesium-container" id="cesiumContainer">
          <!-- 坐标显示 -->
          <div class="coordinate-display">
            <span class="coord-item">
              <span class="coord-label">经度:</span>
              <span class="coord-value">{{ currentLng.toFixed(6) }}</span>
            </span>
            <span class="coord-divider">|</span>
            <span class="coord-item">
              <span class="coord-label">纬度:</span>
              <span class="coord-value">{{ currentLat.toFixed(6) }}</span>
            </span>
          </div>
        </div>
      </div>

      <!-- 侧边栏 -->
      <div class="side-panel">
        <!-- 3D模式下的设备列表 -->
        <el-card v-if="mapMode === '3D'" title="📡 设备列表" class="device-list-card">
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
                <span class="device-coord">{{ device.lng.toFixed(5) }}, {{ device.lat.toFixed(5) }}</span>
              </div>
              <div class="device-actions">
                <el-button size="small" @click="locateDevice(device)">定位</el-button>
                <el-button size="small" type="primary" @click="enterStation(device)">进入基站</el-button>
                <el-button size="small" type="danger" @click="deleteDevice(device)">删除</el-button>
              </div>
            </div>
            <div v-if="filteredDevices.length === 0" class="empty-state">
              <div class="empty-icon">📡</div>
              <div>暂无设备数据</div>
            </div>
          </div>
        </el-card>

        <!-- 基站环境模式下的标签页 -->
        <el-tabs v-if="mapMode === 'STATION'" v-model="activeTab" type="border-card" class="tab-container">
          <!-- 基站管理 -->
          <el-tab-pane label="📡 基站管理" name="stations">
            <div class="tab-content">
              <div class="search-bar">
                <el-input 
                  v-model="searchKeyword" 
                  placeholder="搜索基站名称" 
                  prefix-icon="Search"
                />
              </div>
              <div class="station-list">
                <div 
                  v-for="station in nearbyStations" 
                  :key="station.id" 
                  class="station-item"
                  :class="{ active: selectedStation?.id === station.id }"
                  @click="switchStation(station)"
                >
                  <div class="station-info">
                    <span class="station-name">{{ station.name }}</span>
                    <span class="station-coord">{{ station.lng.toFixed(6) }}, {{ station.lat.toFixed(6) }}</span>
                  </div>
                  <div class="station-actions">
                    <el-button size="small" @click.stop="editStation(station)" icon="Edit">编辑</el-button>
                    <el-button size="small" type="danger" @click.stop="deleteBaseStation(station)" icon="Delete">删除</el-button>
                  </div>
                </div>
              </div>
              <el-button class="add-station-btn" @click="handleAddBaseStationClick" icon="Plus">
                + 添加基站模型
              </el-button>
            </div>
          </el-tab-pane>
          
          <!-- 天线设备 -->
          <el-tab-pane label="📶 天线设备" name="antennas">
            <div class="tab-content">
              <div class="search-bar">
                <el-input 
                  v-model="antennaKeyword" 
                  placeholder="搜索天线名称" 
                  prefix-icon="Search"
                />
              </div>
              <div class="antenna-list">
                <div 
                  v-for="antenna in filteredAntennas" 
                  :key="antenna.id" 
                  class="antenna-item"
                >
                  <div class="antenna-icon" :style="{ background: getAntennaColor(antenna.type) }">
                    <span v-if="antenna.type === '全向天线'">📡</span>
                    <span v-else-if="antenna.type === '定向天线'">🎯</span>
                    <span v-else>🧠</span>
                  </div>
                  <div class="antenna-info">
                    <div class="antenna-header">
                      <span class="antenna-name">{{ antenna.name }}</span>
                      <span class="antenna-type-badge" :class="getAntennaTypeClass(antenna.type)">
                        {{ antenna.type }}
                      </span>
                    </div>
                    <span class="antenna-coord">X:{{ antenna.x }} Y:{{ antenna.y }} Z:{{ antenna.z }}</span>
                  </div>
                  <div class="antenna-actions">
                    <el-button size="small" @click="locateAntenna(antenna)" icon="MapPin">定位</el-button>
                    <el-button size="small" @click="editAntenna(antenna)" icon="Edit">编辑</el-button>
                    <el-button size="small" type="danger" @click="deleteAntenna(antenna)" icon="Delete">删除</el-button>
                  </div>
                </div>
                <div v-if="filteredAntennas.length === 0" class="empty-state">
                  <div class="empty-icon">📶</div>
                  <div>暂无天线设备</div>
                  <div class="empty-hint">点击下方按钮添加</div>
                </div>
              </div>
              <el-button type="primary" class="add-antenna-btn" @click="handleAddAntennaClick" icon="Plus">
                + 添加天线设备
              </el-button>
            </div>
          </el-tab-pane>
          
          <!-- 视图控制 -->
          <el-tab-pane label="🔧 视图控制" name="view">
            <div class="tab-content">
              <div class="view-section">
                <h4>视角预设</h4>
                <div class="preset-buttons">
                  <el-button @click="setCesiumView('top')" icon="Top">俯视图</el-button>
                  <el-button @click="setCesiumView('front')" icon="Eye">前视图</el-button>
                  <el-button @click="setCesiumView('side')" icon="Eye">侧视图</el-button>
                  <el-button @click="setCesiumView('iso')" icon="Eye">等轴测</el-button>
                </div>
              </div>
              
              <div class="view-section">
                <h4>显示设置</h4>
                <el-switch v-model="showLabels" @change="toggleLabels">显示标签</el-switch>
                <el-switch v-model="autoRotate" @change="toggleAutoRotate">自动旋转</el-switch>
              </div>
              
              <div class="view-section">
                <h4>操作说明</h4>
                <ul class="tips-list">
                  <li><span class="tip-key">左键拖拽</span>旋转视角</li>
                  <li><span class="tip-key">滚轮</span>缩放场景</li>
                  <li><span class="tip-key">右键拖拽</span>平移场景</li>
                </ul>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>

        <!-- 操作说明 -->
        <el-card v-if="mapMode === '3D'" title="📖 操作说明">
          <div class="tips">
            <ul>
              <li><strong>左键拖拽</strong>：旋转视角</li>
              <li><strong>滚轮</strong>：缩放地图</li>
              <li><strong>右键拖拽</strong>：平移地图</li>
              <li><strong>点击标记</strong>：查看基站信息</li>
              <li><strong>进入基站</strong>：查看基站三维环境</li>
            </ul>
          </div>
        </el-card>
      </div>
    </div>

    <!-- 添加设备面板 -->
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
      </el-card>
    </div>

    <!-- 基站编辑弹窗 -->
    <el-dialog 
      title="基站信息" 
      :visible.sync="showStationDialog" 
      width="450px"
      class="custom-dialog"
    >
      <el-form :model="stationForm" label-width="80px">
        <el-form-item label="基站名称" required>
          <el-input v-model="stationForm.name" placeholder="请输入基站名称" />
        </el-form-item>
        <el-form-item label="经度">
          <el-input v-model.number="stationForm.lng" placeholder="经度" />
        </el-form-item>
        <el-form-item label="纬度">
          <el-input v-model.number="stationForm.lat" placeholder="纬度" />
        </el-form-item>
        <el-form-item label="塔高(m)">
          <el-input v-model.number="stationForm.height" placeholder="塔高" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showStationDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmAddBaseStation">确认保存</el-button>
      </template>
    </el-dialog>

    <!-- 天线编辑弹窗 -->
    <el-dialog 
      title="天线信息" 
      :visible.sync="showAntennaDialog" 
      width="450px"
      class="custom-dialog"
    >
      <el-form :model="antennaForm" label-width="80px">
        <el-form-item label="天线名称" required>
          <el-input v-model="antennaForm.name" placeholder="请输入天线名称" />
        </el-form-item>
        <el-form-item label="天线类型">
          <el-select v-model="antennaForm.type" style="width: 100%">
            <el-option label="📡 全向天线" value="全向天线" />
            <el-option label="🎯 定向天线" value="定向天线" />
            <el-option label="🧠 智能天线" value="智能天线" />
          </el-select>
        </el-form-item>
        <el-form-item label="位置X">
          <el-input v-model.number="antennaForm.x" placeholder="X坐标" />
        </el-form-item>
        <el-form-item label="位置Y">
          <el-input v-model.number="antennaForm.y" placeholder="Y坐标" />
        </el-form-item>
        <el-form-item label="位置Z">
          <el-input v-model.number="antennaForm.z" placeholder="Z坐标（高度）" />
        </el-form-item>
        <el-form-item label="模型缩放">
          <el-input v-model.number="antennaForm.scale" placeholder="缩放比例" />
        </el-form-item>
        <el-form-item label="模型文件">
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
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAntennaDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmAddAntenna">确认保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';

const mapContainer = ref(null);
const addMode = ref(false);
const searchKeyword = ref('');
const antennaKeyword = ref('');
const devices = ref([]);
const markers = ref([]);
const mapMode = ref('3D');
const showAntennaDialog = ref(false);
const showStationDialog = ref(false);
const selectedStation = ref(null);
const stationAntennas = ref([]);
const nearbyStations = ref([]);
const cesiumViewer = ref(null);
const cesiumEntities = ref([]);
const fileInput = ref(null);
const uploadedModels = ref([]);
const activeTab = ref('stations');
const showLabels = ref(true);
const autoRotate = ref(false);

// 当前坐标显示
const currentLng = ref(116.397428);
const currentLat = ref(39.90923);

const stationForm = ref({
  id: null,
  name: '',
  lng: 116.397428,
  lat: 39.90923,
  height: 100
});

const pendingDevice = ref({
  name: '',
  lng: 116.397428,
  lat: 39.90923
});

const antennaForm = ref({
  name: '',
  type: '全向天线',
  x: 0,
  y: 0,
  z: 10,
  scale: 0.5,
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

const filteredAntennas = computed(() => {
  if (!antennaKeyword.value) return stationAntennas.value;
  return stationAntennas.value.filter(ant => 
    ant.name.toLowerCase().includes(antennaKeyword.value.toLowerCase())
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
  devices.value = [
    { id: 1, name: '测试基站A', lng: 116.397428, lat: 39.90923, type: 'station' },
    { id: 2, name: '测试基站B', lng: 116.407428, lat: 39.91923, type: 'station' },
    { id: 3, name: '测试基站C', lng: 116.387428, lat: 39.89923, type: 'station' }
  ];
  updateMarkers();
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
  ElMessage.success('设备添加成功');
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
  loadNearbyStations(device);
  mapMode.value = 'STATION';
  nextTick(() => {
    initCesium();
    loadStationAntennas();
  });
};

const loadNearbyStations = (currentStation) => {
  nearbyStations.value = [
    { id: 1, name: '测试基站A', lng: 116.397428, lat: 39.90923, height: 100 },
    { id: 2, name: '测试基站B', lng: 116.407428, lat: 39.91923, height: 80 },
    { id: 3, name: '测试基站C', lng: 116.387428, lat: 39.89923, height: 120 }
  ];
};

const handleAddBaseStationClick = () => {
  stationForm.value = {
    id: null,
    name: '',
    lng: selectedStation.value?.lng || 116.397428,
    lat: selectedStation.value?.lat || 39.90923,
    height: 100
  };
  showStationDialog.value = true;
};

const editStation = (station) => {
  stationForm.value = { ...station };
  showStationDialog.value = true;
};

const confirmAddBaseStation = () => {
  if (!stationForm.value.name) {
    ElMessage.warning('请输入基站名称');
    return;
  }
  if (!stationForm.value.lng || !stationForm.value.lat) {
    ElMessage.warning('请输入经纬度');
    return;
  }

  const stationData = { ...stationForm.value };
  
  const existingIndex = nearbyStations.value.findIndex(s => s.id === stationData.id);
  
  if (existingIndex >= 0) {
    nearbyStations.value[existingIndex] = stationData;
    if (selectedStation.value?.id === stationData.id) {
      selectedStation.value = stationData;
      if (cesiumViewer.value) {
        cesiumViewer.value.destroy();
        cesiumViewer.value = null;
      }
      nextTick(() => {
        initCesium();
        loadStationAntennas();
      });
    }
    showStationDialog.value = false;
    ElMessage.success('基站信息更新成功');
  } else {
    const newStation = {
      id: Date.now(),
      ...stationData
    };
    nearbyStations.value.push(newStation);
    showStationDialog.value = false;
    ElMessage.success('基站添加成功');
  }
};

const switchStation = (station) => {
  selectedStation.value = station;
  if (cesiumViewer.value) {
    cesiumViewer.value.destroy();
    cesiumViewer.value = null;
  }
  nextTick(() => {
    initCesium();
    loadStationAntennas();
  });
};

const deleteBaseStation = (station) => {
  ElMessageBox.confirm(`确定删除基站 "${station.name}" 吗？`, '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    const index = nearbyStations.value.findIndex(s => s.id === station.id);
    if (index > -1) {
      nearbyStations.value.splice(index, 1);
    }
    
    if (selectedStation.value?.id === station.id) {
      if (nearbyStations.value.length > 0) {
        switchStation(nearbyStations.value[0]);
      } else {
        backToMap();
      }
    }
    
    ElMessage.success('删除成功');
  }).catch(() => {
    ElMessage.info('已取消删除');
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

const deleteDevice = (device) => {
  ElMessage.confirm('确定删除该设备吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    const index = devices.value.findIndex(d => d.id === device.id);
    if (index > -1) {
      devices.value.splice(index, 1);
    }
    updateMarkers();
    ElMessage.success('删除成功');
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
  
  if (mode === 'STATION' && !selectedStation.value) {
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
    
    cesiumViewer.value.imageryLayers.removeAll();
    
    cesiumViewer.value.scene.backgroundColor = Cesium.Color.fromCssColorString('#0a1628');
    
    const center = Cesium.Cartesian3.fromDegrees(lng, lat, 250);
    
    cesiumViewer.value.camera.setView({
      destination: center,
      orientation: {
        heading: 0,
        pitch: Cesium.Math.toRadians(-45),
        roll: 0
      }
    });
    
    addStationModel();
    
    cesiumViewer.value.scene.screenSpaceEventHandler.setInputAction((event) => {
      const ray = cesiumViewer.value.camera.getPickRay(event.endPosition);
      if (ray) {
        const globe = cesiumViewer.value.scene.globe;
        const intersection = globe.pick(ray, cesiumViewer.value.scene);
        if (intersection) {
          const cartographic = Cesium.Cartographic.fromCartesian(intersection);
          currentLng.value = Cesium.Math.toDegrees(cartographic.longitude);
          currentLat.value = Cesium.Math.toDegrees(cartographic.latitude);
        }
      }
    }, Cesium.ScreenSpaceEventType.MOUSE_MOVE);
    
  } catch (e) {
    console.error('Cesium初始化失败:', e);
    ElMessage.warning('Cesium加载失败');
  }
};

const addStationModel = () => {
  if (!cesiumViewer.value || !selectedStation.value) return;
  
  const lng = selectedStation.value.lng || 116.397428;
  const lat = selectedStation.value.lat || 39.90923;
  const towerHeight = selectedStation.value.height || 100;
  
  const center = Cesium.Cartesian3.fromDegrees(lng, lat, 0);
  
  // 添加地面平台
  cesiumViewer.value.entities.add({
    position: center,
    box: {
      dimensions: new Cesium.Cartesian3(30, 30, 2),
      material: Cesium.Color.GRAY.withAlpha(0.9),
      outline: true,
      outlineColor: Cesium.Color.WHITE,
      outlineWidth: 2
    }
  });
  
  // 添加基站塔
  cesiumViewer.value.entities.add({
    position: Cesium.Cartesian3.fromDegrees(lng, lat, towerHeight / 2),
    cylinder: {
      length: towerHeight,
      topRadius: 1.5,
      bottomRadius: 3,
      material: Cesium.Color.fromCssColorString('#4a5568'),
      outline: true,
      outlineColor: Cesium.Color.WHITE,
      outlineWidth: 2
    }
  });
  
  // 添加塔顶平台
  cesiumViewer.value.entities.add({
    position: Cesium.Cartesian3.fromDegrees(lng, lat, towerHeight + 1),
    box: {
      dimensions: new Cesium.Cartesian3(10, 10, 2),
      material: Cesium.Color.fromCssColorString('#2d3748'),
      outline: true,
      outlineColor: Cesium.Color.WHITE,
      outlineWidth: 2
    }
  });
  
  // 添加地面网格
  addGroundGrid(lng, lat);
  
  // 添加通信厂区模型
  const modelUrl = '/models/communication_site.glb';
  const modelPosition = Cesium.Cartesian3.fromDegrees(lng - 0.002, lat - 0.001, 0);
  cesiumViewer.value.entities.add({
    position: modelPosition,
    model: {
      uri: modelUrl,
      scale: 0.3,
      minimumPixelSize: 30,
      maximumScale: 100,
      heightReference: Cesium.HeightReference.CLAMP_TO_GROUND
    }
  });
};

const addGroundGrid = (lng, lat) => {
  if (!cesiumViewer.value) return;
  
  const gridSize = 150;
  const step = 30;
  
  for (let i = -gridSize; i <= gridSize; i += step) {
    const hStart = Cesium.Cartesian3.fromDegrees(lng - gridSize * 0.00005, lat + i * 0.00005, 0.5);
    const hEnd = Cesium.Cartesian3.fromDegrees(lng + gridSize * 0.00005, lat + i * 0.00005, 0.5);
    const hColor = i === 0 ? Cesium.Color.YELLOW.withAlpha(0.8) : Cesium.Color.WHITE.withAlpha(0.2);
    
    cesiumViewer.value.entities.add({
      polyline: {
        positions: [hStart, hEnd],
        width: 2,
        material: hColor
      }
    });
    
    const vStart = Cesium.Cartesian3.fromDegrees(lng + i * 0.00005, lat - gridSize * 0.00005, 0.5);
    const vEnd = Cesium.Cartesian3.fromDegrees(lng + i * 0.00005, lat + gridSize * 0.00005, 0.5);
    const vColor = i === 0 ? Cesium.Color.YELLOW.withAlpha(0.8) : Cesium.Color.WHITE.withAlpha(0.2);
    
    cesiumViewer.value.entities.add({
      polyline: {
        positions: [vStart, vEnd],
        width: 2,
        material: vColor
      }
    });
  }
};

const loadStationAntennas = () => {
  stationAntennas.value = [];
  
  stationAntennas.value.forEach(antenna => {
    addAntennaToScene(antenna);
  });
};

const addAntennaToScene = (antenna) => {
  if (!cesiumViewer.value || !selectedStation.value) return;
  
  const lng = selectedStation.value.lng || 116.397428;
  const lat = selectedStation.value.lat || 39.90923;
  
  const antennaPosition = Cesium.Cartesian3.fromDegrees(
    lng + (antenna.x * 0.0001),
    lat + (antenna.y * 0.0001),
    antenna.z
  );
  
  const uploadedModel = uploadedModels.value.find(m => m.name === antenna.modelFile);
  const modelUri = uploadedModel ? uploadedModel.url : `/models/${antenna.modelFile}`;
  
  const entity = cesiumViewer.value.entities.add({
    antennaId: antenna.id,
    position: antennaPosition,
    orientation: Cesium.Transforms.headingPitchRollQuaternion(
      antennaPosition,
      new Cesium.HeadingPitchRoll(0, 0, 0)
    ),
    model: {
      uri: modelUri,
      scale: antenna.scale || 0.5,
      minimumPixelSize: 20,
      maximumScale: 200,
      color: getCesiumColor(antenna.type)
    },
    label: {
      text: antenna.name,
      font: '14px sans-serif',
      fillColor: Cesium.Color.WHITE,
      outlineColor: Cesium.Color.BLACK,
      outlineWidth: 2,
      style: Cesium.LabelStyle.FILL_AND_OUTLINE,
      verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
      pixelOffset: new Cesium.Cartesian2(0, -35),
      disableDepthTestDistance: Number.POSITIVE_INFINITY,
      show: showLabels.value
    }
  });
  
  cesiumEntities.value.push(entity);
};

const getCesiumColor = (type) => {
  switch (type) {
    case '全向天线': return Cesium.Color.BLUE.withAlpha(0.9);
    case '定向天线': return Cesium.Color.GREEN.withAlpha(0.9);
    case '智能天线': return Cesium.Color.PURPLE.withAlpha(0.9);
    default: return Cesium.Color.GRAY.withAlpha(0.9);
  }
};

const getAntennaColor = (type) => {
  switch (type) {
    case '全向天线': return '#3b82f6';
    case '定向天线': return '#22c55e';
    case '智能天线': return '#a855f7';
    default: return '#6b7280';
  }
};

const getAntennaTypeClass = (type) => {
  switch (type) {
    case '全向天线': return 'omni';
    case '定向天线': return 'directional';
    case '智能天线': return 'smart';
    default: return '';
  }
};

const updateAntennaInScene = (antenna) => {
  if (!cesiumViewer.value || !selectedStation.value) return;
  
  const lng = selectedStation.value.lng || 116.397428;
  const lat = selectedStation.value.lat || 39.90923;
  
  const entities = cesiumViewer.value.entities.values;
  for (let i = 0; i < entities.length; i++) {
    const entity = entities[i];
    if (entity.antennaId === antenna.id) {
      const newPosition = Cesium.Cartesian3.fromDegrees(
        lng + (antenna.x * 0.0001),
        lat + (antenna.y * 0.0001),
        antenna.z
      );
      
      entity.position = newPosition;
      
      if (entity.model) {
        entity.model.scale = antenna.scale || 0.5;
        entity.model.color = getCesiumColor(antenna.type);
      }
      
      if (entity.label) {
        entity.label.text = antenna.name;
      }
      break;
    }
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
    const blob = new Blob([arrayBuffer], { type: 'model/gltf-binary' });
    const tempUrl = URL.createObjectURL(blob);
    
    const modelInfo = {
      id: Date.now(),
      name: file.name,
      url: tempUrl,
      blob: blob
    };
    uploadedModels.value.push(modelInfo);
    
    antennaForm.value.modelFile = file.name;
    
    ElMessage.success(`已选择模型文件: ${file.name}`);
  };
  
  reader.readAsArrayBuffer(file);
  event.target.value = '';
};

const handleAddAntennaClick = () => {
  antennaForm.value = {
    name: '',
    type: '全向天线',
    x: 0,
    y: 0,
    z: 10,
    scale: 0.5,
    modelFile: 'old_antenna.glb'
  };
  showAntennaDialog.value = true;
};

const editAntenna = (antenna) => {
  antennaForm.value = { ...antenna };
  showAntennaDialog.value = true;
};

const confirmAddAntenna = () => {
  if (!antennaForm.value.name) {
    ElMessage.warning('请输入天线名称');
    return;
  }
  
  const antennaData = { ...antennaForm.value };
  
  const existingIndex = stationAntennas.value.findIndex(a => a.id === antennaData.id);
  
  if (existingIndex >= 0) {
    stationAntennas.value[existingIndex] = antennaData;
    updateAntennaInScene(antennaData);
    showAntennaDialog.value = false;
    ElMessage.success('天线设备更新成功');
  } else {
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
  if (!cesiumViewer.value || !selectedStation.value) return;
  
  const lng = selectedStation.value.lng || 116.397428;
  const lat = selectedStation.value.lat || 39.90923;
  
  const antennaPosition = Cesium.Cartesian3.fromDegrees(
    lng + (antenna.x * 0.0001),
    lat + (antenna.y * 0.0001),
    antenna.z + 10
  );
  
  cesiumViewer.value.camera.flyTo({
    destination: antennaPosition,
    orientation: {
      heading: 0,
      pitch: Cesium.Math.toRadians(-30),
      roll: 0
    },
    duration: 1.5
  });
};

const deleteAntenna = (antenna) => {
  ElMessageBox.confirm('确定删除该天线设备吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    const index = stationAntennas.value.findIndex(a => a.id === antenna.id);
    if (index > -1) {
      stationAntennas.value.splice(index, 1);
    }
    
    if (cesiumViewer.value) {
      const entities = cesiumViewer.value.entities.values;
      const entityArray = Array.from(entities);
      for (let i = entityArray.length - 1; i >= 0; i--) {
        const entity = entityArray[i];
        if (entity.antennaId === antenna.id) {
          cesiumViewer.value.entities.remove(entity);
          const cesiumIndex = cesiumEntities.value.findIndex(e => e === entity);
          if (cesiumIndex > -1) {
            cesiumEntities.value.splice(cesiumIndex, 1);
          }
          break;
        }
      }
    }
    
    ElMessage.success('删除成功');
  }).catch(() => {
    ElMessage.info('已取消删除');
  });
};

const setCesiumView = (viewType) => {
  if (!cesiumViewer.value || !selectedStation.value) return;
  
  const lng = selectedStation.value.lng || 116.397428;
  const lat = selectedStation.value.lat || 39.90923;
  
  const positions = {
    top: { dest: Cesium.Cartesian3.fromDegrees(lng, lat, 300), orient: { heading: 0, pitch: Cesium.Math.toRadians(-90), roll: 0 } },
    front: { dest: Cesium.Cartesian3.fromDegrees(lng - 0.003, lat, 150), orient: { heading: 0, pitch: Cesium.Math.toRadians(-15), roll: 0 } },
    side: { dest: Cesium.Cartesian3.fromDegrees(lng, lat - 0.003, 150), orient: { heading: Cesium.Math.toRadians(90), pitch: Cesium.Math.toRadians(-15), roll: 0 } },
    iso: { dest: Cesium.Cartesian3.fromDegrees(lng - 0.002, lat - 0.002, 200), orient: { heading: Cesium.Math.toRadians(45), pitch: Cesium.Math.toRadians(-30), roll: 0 } }
  };
  
  const config = positions[viewType];
  cesiumViewer.value.camera.flyTo({
    destination: config.dest,
    orientation: config.orient,
    duration: 1
  });
};

const toggleLabels = () => {
  if (!cesiumViewer.value) return;
  
  const entities = cesiumViewer.value.entities.values;
  for (let i = 0; i < entities.length; i++) {
    const entity = entities[i];
    if (entity.label) {
      entity.label.show = showLabels.value;
    }
  }
};

const toggleAutoRotate = () => {
  if (!cesiumViewer.value) return;
  
  cesiumViewer.value.scene.camera.lookAtTransform(Cesium.Matrix4.IDENTITY);
  cesiumViewer.value.scene.camera.enableAutoRotation = autoRotate.value;
};

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
  background: linear-gradient(135deg, #0a1628 0%, #1a2a4a 50%, #0f1a2e 100%);
}

/* 顶部工具栏 */
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  background: rgba(10, 22, 40, 0.9);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  z-index: 100;
}

.mode-switch {
  display: flex;
  gap: 8px;
}

.mode-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.mode-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.btn-icon {
  font-size: 16px;
}

.scene-info {
  display: flex;
  gap: 12px;
}

.info-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 20px;
}

.tag-icon {
  font-size: 14px;
}

.view-controls {
  display: flex;
  gap: 8px;
}

.control-btn {
  padding: 6px 14px;
  border-radius: 6px;
  transition: all 0.3s ease;
}

.control-btn:hover:not(:disabled) {
  transform: translateY(-2px);
}

/* 主内容区 */
.main-content {
  flex: 1;
  display: flex;
  margin: 10px;
  gap: 10px;
  min-height: 0;
}

/* 地图容器 */
.map-container {
  flex: 1;
  border-radius: 12px;
  overflow: hidden;
  position: relative;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

/* 添加模式提示 */
.add-mode-hint {
  position: absolute;
  top: 15px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;
}

/* 基站环境容器 */
.station-container {
  flex: 1;
  border-radius: 12px;
  overflow: hidden;
  position: relative;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.cesium-container {
  width: 100%;
  height: 100%;
}

/* 坐标显示 */
.coordinate-display {
  position: absolute;
  bottom: 15px;
  left: 15px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 15px;
  background: rgba(10, 22, 40, 0.9);
  backdrop-filter: blur(10px);
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  z-index: 10;
}

.coord-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.coord-label {
  font-size: 12px;
  color: #909399;
}

.coord-value {
  font-size: 13px;
  font-weight: 500;
  color: #fff;
  font-family: monospace;
}

.coord-divider {
  color: rgba(255, 255, 255, 0.3);
}

/* 侧边栏 */
.side-panel {
  width: 380px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow-y: auto;
  z-index: 100;
}

.device-list-card {
  background: rgba(10, 22, 40, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
}

.device-list-card :deep(.el-card__header) {
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.device-list-card :deep(.el-card__body) {
  padding: 15px;
}

.device-list-card :deep(.el-card__header .el-card__title) {
  color: #fff;
}

.tab-container {
  flex: 1;
  background: rgba(10, 22, 40, 0.9);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.tab-container :deep(.el-tabs__header) {
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.tab-container :deep(.el-tabs__item) {
  color: #909399;
}

.tab-container :deep(.el-tabs__item.is-active) {
  color: #409eff;
}

.tab-content {
  padding: 15px;
}

.search-bar {
  margin-bottom: 15px;
}

.search-bar :deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

/* 设备列表 */
.device-list {
  max-height: 300px;
  overflow-y: auto;
}

.device-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  margin-bottom: 8px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  transition: all 0.3s ease;
}

.device-item:hover {
  background: rgba(255, 255, 255, 0.1);
}

.device-info {
  flex: 1;
  min-width: 0;
}

.device-name {
  display: block;
  font-weight: 500;
  font-size: 14px;
  color: #fff;
  margin-bottom: 4px;
}

.device-coord {
  display: block;
  font-size: 12px;
  color: #909399;
}

.device-actions {
  display: flex;
  gap: 6px;
}

/* 基站列表 */
.station-list {
  max-height: 250px;
  overflow-y: auto;
  margin-bottom: 15px;
}

.station-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  margin-bottom: 8px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.station-item:hover {
  background: rgba(255, 255, 255, 0.1);
}

.station-item.active {
  background: rgba(64, 158, 255, 0.2);
  border-left: 3px solid #409eff;
}

.station-info {
  flex: 1;
  min-width: 0;
}

.station-name {
  display: block;
  font-weight: 500;
  font-size: 14px;
  color: #fff;
  margin-bottom: 4px;
}

.station-coord {
  display: block;
  font-size: 11px;
  color: #909399;
}

.station-actions {
  display: flex;
  gap: 6px;
}

.add-station-btn {
  width: 100%;
  padding: 10px;
}

/* 天线列表 */
.antenna-list {
  max-height: 350px;
  overflow-y: auto;
  margin-bottom: 15px;
}

.antenna-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  margin-bottom: 8px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  transition: all 0.3s ease;
}

.antenna-item:hover {
  background: rgba(255, 255, 255, 0.1);
}

.antenna-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}

.antenna-info {
  flex: 1;
  min-width: 0;
}

.antenna-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.antenna-name {
  font-weight: 500;
  font-size: 14px;
  color: #fff;
}

.antenna-type-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  background: rgba(100, 116, 139, 0.3);
  color: #909399;
}

.antenna-type-badge.omni {
  background: rgba(59, 130, 246, 0.2);
  color: #60a5fa;
}

.antenna-type-badge.directional {
  background: rgba(34, 197, 94, 0.2);
  color: #4ade80;
}

.antenna-type-badge.smart {
  background: rgba(168, 85, 247, 0.2);
  color: #c084fc;
}

.antenna-coord {
  display: block;
  font-size: 11px;
  color: #909399;
}

.antenna-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.add-antenna-btn {
  width: 100%;
  padding: 10px;
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 30px;
  color: #909399;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 10px;
}

.empty-hint {
  font-size: 12px;
  color: #606266;
  margin-top: 5px;
}

/* 添加设备面板 */
.add-device-panel {
  position: fixed;
  top: 100px;
  right: 400px;
  width: 320px;
  z-index: 200;
}

.add-card {
  background: rgba(20, 30, 50, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.add-card :deep(.el-card__header) {
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.add-card :deep(.el-card__header .el-card__title) {
  color: #fff;
}

.add-card :deep(.el-form-item__label) {
  color: #909399;
}

.add-card :deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.form-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 15px;
}

/* 视图控制 */
.view-section {
  margin-bottom: 20px;
}

.view-section:last-child {
  margin-bottom: 0;
}

.view-section h4 {
  margin: 0 0 12px 0;
  font-size: 13px;
  font-weight: 600;
  color: #fff;
}

.preset-buttons {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.tips-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.tips-list li {
  padding: 8px 0;
  font-size: 13px;
  color: #909399;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.tips-list li:last-child {
  border-bottom: none;
}

.tip-key {
  display: inline-block;
  min-width: 80px;
  font-weight: 500;
  color: #fff;
}

/* 操作说明 */
.tips {
  font-size: 13px;
  color: #909399;
}

.tips ul {
  margin: 0;
  padding-left: 20px;
}

.tips li {
  margin: 8px 0;
}

/* 文件上传按钮 */
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

.form-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 4px;
  font-size: 14px;
  background: rgba(255, 255, 255, 0.05);
  color: #fff;
  box-sizing: border-box;
}

.form-input:focus {
  outline: none;
  border-color: #409EFF;
}

/* 自定义弹窗 */
.custom-dialog {
  :deep(.el-dialog) {
    background: rgba(20, 30, 50, 0.95);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
  }
  
  :deep(.el-dialog__header) {
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  }
  
  :deep(.el-dialog__title) {
    color: #fff;
  }
  
  :deep(.el-form-item__label) {
    color: #909399;
  }
  
  :deep(.el-input__wrapper) {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
  }
  
  :deep(.el-select) {
    :deep(.el-input__wrapper) {
      background: rgba(255, 255, 255, 0.05);
    }
  }
}
</style>