<template>
  <div class="cesium-station-scene">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <div class="mode-switch">
        <el-button 
          :type="mode === 'model' ? 'primary' : 'default'" 
          class="mode-btn"
          @click="mode = 'model'"
        >
          <el-icon class="btn-icon">
            <Box />
          </el-icon>
          <span>模型模式</span>
        </el-button>
        <el-button 
          :type="mode === 'analysis' ? 'primary' : 'default'" 
          class="mode-btn"
          @click="mode = 'analysis'"
        >
          <el-icon class="btn-icon">
            <DataAnalysis />
          </el-icon>
          <span>分析模式</span>
        </el-button>
      </div>
      
      <div class="scene-info">
        <el-tag
          type="success"
          class="info-tag"
        >
          <el-icon class="tag-icon">
            <Location />
          </el-icon>
          {{ stationName }}
        </el-tag>
        <el-tag
          type="info"
          class="info-tag"
        >
          <el-icon class="tag-icon">
            <Connection />
          </el-icon>
          天线: {{ antennas.length }} 个
        </el-tag>
        <el-tag class="info-tag">
          <el-icon class="tag-icon">
            <Aim />
          </el-icon>
          {{ mode === 'model' ? '建模' : '分析' }}
        </el-tag>
      </div>
      
      <div class="view-controls">
        <el-button
          icon="ZoomIn"
          class="control-btn"
          @click="zoomIn"
        >
          放大
        </el-button>
        <el-button
          icon="ZoomOut"
          class="control-btn"
          @click="zoomOut"
        >
          缩小
        </el-button>
        <el-button
          icon="Refresh"
          class="control-btn"
          @click="resetView"
        >
          复位
        </el-button>
        <el-button
          icon="MapPin"
          class="control-btn"
          @click="flyToStation"
        >
          飞向基站
        </el-button>
      </div>
    </div>

    <div class="main-content">
      <!-- Cesium场景容器 -->
      <div
        ref="cesiumContainer"
        class="cesium-container"
      >
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
        <div
          v-if="addMode"
          class="add-mode-hint"
        >
          <el-tag
            type="warning"
            size="large"
          >
            <span><el-icon><Warning /></el-icon> 添加模式：点击场景放置天线</span>
          </el-tag>
        </div>
      </div>

      <!-- 侧边栏 -->
      <div class="side-panel">
        <el-tabs
          v-model="activeTab"
          type="border-card"
          class="tab-container"
        >
          <!-- 基站管理 -->
          <el-tab-pane
            label="基站管理"
            name="stations"
          >
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
                    <el-button
                      size="small"
                      icon="Edit"
                      @click.stop="editStation(station)"
                    >
                      编辑
                    </el-button>
                    <el-button
                      size="small"
                      type="danger"
                      icon="Delete"
                      @click.stop="deleteBaseStation(station)"
                    >
                      删除
                    </el-button>
                  </div>
                </div>
              </div>
              <el-button
                class="add-station-btn"
                icon="Plus"
                @click="handleAddBaseStationClick"
              >
                + 添加基站模型
              </el-button>
            </div>
          </el-tab-pane>
          
          <!-- 天线设备 -->
          <el-tab-pane
            label="天线设备"
            name="antennas"
          >
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
                  <div
                    class="antenna-icon"
                    :style="{ background: antenna.color }"
                  >
                    <el-icon v-if="antenna.type === 'omni'">
                      <Position />
                    </el-icon>
                    <el-icon v-else-if="antenna.type === 'directional'">
                      <Aim />
                    </el-icon>
                    <el-icon v-else>
                      <MagicStick />
                    </el-icon>
                  </div>
                  <div class="antenna-info">
                    <div class="antenna-header">
                      <span class="antenna-name">{{ antenna.name }}</span>
                      <span
                        class="antenna-type-badge"
                        :class="antenna.type"
                      >
                        {{ getAntennaTypeName(antenna.type) }}
                      </span>
                    </div>
                    <span class="antenna-coord">
                      {{ antenna.lng.toFixed(6) }}, {{ antenna.lat.toFixed(6) }}, {{ antenna.height }}m
                    </span>
                  </div>
                  <div class="antenna-actions">
                    <el-button
                      size="small"
                      icon="MapPin"
                      @click="locateAntenna(antenna)"
                    >
                      定位
                    </el-button>
                    <el-button
                      size="small"
                      icon="Edit"
                      @click="editAntenna(antenna)"
                    >
                      编辑
                    </el-button>
                    <el-button
                      size="small"
                      type="danger"
                      icon="Delete"
                      @click="deleteAntenna(antenna)"
                    >
                      删除
                    </el-button>
                  </div>
                </div>
                <div
                  v-if="filteredAntennas.length === 0"
                  class="empty-state"
                >
                  <div class="empty-icon">
                    <el-icon><Position /></el-icon>
                  </div>
                  <div>暂无天线设备</div>
                  <div class="empty-hint">
                    点击上方"添加天线"按钮添加
                  </div>
                </div>
              </div>
              <div class="add-antenna-btns">
                <el-button
                  :type="addMode ? 'danger' : 'primary'"
                  icon="Plus"
                  @click="toggleAddMode"
                >
                  {{ addMode ? '退出添加' : '+ 添加天线' }}
                </el-button>
              </div>
            </div>
          </el-tab-pane>
          
          <!-- 视图控制 -->
          <el-tab-pane
            label="视图控制"
            name="view"
          >
            <div class="tab-content">
              <el-card class="view-card">
                <div class="view-section">
                  <h4>视角预设</h4>
                  <div class="preset-buttons">
                    <el-button
                      icon="Top"
                      @click="setView('top')"
                    >
                      俯视图
                    </el-button>
                    <el-button
                      icon="Eye"
                      @click="setView('front')"
                    >
                      前视图
                    </el-button>
                    <el-button
                      icon="Eye"
                      @click="setView('side')"
                    >
                      侧视图
                    </el-button>
                    <el-button
                      icon="Eye"
                      @click="setView('iso')"
                    >
                      等轴测
                    </el-button>
                  </div>
                </div>
                
                <div class="view-section">
                  <h4>显示设置</h4>
                  <el-switch
                    v-model="showGrid"
                    @change="toggleGrid"
                  >
                    显示网格
                  </el-switch>
                  <el-switch
                    v-model="showLabels"
                    @change="toggleLabels"
                  >
                    显示标签
                  </el-switch>
                  <el-switch
                    v-model="autoRotate"
                    @change="toggleAutoRotate"
                  >
                    自动旋转
                  </el-switch>
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

          <!-- AI 智能设计 -->
          <el-tab-pane
            label="AI 智能设计"
            name="ai"
          >
            <div class="tab-content">
              <div class="search-bar">
                <el-input
                  v-model="aiInput"
                  type="textarea"
                  :rows="4"
                  placeholder="用自然语言描述建站需求，如：在运城学院建宏基站，站高30米，覆盖半径500米，频段FDD-LTE-1800，三扇区，城区"
                />
              </div>
              <el-button
                class="add-station-btn"
                type="primary"
                :loading="aiLoading"
                icon="MagicStick"
                @click="generateSceneFromAI"
              >
                {{ aiLoading ? 'AI 解析中…' : 'AI 解析并生成 3D 场景' }}
              </el-button>
              <div
                v-if="aiResult"
                class="ai-result"
              >
                <div class="ai-result-title">
                  解析结果
                </div>
                <ul class="ai-result-list">
                  <li v-if="aiResult.template_type">
                    <span>站型</span>{{ TYPE_LABEL[aiResult.template_type] }}
                  </li>
                  <li v-if="aiResult.scenario">
                    <span>场景</span>{{ SCENARIO_LABEL[aiResult.scenario] }}
                  </li>
                  <li v-if="aiResult.frequency_band">
                    <span>频段</span>{{ aiResult.frequency_band }}
                  </li>
                  <li v-if="aiResult.tower_height">
                    <span>塔高</span>{{ aiResult.tower_height }} m
                  </li>
                  <li v-if="aiResult.antenna_height">
                    <span>挂高</span>{{ aiResult.antenna_height }} m
                  </li>
                  <li v-if="aiResult.sector_count != null">
                    <span>扇区</span>{{ aiResult.sector_count === 0 ? '全向' : aiResult.sector_count + ' 扇区' }}
                  </li>
                  <li v-if="aiResult.coverage_radius">
                    <span>覆盖半径</span>{{ aiResult.coverage_radius }} m
                  </li>
                  <li v-if="aiResult.center_longitude">
                    <span>坐标</span>{{ aiResult.center_longitude.toFixed(4) }}, {{ aiResult.center_latitude.toFixed(4) }}
                  </li>
                </ul>
                <div
                  v-if="aiResult.notes"
                  class="ai-notes"
                >
                  备注：{{ aiResult.notes }}
                </div>
                <div class="ai-coverage-actions">
                  <el-button
                    type="primary"
                    icon="DataAnalysis"
                    @click="generateCoverage"
                  >
                    生成 3D 覆盖热力图
                  </el-button>
                  <el-button
                    icon="Delete"
                    @click="clearHeatmap"
                  >
                    清除热力图
                  </el-button>
                  <el-button
                    icon="Document"
                    @click="showCoverageReport"
                  >
                    覆盖报告
                  </el-button>
                </div>
                <div class="ai-coverage-opacity">
                  <span class="opacity-label">透明度</span>
                  <el-slider
                    v-model="coverageOpacity"
                    :min="5"
                    :max="90"
                    class="opacity-slider"
                    @change="updateCoverageOpacity"
                  />
                </div>
              </div>
              <div
                v-if="aiError"
                class="ai-error"
              >
                {{ aiError }}
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>

    <!-- 右键菜单 -->
    <div 
      v-if="showContextMenu" 
      class="context-menu" 
      :style="{ left: menuPosition.x + 'px', top: menuPosition.y + 'px' }"
    >
      <ul>
        <li @click="contextLocate">
          <el-icon><Location /></el-icon>定位设备
        </li>
        <li @click="contextEdit">
          <el-icon><Edit /></el-icon>编辑属性
        </li>
        <li @click="contextDelete">
          <el-icon><Delete /></el-icon>删除设备
        </li>
      </ul>
    </div>

    <!-- 设备名称输入弹窗 -->
    <el-dialog 
      v-model="showNameDialog" 
      title="输入天线信息" 
      width="450px"
      :close-on-click-modal="false"
      class="custom-dialog"
    >
      <el-form
        :model="tempAntenna"
        label-width="80px"
      >
        <el-form-item
          label="天线名称"
          required
        >
          <el-input
            v-model="tempAntenna.name"
            placeholder="请输入天线名称"
          />
        </el-form-item>
        <el-form-item label="天线类型">
          <el-select
            v-model="tempAntenna.type"
            style="width: 100%"
          >
            <el-option
              label="全向天线"
              value="omni"
            />
            <el-option
              label="定向天线"
              value="directional"
            />
            <el-option
              label="智能天线"
              value="smart"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="安装高度(m)">
          <el-input
            v-model.number="tempAntenna.height"
            placeholder="默认90m"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="cancelAdd">
          取消
        </el-button>
        <el-button
          type="primary"
          @click="confirmAdd"
        >
          确认添加
        </el-button>
      </template>
    </el-dialog>

    <!-- 基站编辑弹窗 -->
    <el-dialog 
      v-model="showStationDialog" 
      title="编辑基站信息" 
      width="450px"
      class="custom-dialog"
    >
      <el-form
        :model="stationForm"
        label-width="80px"
      >
        <el-form-item
          label="基站名称"
          required
        >
          <el-input
            v-model="stationForm.name"
            placeholder="请输入基站名称"
          />
        </el-form-item>
        <el-form-item label="经度">
          <el-input
            v-model.number="stationForm.lng"
            placeholder="经度"
          />
        </el-form-item>
        <el-form-item label="纬度">
          <el-input
            v-model.number="stationForm.lat"
            placeholder="纬度"
          />
        </el-form-item>
        <el-form-item label="塔高(m)">
          <el-input
            v-model.number="stationForm.height"
            placeholder="塔高"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showStationDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          @click="confirmAddBaseStation"
        >
          确认保存
        </el-button>
      </template>
    </el-dialog>

    <!-- 天线编辑弹窗 -->
    <el-dialog 
      v-model="showAntennaDialog" 
      title="编辑天线信息" 
      width="450px"
      class="custom-dialog"
    >
      <el-form
        :model="editAntennaForm"
        label-width="80px"
      >
        <el-form-item
          label="天线名称"
          required
        >
          <el-input
            v-model="editAntennaForm.name"
            placeholder="请输入天线名称"
          />
        </el-form-item>
        <el-form-item label="天线类型">
          <el-select
            v-model="editAntennaForm.type"
            style="width: 100%"
          >
            <el-option
              label="全向天线"
              value="omni"
            />
            <el-option
              label="定向天线"
              value="directional"
            />
            <el-option
              label="智能天线"
              value="smart"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="经度">
          <el-input
            v-model.number="editAntennaForm.lng"
            placeholder="经度"
          />
        </el-form-item>
        <el-form-item label="纬度">
          <el-input
            v-model.number="editAntennaForm.lat"
            placeholder="纬度"
          />
        </el-form-item>
        <el-form-item label="高度(m)">
          <el-input
            v-model.number="editAntennaForm.height"
            placeholder="高度"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAntennaDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          @click="confirmEditAntenna"
        >
          确认保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
export default { name: 'CesiumStationScene' }
</script>
<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import * as Cesium from 'cesium';
import { createViewer } from '@/composables/useCesiumCore.js';
import { DEFAULT_LOCATION } from '@/config/location.js';
import { logger } from '@/utils/logger.js';
import { llmAPI } from '@/utils/request.js';
import { useCoverageAnalysis } from '@/composables/useCoverageAnalysis.js';
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
// ===== AI 智能设计（自然语言需求 → LLM 解析 → 3D 场景自动生成） =====
const aiInput = ref('');
const aiLoading = ref(false);
const aiResult = ref(null);
const aiError = ref('');
const TYPE_LABEL = { macro: '宏基站', micro: '微基站', indoor: '室分系统' };
const SCENARIO_LABEL = { urban: '城区', suburban: '郊区', rural: '农村', indoor: '室内' };
// 当前坐标显示
const currentLng = ref(DEFAULT_LOCATION.longitude);
const currentLat = ref(DEFAULT_LOCATION.latitude);
const currentHeight = ref(0);
// 右键菜单位置
const menuPosition = reactive({ x: 0, y: 0 });
const contextAntenna = ref(null);
// 基站信息
const stationName = ref('运城学院测试基站');
const selectedStation = ref(null);
const stationPosition = reactive({
 lng: DEFAULT_LOCATION.longitude,
 lat: DEFAULT_LOCATION.latitude,
 height: 100
});
// 附近基站列表
const nearbyStations = ref([
 { id: 1, name: '测试基站A', lng: DEFAULT_LOCATION.longitude, lat: DEFAULT_LOCATION.latitude, height: 100 },
 { id: 2, name: '测试基站B', lng: 110.934222, lat: 35.122717, height: 80 },
 { id: 3, name: '测试基站C', lng: 110.929828, lat: 35.124791, height: 120 }
]);

// ===== 步骤2：3D 覆盖可视化（复用 useCoverageAnalysis，前端 Okumura-Hata 传播模型，离线可跑） =====
const coverageOpacity = ref(45)
// 把当前基站列表映射成覆盖分析所需的站点格式(longitude/latitude/towerHeight)
const coverageSites = computed(() => nearbyStations.value.map(s => ({
  id: s.id, longitude: s.lng, latitude: s.lat, towerHeight: s.height
})))
// AI 解析出的频段 → 载波频率(MHz) 映射（与 Design.vue 同源）
const FREQ_TO_MHZ = {
  'FDD-LTE-900': 900, 'FDD-LTE-1800': 1800, 'FDD-LTE-2100': 2100,
  '5G-N41': 2600, '5G-N78': 3500, '5G-N79': 4900, '700MHz': 700,
}
const bandToMHz = (band) => FREQ_TO_MHZ[band] || 2100
const currentBand = ref('FDD-LTE-1800')
const currentCoverageRadius = ref(500)
const {
  showCoverageReport, generateHeatmap, clearHeatmap, updateCoverageOpacity
} = useCoverageAnalysis({
  viewer: cesiumViewer,
  sites: coverageSites,
  coverageOpacity,
  frequencyMHz: 2100,
  coverageRadius: 500,
  environment: 'URBAN',
})
// AI 生成基站后的一键覆盖推演（闭环：AI设计→3D生成→覆盖推演→报告）
const generateCoverage = () => {
  if (!cesiumViewer.value) { ElMessage.warning('场景尚未就绪'); return }
  generateHeatmap(currentCoverageRadius.value || 500, bandToMHz(currentBand.value))
}
// 天线列表
const antennas = ref([]);
// 表单数据
const newAntennaForm = reactive({
 name: '',
 lng: DEFAULT_LOCATION.longitude,
 lat: DEFAULT_LOCATION.latitude,
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
 lng: DEFAULT_LOCATION.longitude,
 lat: DEFAULT_LOCATION.latitude,
 height: 100
});
// 天线编辑表单
const editAntennaForm = reactive({
 id: null,
 name: '',
 lng: DEFAULT_LOCATION.longitude,
 lat: DEFAULT_LOCATION.latitude,
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
 cesiumViewer.value = createViewer('cesiumContainer', {
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
 renderScene();
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
 
 }
 catch (error) {
 logger.error('CesiumStationScene', 'Cesium初始化失败', error);
 ElMessage.error('Cesium加载失败');
 }
};
// 渲染场景（初始化 / AI 生成 / 切换基站 共用：清空后按当前 stationPosition + antennas 重绘）
const renderScene = () => {
 if (!cesiumViewer.value) return;
 cesiumViewer.value.entities.removeAll();
 addStationTower();
 addCommunicationSiteModel();
 addGroundGrid();
 antennas.value.forEach(antenna => {
  addAntennaEntity(antenna);
 });
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
  renderScene();
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
// ===== AI 智能设计：自然语言需求 → LLM 解析 → 3D 场景自动生成 =====
const generateSceneFromAI = async () => {
 const text = aiInput.value.trim();
 if (!text) { ElMessage.warning('请输入设计需求描述'); return; }
 aiLoading.value = true; aiError.value = ''; aiResult.value = null;
 try {
  const res = await llmAPI.parseDesignParams(text);
  const p = res && res.data ? res.data.params : (res && res.params ? res.params : null);
  if (!p) throw new Error('解析结果为空');
  applyAIParamsToScene(p);
  aiResult.value = p;
  ElMessage.success('AI 场景已生成');
 } catch (e) {
  aiError.value = (e && e.message) || '解析失败';
  ElMessage.error('AI 解析失败：' + aiError.value);
  logger.error('CesiumStationScene', 'AI解析失败', e);
 } finally {
  aiLoading.value = false;
 }
};

const applyAIParamsToScene = (p) => {
 if (p.center_longitude != null && p.center_latitude != null) {
  stationPosition.lng = p.center_longitude;
  stationPosition.lat = p.center_latitude;
 }
 if (p.tower_height != null) stationPosition.height = p.tower_height;
 const typeL = TYPE_LABEL[p.template_type] || '基站';
 const scenL = SCENARIO_LABEL[p.scenario] || '';
 stationName.value = [scenL, typeL, p.frequency_band].filter(Boolean).join('·') || 'AI生成基站';
 antennas.value = buildAntennasFromParams(p);
 if (cesiumViewer.value) {
  renderScene();
  resetView();
 }
 const aiStation = { id: Date.now(), name: stationName.value, lng: stationPosition.lng, lat: stationPosition.lat, height: stationPosition.height };
 nearbyStations.value.unshift(aiStation);
 selectedStation.value = aiStation;
 currentBand.value = p.frequency_band || 'FDD-LTE-1800';
 currentCoverageRadius.value = p.coverage_radius || 500;
 // 步骤2：AI 生成后立即推演 3D 覆盖热力图（闭环亮点的关键一步）
 nextTick(() => {
  try { generateHeatmap(currentCoverageRadius.value, bandToMHz(currentBand.value)) }
  catch (e) { logger.warn('CesiumStationScene', '自动覆盖推演跳过', e) }
 });
};

const buildAntennasFromParams = (p) => {
 const cx = stationPosition.lng, cy = stationPosition.lat;
 const antH = p.antenna_height != null ? p.antenna_height : (stationPosition.height - 2 > 0 ? stationPosition.height - 2 : stationPosition.height);
 const sectors = p.sector_count != null ? p.sector_count : (p.template_type === 'micro' ? 3 : p.template_type === 'indoor' ? 0 : 3);
 const list = [];
 if (sectors === 0) {
  list.push(makeAntenna(Date.now(), '全向天线', cx, cy, antH, 'omni'));
 } else {
  const step = 360 / sectors;
  const R = 0.0003;
  for (let i = 0; i < sectors; i++) {
   const ang = (i * step) * Math.PI / 180;
   const lng = cx + R * Math.cos(ang);
   const lat = cy + R * Math.sin(ang);
   list.push(makeAntenna(Date.now() + i, sectors + '扇区-' + (i + 1), lng, lat, antH, 'directional'));
  }
 }
 return list;
};

const makeAntenna = (id, name, lng, lat, height, type) => ({
 id, name, lng, lat, height, type, color: getAntennaColor(type)
});

// 生命周期
onMounted(() => {
 nextTick(() => {
 initCesium();
 });
});
onUnmounted(() => {
 // 清理可能残留的事件监听器
 document.removeEventListener('click', closeContextMenu);
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
/* AI 智能设计面板 */
.ai-result {
  margin-top: 16px;
  padding: 14px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
}
.ai-result-title {
  font-weight: 600;
  color: #fff;
  margin-bottom: 10px;
  font-size: 13px;
}
.ai-result-list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.ai-result-list li {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  font-size: 13px;
  color: #cbd5e1;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}
.ai-result-list li span {
  color: #909399;
}
.ai-notes {
  margin-top: 10px;
  font-size: 12px;
  color: #909399;
}
.ai-error {
  margin-top: 12px;
  padding: 10px 12px;
  background: rgba(239, 68, 68, 0.15);
  border: 1px solid rgba(239, 68, 68, 0.4);
  border-radius: 8px;
  color: #fca5a5;
  font-size: 13px;
}

/* 步骤2：3D 覆盖可视化控制区 */
.ai-coverage-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
}
.ai-coverage-opacity {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}
.opacity-label {
  font-size: 13px;
  color: #909399;
  white-space: nowrap;
}
.opacity-slider {
  flex: 1;
  max-width: 220px;
}

</style>