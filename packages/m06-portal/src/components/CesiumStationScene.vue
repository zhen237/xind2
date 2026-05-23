<template>
  <div class="cesium-station-scene">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <div class="mode-switch">
        <el-button 
          :type="mode === 'model' ? 'primary' : 'default'" 
          @click="mode = 'model'"
          class="mode-btn"
        >
          <span class="btn-icon">🏗️</span>
          <span>模型模式</span>
        </el-button>
        <el-button 
          :type="mode === 'analysis' ? 'primary' : 'default'" 
          @click="mode = 'analysis'"
          class="mode-btn"
        >
          <span class="btn-icon">📊</span>
          <span>分析模式</span>
        </el-button>
      </div>
      
      <div class="scene-info">
        <el-tag type="success" class="info-tag">
          <span class="tag-icon">📍</span>
          {{ stationName }}
        </el-tag>
        <el-tag type="info" class="info-tag">
          <span class="tag-icon">📶</span>
          天线: {{ antennas.length }} 个
        </el-tag>
        <el-tag class="info-tag">
          <span class="tag-icon">🎯</span>
          {{ mode === 'model' ? '建模' : '分析' }}
        </el-tag>
      </div>
      
      <div class="view-controls">
        <el-button @click="zoomIn" icon="ZoomIn" class="control-btn">放大</el-button>
        <el-button @click="zoomOut" icon="ZoomOut" class="control-btn">缩小</el-button>
        <el-button @click="resetView" icon="Refresh" class="control-btn">复位</el-button>
        <el-button @click="flyToStation" icon="MapPin" class="control-btn">飞向基站</el-button>
      </div>
    </div>

    <div class="main-content">
      <!-- Cesium场景容器 -->
      <div class="cesium-container" ref="cesiumContainer">
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
          <span class="coord-divider">|</span>
          <span class="coord-item">
            <span class="coord-label">高度:</span>
            <span class="coord-value">{{ currentHeight.toFixed(2) }}m</span>
          </span>
        </div>
        
        <!-- 添加模式提示 -->
        <div class="add-mode-hint" v-if="addMode">
          <el-tag type="warning" size="large">
            <span>⚠️ 添加模式：点击场景放置天线</span>
          </el-tag>
        </div>
      </div>

      <!-- 侧边栏 -->
      <div class="side-panel">
        <el-tabs v-model="activeTab" type="border-card" class="tab-container">
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
                    <span class="station-coord">
                      {{ station.lng.toFixed(6) }}, {{ station.lat.toFixed(6) }}
                    </span>
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
                  <div class="antenna-icon" :style="{ background: antenna.color }">
                    <span v-if="antenna.type === 'omni'">📡</span>
                    <span v-else-if="antenna.type === 'directional'">🎯</span>
                    <span v-else>🧠</span>
                  </div>
                  <div class="antenna-info">
                    <div class="antenna-header">
                      <span class="antenna-name">{{ antenna.name }}</span>
                      <span class="antenna-type-badge" :class="antenna.type">
                        {{ getAntennaTypeName(antenna.type) }}
                      </span>
                    </div>
                    <span class="antenna-coord">
                      {{ antenna.lng.toFixed(6) }}, {{ antenna.lat.toFixed(6) }}, {{ antenna.height }}m
                    </span>
                  </div>
                  <div class="antenna-actions">
                    <el-button size="small" @click="locateAntenna(antenna)" icon="MapPin">定位</el-button>
                    <el-button size="small" @click="editAntenna(antenna)" icon="Edit">编辑</el-button>
                    <el-button size="small" type="danger" @click="deleteAntenna(antenna)" icon="Delete">删除</el-button>
                  </div>
                </div>
                <div v-if="filteredAntennas.length === 0" class="empty-state">
                  <div class="empty-icon">📡</div>
                  <div>暂无天线设备</div>
                  <div class="empty-hint">点击上方"添加天线"按钮添加</div>
                </div>
              </div>
              <div class="add-antenna-btns">
                <el-button @click="toggleAddMode" :type="addMode ? 'danger' : 'primary'" icon="Plus">
                  {{ addMode ? '✕ 退出添加' : '+ 添加天线' }}
                </el-button>
              </div>
            </div>
          </el-tab-pane>
          
          <!-- 视图控制 -->
          <el-tab-pane label="🔧 视图控制" name="view">
            <div class="tab-content">
              <el-card class="view-card">
                <div class="view-section">
                  <h4>视角预设</h4>
                  <div class="preset-buttons">
                    <el-button @click="setView('top')" icon="Top">俯视图</el-button>
                    <el-button @click="setView('front')" icon="Eye">前视图</el-button>
                    <el-button @click="setView('side')" icon="Eye">侧视图</el-button>
                    <el-button @click="setView('iso')" icon="Eye">等轴测</el-button>
                  </div>
                </div>
                
                <div class="view-section">
                  <h4>显示设置</h4>
                  <el-switch v-model="showGrid" @change="toggleGrid">显示网格</el-switch>
                  <el-switch v-model="showLabels" @change="toggleLabels">显示标签</el-switch>
                  <el-switch v-model="autoRotate" @change="toggleAutoRotate">自动旋转</el-switch>
                </div>
                
                <div class="view-section">
                  <h4>操作说明</h4>
                  <ul class="tips-list">
                    <li><span class="tip-key">左键拖拽</span>旋转视角</li>
                    <li><span class="tip-key">滚轮</span>缩放场景</li>
                    <li><span class="tip-key">右键拖拽</span>平移场景</li>
                    <li><span class="tip-key">右键点击天线</span>快捷菜单</li>
                  </ul>
                </div>
              </el-card>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>

    <!-- 右键菜单 -->
    <div 
      class="context-menu" 
      v-if="showContextMenu" 
      :style="{ left: menuPosition.x + 'px', top: menuPosition.y + 'px' }"
    >
      <ul>
        <li @click="contextLocate">📍 定位设备</li>
        <li @click="contextEdit">✏️ 编辑属性</li>
        <li @click="contextDelete">🗑️ 删除设备</li>
      </ul>
    </div>

    <!-- 设备名称输入弹窗 -->
    <el-dialog 
      title="输入天线信息" 
      v-model="showNameDialog" 
      width="450px"
      :close-on-click-modal="false"
      class="custom-dialog"
    >
      <el-form :model="tempAntenna" label-width="80px">
        <el-form-item label="天线名称" required>
          <el-input v-model="tempAntenna.name" placeholder="请输入天线名称" />
        </el-form-item>
        <el-form-item label="天线类型">
          <el-select v-model="tempAntenna.type" style="width: 100%">
            <el-option label="📡 全向天线" value="omni" />
            <el-option label="🎯 定向天线" value="directional" />
            <el-option label="🧠 智能天线" value="smart" />
          </el-select>
        </el-form-item>
        <el-form-item label="安装高度(m)">
          <el-input v-model.number="tempAntenna.height" placeholder="默认90m" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="cancelAdd">取消</el-button>
        <el-button type="primary" @click="confirmAdd">确认添加</el-button>
      </template>
    </el-dialog>

    <!-- 基站编辑弹窗 -->
    <el-dialog 
      title="编辑基站信息" 
      v-model="showStationDialog" 
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
      title="编辑天线信息" 
      v-model="showAntennaDialog" 
      width="450px"
      class="custom-dialog"
    >
      <el-form :model="editAntennaForm" label-width="80px">
        <el-form-item label="天线名称" required>
          <el-input v-model="editAntennaForm.name" placeholder="请输入天线名称" />
        </el-form-item>
        <el-form-item label="天线类型">
          <el-select v-model="editAntennaForm.type" style="width: 100%">
            <el-option label="📡 全向天线" value="omni" />
            <el-option label="🎯 定向天线" value="directional" />
            <el-option label="🧠 智能天线" value="smart" />
          </el-select>
        </el-form-item>
        <el-form-item label="经度">
          <el-input v-model.number="editAntennaForm.lng" placeholder="经度" />
        </el-form-item>
        <el-form-item label="纬度">
          <el-input v-model.number="editAntennaForm.lat" placeholder="纬度" />
        </el-form-item>
        <el-form-item label="高度(m)">
          <el-input v-model.number="editAntennaForm.height" placeholder="高度" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAntennaDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmEditAntenna">确认保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
// 组件引用
const cesiumContainer = ref(null);
const searchKeyword = ref('');
const antennaKeyword = ref('');
const addMode = ref(false);
const showNameDialog = ref(false);
const showStationDialog = ref(false);
const showAntennaDialog = ref(false);
const showContextMenu = ref(false);
const cesiumViewer = ref(null);
const autoRotate = ref(false);
const showGrid = ref(true);
const showLabels = ref(true);
const activeTab = ref('stations');
const mode = ref('model');
// 当前坐标显示
const currentLng = ref(116.397428);
const currentLat = ref(39.90923);
const currentHeight = ref(0);
// 右键菜单位置
const menuPosition = reactive({ x: 0, y: 0 });
const contextAntenna = ref(null);
// 基站信息
const stationName = ref('北京测试基站');
const selectedStation = ref(null);
const stationPosition = reactive({
 lng: 116.397428,
 lat: 39.90923,
 height: 100
});
// 附近基站列表
const nearbyStations = ref([
 { id: 1, name: '测试基站A', lng: 116.397428, lat: 39.90923, height: 100 },
 { id: 2, name: '测试基站B', lng: 116.407428, lat: 39.91923, height: 80 },
 { id: 3, name: '测试基站C', lng: 116.387428, lat: 39.89923, height: 120 }
]);
// 天线列表
const antennas = ref([]);
// 表单数据
const newAntennaForm = reactive({
 name: '',
 lng: 116.397428,
 lat: 39.90923,
 height: 90,
 type: 'omni'
});
// 临时天线数据
const tempAntenna = reactive({
 name: '',
 lng: 0,
 lat: 0,
 height: 90,
 type: 'omni'
});
// 基站表单
const stationForm = reactive({
 id: null,
 name: '',
 lng: 116.397428,
 lat: 39.90923,
 height: 100
});
// 天线编辑表单
const editAntennaForm = reactive({
 id: null,
 name: '',
 lng: 116.397428,
 lat: 39.90923,
 height: 90,
 type: 'omni'
});
// 过滤后的天线列表
const filteredAntennas = computed(() => {
 if (!antennaKeyword.value)
 return antennas.value;
 return antennas.value.filter(ant => ant.name.toLowerCase().includes(antennaKeyword.value.toLowerCase()));
});
// 获取天线类型颜色
const getAntennaColor = (type) => {
 const colors = {
 'omni': '#3b82f6',
 'directional': '#22c55e',
 'smart': '#a855f7'
 };
 return colors[type] || '#6b7280';
};
// 获取天线类型名称
const getAntennaTypeName = (type) => {
 const names = {
 'omni': '全向天线',
 'directional': '定向天线',
 'smart': '智能天线'
 };
 return names[type] || '未知';
};
// 初始化Cesium场景
const initCesium = () => {
 if (!cesiumContainer.value)
 return;
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
 cesiumViewer.value.scene.backgroundColor = Cesium.Color.fromCssColorString('#0a1628');
 const cameraPosition = Cesium.Cartesian3.fromDegrees(stationPosition.lng, stationPosition.lat, 250);
 cesiumViewer.value.camera.setView({
 destination: cameraPosition,
 orientation: {
 heading: 0,
 pitch: Cesium.Math.toRadians(-45),
 roll: 0
 }
 });
 addStationTower();
 addCommunicationSiteModel();
 addGroundGrid();
 antennas.value.forEach(antenna => {
 addAntennaEntity(antenna);
 });
 // 添加鼠标移动事件获取坐标
 cesiumViewer.value.scene.screenSpaceEventHandler.setInputAction((event) => {
 const ray = cesiumViewer.value.camera.getPickRay(event.endPosition);
 if (ray) {
 const globe = cesiumViewer.value.scene.globe;
 const intersection = globe.pick(ray, cesiumViewer.value.scene);
 if (intersection) {
 const cartographic = Cesium.Cartographic.fromCartesian(intersection);
 currentLng.value = Cesium.Math.toDegrees(cartographic.longitude);
 currentLat.value = Cesium.Math.toDegrees(cartographic.latitude);
 currentHeight.value = cartographic.height;
 }
 }
 }, Cesium.ScreenSpaceEventType.MOUSE_MOVE);
 cesiumViewer.value.scene.screenSpaceEventHandler.setInputAction((event) => {
 handleSceneClick(event);
 }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
 cesiumViewer.value.scene.screenSpaceEventHandler.setInputAction((event) => {
 handleRightClick(event);
 }, Cesium.ScreenSpaceEventType.RIGHT_CLICK);
 console.log('Cesium场景初始化完成');
 }
 catch (error) {
 console.error('Cesium初始化失败:', error);
 ElMessage.error('Cesium加载失败');
 }
};
// 添加基站塔
const addStationTower = () => {
 if (!cesiumViewer.value)
 return;
 const center = Cesium.Cartesian3.fromDegrees(stationPosition.lng, stationPosition.lat, 0);
 const platformEntity = cesiumViewer.value.entities.add({
 position: center,
 box: {
 dimensions: new Cesium.Cartesian3(30, 30, 2),
 material: Cesium.Color.GRAY.withAlpha(0.9),
 outline: true,
 outlineColor: Cesium.Color.WHITE,
 outlineWidth: 2
 }
 });
 const towerHeight = stationPosition.height;
 const towerEntity = cesiumViewer.value.entities.add({
 position: Cesium.Cartesian3.fromDegrees(stationPosition.lng, stationPosition.lat, towerHeight / 2),
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
 const topPlatformEntity = cesiumViewer.value.entities.add({
 position: Cesium.Cartesian3.fromDegrees(stationPosition.lng, stationPosition.lat, towerHeight + 1),
 box: {
 dimensions: new Cesium.Cartesian3(10, 10, 2),
 material: Cesium.Color.fromCssColorString('#2d3748'),
 outline: true,
 outlineColor: Cesium.Color.WHITE,
 outlineWidth: 2
 }
 });
 const labelEntity = cesiumViewer.value.entities.add({
 position: Cesium.Cartesian3.fromDegrees(stationPosition.lng, stationPosition.lat, towerHeight + 15),
 label: {
 text: stationName.value,
 font: '18px sans-serif',
 fillColor: Cesium.Color.WHITE,
 outlineColor: Cesium.Color.BLACK,
 outlineWidth: 3,
 style: Cesium.LabelStyle.FILL_AND_OUTLINE,
 verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
 disableDepthTestDistance: Number.POSITIVE_INFINITY,
 show: showLabels.value
 }
 });
};
// 添加通信厂区模型
const addCommunicationSiteModel = () => {
 if (!cesiumViewer.value)
 return;
 const modelUrl = '/models/communication_site.glb';
 const modelPosition = Cesium.Cartesian3.fromDegrees(stationPosition.lng - 0.002, stationPosition.lat - 0.001, 0);
 const modelEntity = cesiumViewer.value.entities.add({
 position: modelPosition,
 model: {
 uri: modelUrl,
 scale: 0.3,
 minimumPixelSize: 30,
 maximumScale: 100,
 heightReference: Cesium.HeightReference.CLAMP_TO_GROUND
 }
 });
 console.log('正在加载通信厂区模型:', modelUrl);
};
// 添加地面网格
const addGroundGrid = () => {
 if (!cesiumViewer.value)
 return;
 const gridSize = 150;
 const step = 30;
 const lng = stationPosition.lng;
 const lat = stationPosition.lat;
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
// 添加天线实体
const addAntennaEntity = (antenna) => {
 if (!cesiumViewer.value)
 return;
 const position = Cesium.Cartesian3.fromDegrees(antenna.lng, antenna.lat, antenna.height);
 const entity = cesiumViewer.value.entities.add({
 id: `antenna_${antenna.id}`,
 antennaId: antenna.id,
 position: position,
 cylinder: {
 length: 3,
 topRadius: 0.5,
 bottomRadius: 0.8,
 material: Cesium.Color.fromCssColorString('#64748b'),
 outline: true,
 outlineColor: Cesium.Color.WHITE,
 outlineWidth: 1
 },
 box: {
 dimensions: new Cesium.Cartesian3(2, 2, 4),
 material: Cesium.Color.fromCssColorString(antenna.color || getAntennaColor(antenna.type)),
 outline: true,
 outlineColor: Cesium.Color.WHITE,
 outlineWidth: 1
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
};
// 更新天线实体
const updateAntennaEntity = (antenna) => {
 if (!cesiumViewer.value)
 return;
 const entities = cesiumViewer.value.entities.values;
 for (let i = 0; i < entities.length; i++) {
 const entity = entities[i];
 if (entity.antennaId === antenna.id) {
 const newPosition = Cesium.Cartesian3.fromDegrees(antenna.lng, antenna.lat, antenna.height);
 entity.position = newPosition;
 if (entity.label) {
 entity.label.text = antenna.name;
 }
 break;
 }
 }
};
// 删除天线实体
const removeAntennaEntity = (antennaId) => {
 if (!cesiumViewer.value)
 return;
 const entities = cesiumViewer.value.entities.values;
 for (let i = entities.length - 1; i >= 0; i--) {
 const entity = entities[i];
 if (entity.antennaId === antennaId) {
 cesiumViewer.value.entities.remove(entity);
 break;
 }
 }
};
// 处理场景点击
const handleSceneClick = (event) => {
 if (!addMode.value)
 return;
 const ray = cesiumViewer.value.camera.getPickRay(event.position);
 if (!ray)
 return;
 const globe = cesiumViewer.value.scene.globe;
 const intersection = globe.pick(ray, cesiumViewer.value.scene);
 if (intersection) {
 const cartographic = Cesium.Cartographic.fromCartesian(intersection);
 const lng = Cesium.Math.toDegrees(cartographic.longitude);
 const lat = Cesium.Math.toDegrees(cartographic.latitude);
 tempAntenna.lng = lng;
 tempAntenna.lat = lat;
 tempAntenna.height = 90;
 tempAntenna.name = '';
 showNameDialog.value = true;
 }
};
// 处理右键点击
const handleRightClick = (event) => {
 event.preventDefault();
 const pickedObject = cesiumViewer.value.scene.pick(event.position);
 if (pickedObject && pickedObject.id && pickedObject.id.antennaId) {
 const antennaId = pickedObject.id.antennaId;
 const antenna = antennas.value.find(a => a.id === antennaId);
 if (antenna) {
 contextAntenna.value = antenna;
 menuPosition.x = event.position.x;
 menuPosition.y = event.position.y;
 showContextMenu.value = true;
 document.addEventListener('click', closeContextMenu);
 }
 }
};
const closeContextMenu = () => {
 showContextMenu.value = false;
 document.removeEventListener('click', closeContextMenu);
};
const contextLocate = () => {
 if (contextAntenna.value) {
 locateAntenna(contextAntenna.value);
 }
 closeContextMenu();
};
const contextEdit = () => {
 if (contextAntenna.value) {
 editAntenna(contextAntenna.value);
 }
 closeContextMenu();
};
const contextDelete = () => {
 if (contextAntenna.value) {
 deleteAntenna(contextAntenna.value);
 }
 closeContextMenu();
};
// 切换添加模式
const toggleAddMode = () => {
 addMode.value = !addMode.value;
 if (!addMode.value) {
 showNameDialog.value = false;
 }
};
// 确认添加天线
const confirmAdd = () => {
 if (!tempAntenna.name.trim()) {
 ElMessage.warning('请输入天线名称');
 return;
 }
 const newAntenna = {
 id: Date.now(),
 name: tempAntenna.name,
 lng: tempAntenna.lng,
 lat: tempAntenna.lat,
 height: tempAntenna.height || 90,
 type: tempAntenna.type,
 color: getAntennaColor(tempAntenna.type)
 };
 antennas.value.push(newAntenna);
 addAntennaEntity(newAntenna);
 showNameDialog.value = false;
 addMode.value = false;
 ElMessage.success('天线添加成功');
};
// 取消添加
const cancelAdd = () => {
 showNameDialog.value = false;
 addMode.value = false;
};
// 编辑天线
const editAntenna = (antenna) => {
 editAntennaForm.id = antenna.id;
 editAntennaForm.name = antenna.name;
 editAntennaForm.lng = antenna.lng;
 editAntennaForm.lat = antenna.lat;
 editAntennaForm.height = antenna.height;
 editAntennaForm.type = antenna.type;
 showAntennaDialog.value = true;
};
// 确认编辑天线
const confirmEditAntenna = () => {
 if (!editAntennaForm.name.trim()) {
 ElMessage.warning('请输入天线名称');
 return;
 }
 const antenna = antennas.value.find(a => a.id === editAntennaForm.id);
 if (antenna) {
 antenna.name = editAntennaForm.name;
 antenna.lng = editAntennaForm.lng;
 antenna.lat = editAntennaForm.lat;
 antenna.height = editAntennaForm.height;
 antenna.type = editAntennaForm.type;
 antenna.color = getAntennaColor(editAntennaForm.type);
 updateAntennaEntity(antenna);
 }
 showAntennaDialog.value = false;
 ElMessage.success('天线信息更新成功');
};
// 定位天线
const locateAntenna = (antenna) => {
 if (!cesiumViewer.value)
 return;
 const position = Cesium.Cartesian3.fromDegrees(antenna.lng, antenna.lat, antenna.height + 30);
 cesiumViewer.value.camera.flyTo({
 destination: position,
 orientation: {
 heading: 0,
 pitch: Cesium.Math.toRadians(-30),
 roll: 0
 },
 duration: 1.5
 });
};
// 删除天线
const deleteAntenna = (antenna) => {
 const index = antennas.value.findIndex(a => a.id === antenna.id);
 if (index > -1) {
 antennas.value.splice(index, 1);
 }
 removeAntennaEntity(antenna.id);
 ElMessage.success('删除成功');
};
// 基站操作
const handleAddBaseStationClick = () => {
 stationForm.id = null;
 stationForm.name = '';
 stationForm.lng = stationPosition.lng;
 stationForm.lat = stationPosition.lat;
 stationForm.height = 100;
 showStationDialog.value = true;
};
const editStation = (station) => {
 stationForm.id = station.id;
 stationForm.name = station.name;
 stationForm.lng = station.lng;
 stationForm.lat = station.lat;
 stationForm.height = station.height;
 showStationDialog.value = true;
};
const confirmAddBaseStation = () => {
 if (!stationForm.name.trim()) {
 ElMessage.warning('请输入基站名称');
 return;
 }
 if (!stationForm.lng || !stationForm.lat) {
 ElMessage.warning('请输入经纬度');
 return;
 }
 const stationData = { ...stationForm };
 const existingIndex = nearbyStations.value.findIndex(s => s.id === stationData.id);
 if (existingIndex >= 0) {
 nearbyStations.value[existingIndex] = stationData;
 if (selectedStation.value?.id === stationData.id) {
 selectedStation.value = stationData;
 }
 showStationDialog.value = false;
 ElMessage.success('基站信息更新成功');
 }
 else {
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
 stationPosition.lng = station.lng;
 stationPosition.lat = station.lat;
 stationPosition.height = station.height;
 stationName.value = station.name;
 if (cesiumViewer.value) {
 cesiumViewer.value.entities.removeAll();
 nextTick(() => {
 initCesium();
 });
 }
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
 }
 }
 ElMessage.success('删除成功');
 }).catch(() => {
 ElMessage.info('已取消删除');
 });
};
// 视图控制
const zoomIn = () => {
 if (cesiumViewer.value) {
 cesiumViewer.value.camera.zoomIn(1.2);
 }
};
const zoomOut = () => {
 if (cesiumViewer.value) {
 cesiumViewer.value.camera.zoomOut(1.2);
 }
};
const resetView = () => {
 if (!cesiumViewer.value)
 return;
 const cameraPosition = Cesium.Cartesian3.fromDegrees(stationPosition.lng, stationPosition.lat, 250);
 cesiumViewer.value.camera.setView({
 destination: cameraPosition,
 orientation: {
 heading: 0,
 pitch: Cesium.Math.toRadians(-45),
 roll: 0
 }
 });
};
const flyToStation = () => {
 resetView();
};
const setView = (viewType) => {
 if (!cesiumViewer.value)
 return;
 const positions = {
 top: { dest: Cesium.Cartesian3.fromDegrees(stationPosition.lng, stationPosition.lat, 300), orient: { heading: 0, pitch: Cesium.Math.toRadians(-90), roll: 0 } },
 front: { dest: Cesium.Cartesian3.fromDegrees(stationPosition.lng - 0.003, stationPosition.lat, 150), orient: { heading: 0, pitch: Cesium.Math.toRadians(-15), roll: 0 } },
 side: { dest: Cesium.Cartesian3.fromDegrees(stationPosition.lng, stationPosition.lat - 0.003, 150), orient: { heading: Cesium.Math.toRadians(90), pitch: Cesium.Math.toRadians(-15), roll: 0 } },
 iso: { dest: Cesium.Cartesian3.fromDegrees(stationPosition.lng - 0.002, stationPosition.lat - 0.002, 200), orient: { heading: Cesium.Math.toRadians(45), pitch: Cesium.Math.toRadians(-30), roll: 0 } }
 };
 const config = positions[viewType];
 cesiumViewer.value.camera.flyTo({
 destination: config.dest,
 orientation: config.orient,
 duration: 1
 });
};
const toggleGrid = () => {
};
const toggleLabels = () => {
 if (cesiumViewer.value) {
 const entities = cesiumViewer.value.entities.values;
 for (let i = 0; i < entities.length; i++) {
 const entity = entities[i];
 if (entity.label) {
 entity.label.show = showLabels.value;
 }
 }
 }
};
const toggleAutoRotate = () => {
 if (cesiumViewer.value) {
 cesiumViewer.value.scene.camera.lookAtTransform(Cesium.Matrix4.IDENTITY);
 if (autoRotate.value) {
 cesiumViewer.value.scene.camera.enableAutoRotation = true;
 }
 else {
 cesiumViewer.value.scene.camera.enableAutoRotation = false;
 }
 }
};
// 生命周期
onMounted(() => {
 nextTick(() => {
 initCesium();
 });
});
onUnmounted(() => {
 if (cesiumViewer.value) {
 cesiumViewer.value.destroy();
 cesiumViewer.value = null;
 }
});
</script>

<style scoped>
.cesium-station-scene {
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

/* Cesium容器 */
.cesium-container {
  flex: 1;
  border-radius: 12px;
  overflow: hidden;
  position: relative;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
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

/* 添加模式提示 */
.add-mode-hint {
  position: absolute;
  top: 15px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;
}

/* 侧边栏 */
.side-panel {
  width: 400px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow: hidden;
  z-index: 100;
}

.tab-container {
  flex: 1;
  background: rgba(10, 22, 40, 0.9);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.tab-content {
  padding: 15px;
}

.search-bar {
  margin-bottom: 15px;
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

.add-antenna-btns {
  display: flex;
  gap: 10px;
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

/* 视图控制卡片 */
.view-card {
  background: transparent;
  border: none;
}

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

/* 右键菜单 */
.context-menu {
  position: fixed;
  background: rgba(20, 30, 50, 0.95);
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
  z-index: 1000;
}

.context-menu ul {
  margin: 0;
  padding: 0;
  list-style: none;
}

.context-menu li {
  padding: 10px 20px;
  cursor: pointer;
  font-size: 13px;
  color: #fff;
  border-radius: 4px;
  transition: background 0.2s;
}

.context-menu li:hover {
  background: rgba(255, 255, 255, 0.1);
}

/* 自定义弹窗 */
.custom-dialog {
  .el-dialog {
    background: rgba(20, 30, 50, 0.95);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
  }
  
  .el-dialog__header {
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  }
  
  .el-dialog__title {
    color: #fff;
  }
  
  .el-form-item__label {
    color: #909399;
  }
  
  .el-input__wrapper {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
  }
  
  .el-select {
    .el-input__wrapper {
      background: rgba(255, 255, 255, 0.05);
    }
  }
}
</style>