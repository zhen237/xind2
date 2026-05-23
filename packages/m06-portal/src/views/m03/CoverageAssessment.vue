<template>
  <div class="coverage-assessment">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <h2>重点场所覆盖评估</h2>
      </div>
      <div class="toolbar-right">
        <el-button 
          type="primary" 
          @click="toggleAddMarkerMode"
          :class="{ active: addMarkerMode }"
        >
          <el-icon><Plus /></el-icon>
          {{ addMarkerMode ? '退出添加模式' : '添加标记点' }}
        </el-button>
        <el-button @click="clearAllCustomMarkers" v-if="customMarkers.length > 0">
          <el-icon><Delete /></el-icon>
          清除所有标记
        </el-button>
      </div>
    </div>
    
    <!-- 地图容器 -->
    <div ref="mapContainer" class="map-container"></div>
    
    <!-- 添加模式提示 -->
    <div v-if="addMarkerMode" class="add-mode-hint">
      <el-tag type="warning" size="large">
        <span>⚠️ 添加模式：点击地图创建红色标记点</span>
      </el-tag>
    </div>
    
    <!-- 右侧控制面板 -->
    <div class="control-panel">
      <el-card class="panel-card">
        <template #header>
          <div class="panel-header">
            <el-icon><Box /></el-icon>
            <span>重点场所覆盖评估</span>
          </div>
        </template>
        
        <!-- 搜索框 -->
        <div class="search-section">
          <el-input
            v-model="searchText"
            placeholder="搜索场所名称"
            @input="handleSearch"
            clearable
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </div>
        
        <!-- 筛选条件 -->
        <div class="filter-section">
          <el-form label-width="80px" label-position="left">
            <el-form-item label="场所类型">
              <el-select 
                v-model="filters.type" 
                placeholder="请选择类型"
                @change="handleFilterChange"
                clearable
              >
                <el-option
                  v-for="item in typeOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
            
            <el-form-item label="行政区">
              <el-select
                v-model="filters.area"
                placeholder="请选择区域"
                @change="handleFilterChange"
                clearable
              >
                <el-option
                  v-for="item in areaOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
          </el-form>
        </div>
        
        <!-- 按钮组 -->
        <div class="button-group">
          <el-button type="primary" @click="switchBaseLayer">
            <el-icon><Monitor /></el-icon>
            {{ currentLayerName }}
          </el-button>
          <el-button @click="zoomIn">
            <el-icon><Plus /></el-icon>
            放大
          </el-button>
          <el-button @click="zoomOut">
            <el-icon><Minus /></el-icon>
            缩小
          </el-button>
          <el-button @click="resetView">
            <el-icon><Refresh /></el-icon>
            重置视图
          </el-button>
        </div>
        
        <!-- 统计信息 -->
        <div class="statistics">
          <el-statistic title="场所总数" :value="filteredLocations.length" />
          <el-divider direction="vertical" />
          <el-statistic 
            title="已覆盖(≥90%)" 
            :value="coveredCount" 
            :value-style="{ color: '#67c23a' }"
          />
          <el-divider direction="vertical" />
          <el-statistic 
            title="自定义标记" 
            :value="customMarkers.length" 
            :value-style="{ color: '#f56c6c' }"
          />
        </div>
        
        <!-- 场所列表 -->
        <div class="location-list">
          <div class="list-title">场所列表</div>
          <el-scrollbar height="250px">
            <div
              v-for="location in filteredLocations"
              :key="location.id"
              class="location-item"
              :class="{ active: selectedLocation?.id === location.id }"
              @click="focusOnLocation(location)"
            >
              <div class="location-name">{{ location.name }}</div>
              <div class="location-info">
                <el-tag size="small" :type="getTypeTagType(location.type)">
                  {{ location.type }}
                </el-tag>
                <span class="coverage" :class="getCoverageClass(location.coverage)">
                  {{ location.coverage }}%
                </span>
              </div>
            </div>
          </el-scrollbar>
        </div>
        
        <!-- 自定义标记列表 -->
        <div v-if="customMarkers.length > 0" class="custom-marker-list">
          <div class="list-title">自定义标记</div>
          <el-scrollbar height="150px">
            <div
              v-for="marker in customMarkers"
              :key="marker.id"
              class="marker-item"
              @click="focusOnCustomMarker(marker)"
            >
              <div class="marker-name">{{ marker.name || '未命名标记' }}</div>
              <div class="marker-actions">
                <el-button size="mini" @click.stop="editCustomMarker(marker)">编辑</el-button>
                <el-button size="mini" type="danger" @click.stop="deleteCustomMarker(marker)">删除</el-button>
              </div>
            </div>
          </el-scrollbar>
        </div>
      </el-card>
    </div>
    
    <!-- 详细报告弹窗 -->
    <CoverageReport 
      :visible="showReport" 
      :place="reportPlace"
      @update:visible="showReport = false"
    />
    
    <!-- 自定义标记编辑弹窗 -->
    <el-dialog 
      title="编辑标记点" 
      :visible.sync="showMarkerDialog" 
      width="400px"
    >
      <el-form :model="markerForm" label-width="80px">
        <el-form-item label="标记名称">
          <el-input v-model="markerForm.name" placeholder="请输入标记名称" />
        </el-form-item>
        <el-form-item label="经度">
          <el-input v-model.number="markerForm.lng" />
        </el-form-item>
        <el-form-item label="纬度">
          <el-input v-model.number="markerForm.lat" />
        </el-form-item>
        <el-form-item label="简介">
          <el-textarea v-model="markerForm.description" placeholder="请输入标记简介" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showMarkerDialog = false">取消</el-button>
        <el-button type="primary" @click="saveMarker">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { 
  Box, 
  Search, 
  Monitor, 
  Plus, 
  Minus, 
  Refresh,
  Delete
} from '@element-plus/icons-vue'
import CoverageReport from '@/components/CoverageReport.vue'

// 高德地图API Key
const AMAP_KEY = '508bd9aba42a7f37dc25e8be995d10fc'

// 详细报告状态
const showReport = ref(false)
const reportPlace = ref({})

// 添加标记模式
const addMarkerMode = ref(false)

// 自定义标记列表
const customMarkers = ref([
  { id: 1001, name: '测试标记1', lng: 116.407428, lat: 39.91923, description: '这是一个测试标记点' },
  { id: 1002, name: '测试标记2', lng: 116.387428, lat: 39.92923, description: '另一个测试标记点' }
])

// 自定义标记对应的地图标记对象
const customMarkerObjects = ref([])

// 标记编辑弹窗
const showMarkerDialog = ref(false)
const markerForm = reactive({
  id: null,
  name: '',
  lng: 0,
  lat: 0,
  description: ''
})

// 模拟数据（包含完整字段）
const mockLocations = [
  { 
    id: 1, 
    name: '北京协和医院', 
    lng: 116.397428, 
    lat: 39.90923, 
    type: '医院', 
    area: '东城区', 
    coverage: 98,
    rsrp: -85,
    sinr: 25,
    uploadSpeed: 85,
    downloadSpeed: 350,
    latency: 22,
    improvement: 3.5,
    responsibleGrid: '东城网格A区',
    maintenanceUnit: '北京联通运维部',
    lastTestTime: '2024-01-15 14:30',
    trendData: { coverage: [95, 96, 98], rsrp: [-90, -88, -85], sinr: [22, 23, 25], downlink: [300, 320, 350] },
    nearbyStations: [
      { name: '东单基站-A', distance: 150, operator: '联通', band: '1800MHz', rsrp: -85, attribution: '自建' },
      { name: '王府井基站-B', distance: 280, operator: '移动', band: '2100MHz', rsrp: -92, attribution: '自建' },
      { name: '建国门基站', distance: 420, operator: '电信', band: '800MHz', rsrp: -98, attribution: '共享' }
    ],
    workOrders: [
      { orderNo: 'WO-20240115-001', createTime: '2024-01-15 09:30', type: '覆盖优化', status: '已完成', result: '天线调整完成，覆盖改善' },
      { orderNo: 'WO-20240108-003', createTime: '2024-01-08 14:20', type: '故障处理', status: '已完成', result: '信号干扰排除' }
    ]
  },
  { 
    id: 2, 
    name: '北京站', 
    lng: 116.427428, 
    lat: 39.90423, 
    type: '交通枢纽', 
    area: '东城区', 
    coverage: 95,
    rsrp: -92,
    sinr: 22,
    uploadSpeed: 75,
    downloadSpeed: 320,
    latency: 28,
    improvement: 2.1,
    responsibleGrid: '东城网格B区',
    maintenanceUnit: '北京移动运维部',
    lastTestTime: '2024-01-14 10:15',
    trendData: { coverage: [93, 94, 95], rsrp: [-95, -93, -92], sinr: [20, 21, 22], downlink: [280, 300, 320] },
    nearbyStations: [
      { name: '北京站基站', distance: 80, operator: '移动', band: '2600MHz', rsrp: -88, attribution: '自建' },
      { name: '崇文门基站', distance: 350, operator: '联通', band: '1800MHz', rsrp: -95, attribution: '共享' },
      { name: '前门基站', distance: 450, operator: '电信', band: '800MHz', rsrp: -100, attribution: '共享' }
    ],
    workOrders: [
      { orderNo: 'WO-20240110-002', createTime: '2024-01-10 11:00', type: '站点勘察', status: '进行中', result: '待制定优化方案' }
    ]
  },
  { 
    id: 3, 
    name: '国家体育场', 
    lng: 116.397428, 
    lat: 39.94423, 
    type: '场馆', 
    area: '朝阳区', 
    coverage: 92,
    rsrp: -98,
    sinr: 18,
    uploadSpeed: 65,
    downloadSpeed: 280,
    latency: 32,
    improvement: 1.2,
    responsibleGrid: '朝阳网格C区',
    maintenanceUnit: '北京电信运维部',
    lastTestTime: '2024-01-13 16:45',
    trendData: { coverage: [90, 91, 92], rsrp: [-100, -99, -98], sinr: [16, 17, 18], downlink: [250, 265, 280] },
    nearbyStations: [
      { name: '奥体中心基站', distance: 120, operator: '电信', band: '2100MHz', rsrp: -92, attribution: '自建' },
      { name: '亚运村基站', distance: 380, operator: '移动', band: '1800MHz', rsrp: -102, attribution: '共享' },
      { name: '安贞基站', distance: 480, operator: '联通', band: '2600MHz', rsrp: -105, attribution: '自建' }
    ],
    workOrders: [
      { orderNo: 'WO-20240105-004', createTime: '2024-01-05 09:00', type: '覆盖优化', status: '已完成', result: '新增室内天线' }
    ]
  },
  { 
    id: 4, 
    name: '北京大学', 
    lng: 116.317428, 
    lat: 39.98923, 
    type: '学校', 
    area: '海淀区', 
    coverage: 88,
    rsrp: -105,
    sinr: 15,
    uploadSpeed: 45,
    downloadSpeed: 220,
    latency: 38,
    improvement: -0.5,
    responsibleGrid: '海淀网格A区',
    maintenanceUnit: '北京联通运维部',
    lastTestTime: '2024-01-12 09:30',
    trendData: { coverage: [89, 88, 88], rsrp: [-102, -104, -105], sinr: [17, 16, 15], downlink: [240, 230, 220] },
    nearbyStations: [
      { name: '北大基站', distance: 200, operator: '联通', band: '1800MHz', rsrp: -98, attribution: '自建' },
      { name: '清华基站', distance: 350, operator: '移动', band: '2600MHz', rsrp: -108, attribution: '共享' },
      { name: '五道口基站', distance: 420, operator: '电信', band: '800MHz', rsrp: -110, attribution: '共享' }
    ],
    workOrders: [
      { orderNo: 'WO-20240112-006', createTime: '2024-01-12 14:00', type: '故障处理', status: '待处理', result: '待派单' }
    ]
  },
  { 
    id: 5, 
    name: '首都国际机场', 
    lng: 116.587428, 
    lat: 40.07923, 
    type: '交通枢纽', 
    area: '顺义区', 
    coverage: 99,
    rsrp: -78,
    sinr: 28,
    uploadSpeed: 120,
    downloadSpeed: 450,
    latency: 18,
    improvement: 4.2,
    responsibleGrid: '顺义网格A区',
    maintenanceUnit: '北京移动运维部',
    lastTestTime: '2024-01-16 08:00',
    trendData: { coverage: [96, 98, 99], rsrp: [-82, -80, -78], sinr: [25, 27, 28], downlink: [400, 420, 450] },
    nearbyStations: [
      { name: 'T1航站楼基站', distance: 50, operator: '移动', band: '2600MHz', rsrp: -72, attribution: '自建' },
      { name: 'T2航站楼基站', distance: 180, operator: '移动', band: '2100MHz', rsrp: -75, attribution: '自建' },
      { name: 'T3航站楼基站', distance: 280, operator: '联通', band: '1800MHz', rsrp: -80, attribution: '共享' }
    ],
    workOrders: []
  },
  { 
    id: 6, 
    name: '北京友谊医院', 
    lng: 116.357428, 
    lat: 39.93923, 
    type: '医院', 
    area: '西城区', 
    coverage: 91,
    rsrp: -100,
    sinr: 19,
    uploadSpeed: 55,
    downloadSpeed: 260,
    latency: 30,
    improvement: 1.8,
    responsibleGrid: '西城网格B区',
    maintenanceUnit: '北京电信运维部',
    lastTestTime: '2024-01-11 15:20',
    trendData: { coverage: [89, 90, 91], rsrp: [-102, -101, -100], sinr: [17, 18, 19], downlink: [240, 250, 260] },
    nearbyStations: [
      { name: '宣武门基站', distance: 220, operator: '电信', band: '800MHz', rsrp: -95, attribution: '自建' },
      { name: '西单基站', distance: 360, operator: '联通', band: '1800MHz', rsrp: -102, attribution: '共享' },
      { name: '复兴门基站', distance: 440, operator: '移动', band: '2100MHz', rsrp: -105, attribution: '共享' }
    ],
    workOrders: []
  },
  { 
    id: 7, 
    name: '北京南站', 
    lng: 116.387428, 
    lat: 39.86423, 
    type: '交通枢纽', 
    area: '丰台区', 
    coverage: 94,
    rsrp: -94,
    sinr: 21,
    uploadSpeed: 70,
    downloadSpeed: 300,
    latency: 25,
    improvement: 2.5,
    responsibleGrid: '丰台网格A区',
    maintenanceUnit: '北京联通运维部',
    lastTestTime: '2024-01-14 11:30',
    trendData: { coverage: [92, 93, 94], rsrp: [-96, -95, -94], sinr: [19, 20, 21], downlink: [270, 285, 300] },
    nearbyStations: [
      { name: '北京南站基站', distance: 60, operator: '联通', band: '2600MHz', rsrp: -88, attribution: '自建' },
      { name: '永定门基站', distance: 320, operator: '移动', band: '1800MHz', rsrp: -98, attribution: '共享' },
      { name: '陶然亭基站', distance: 460, operator: '电信', band: '800MHz', rsrp: -102, attribution: '共享' }
    ],
    workOrders: []
  },
  { 
    id: 8, 
    name: '水立方', 
    lng: 116.387428, 
    lat: 39.94423, 
    type: '场馆', 
    area: '朝阳区', 
    coverage: 93,
    rsrp: -96,
    sinr: 20,
    uploadSpeed: 68,
    downloadSpeed: 290,
    latency: 27,
    improvement: 2.0,
    responsibleGrid: '朝阳网格C区',
    maintenanceUnit: '北京移动运维部',
    lastTestTime: '2024-01-13 17:00',
    trendData: { coverage: [91, 92, 93], rsrp: [-98, -97, -96], sinr: [18, 19, 20], downlink: [265, 278, 290] },
    nearbyStations: [
      { name: '奥体中心基站', distance: 150, operator: '移动', band: '2100MHz', rsrp: -90, attribution: '自建' },
      { name: '北辰基站', distance: 390, operator: '联通', band: '1800MHz', rsrp: -99, attribution: '共享' },
      { name: '大屯基站', distance: 470, operator: '电信', band: '2600MHz', rsrp: -103, attribution: '共享' }
    ],
    workOrders: []
  },
  { 
    id: 9, 
    name: '清华大学', 
    lng: 116.327428, 
    lat: 39.99923, 
    type: '学校', 
    area: '海淀区', 
    coverage: 89,
    rsrp: -102,
    sinr: 16,
    uploadSpeed: 50,
    downloadSpeed: 240,
    latency: 35,
    improvement: 0.8,
    responsibleGrid: '海淀网格B区',
    maintenanceUnit: '北京电信运维部',
    lastTestTime: '2024-01-12 10:00',
    trendData: { coverage: [88, 89, 89], rsrp: [-103, -102, -102], sinr: [15, 16, 16], downlink: [230, 235, 240] },
    nearbyStations: [
      { name: '清华基站', distance: 180, operator: '电信', band: '800MHz', rsrp: -96, attribution: '自建' },
      { name: '北大基站', distance: 320, operator: '联通', band: '1800MHz', rsrp: -104, attribution: '共享' },
      { name: '中关村基站', distance: 410, operator: '移动', band: '2600MHz', rsrp: -106, attribution: '共享' }
    ],
    workOrders: []
  },
  { 
    id: 10, 
    name: '北京儿童医院', 
    lng: 116.347428, 
    lat: 39.86923, 
    type: '医院', 
    area: '西城区', 
    coverage: 96,
    rsrp: -88,
    sinr: 24,
    uploadSpeed: 80,
    downloadSpeed: 330,
    latency: 23,
    improvement: 3.0,
    responsibleGrid: '西城网格A区',
    maintenanceUnit: '北京移动运维部',
    lastTestTime: '2024-01-15 13:45',
    trendData: { coverage: [94, 95, 96], rsrp: [-92, -90, -88], sinr: [22, 23, 24], downlink: [300, 315, 330] },
    nearbyStations: [
      { name: '儿童医院基站', distance: 100, operator: '移动', band: '2600MHz', rsrp: -82, attribution: '自建' },
      { name: '月坛基站', distance: 290, operator: '联通', band: '1800MHz', rsrp: -92, attribution: '共享' },
      { name: '金融街基站', distance: 400, operator: '电信', band: '800MHz', rsrp: -96, attribution: '共享' }
    ],
    workOrders: []
  },
  { 
    id: 11, 
    name: '北京西站', 
    lng: 116.317428, 
    lat: 39.85423, 
    type: '交通枢纽', 
    area: '丰台区', 
    coverage: 97,
    rsrp: -86,
    sinr: 26,
    uploadSpeed: 95,
    downloadSpeed: 380,
    latency: 20,
    improvement: 3.8,
    responsibleGrid: '丰台网格B区',
    maintenanceUnit: '北京联通运维部',
    lastTestTime: '2024-01-16 09:20',
    trendData: { coverage: [94, 96, 97], rsrp: [-89, -87, -86], sinr: [24, 25, 26], downlink: [350, 365, 380] },
    nearbyStations: [
      { name: '北京西站基站', distance: 70, operator: '联通', band: '2600MHz', rsrp: -80, attribution: '自建' },
      { name: '莲花桥基站', distance: 260, operator: '移动', band: '2100MHz', rsrp: -88, attribution: '共享' },
      { name: '公主坟基站', distance: 380, operator: '电信', band: '800MHz', rsrp: -94, attribution: '共享' }
    ],
    workOrders: []
  },
  { 
    id: 12, 
    name: '国家大剧院', 
    lng: 116.407428, 
    lat: 39.90923, 
    type: '场馆', 
    area: '西城区', 
    coverage: 90,
    rsrp: -101,
    sinr: 17,
    uploadSpeed: 52,
    downloadSpeed: 250,
    latency: 33,
    improvement: 1.0,
    responsibleGrid: '西城网格A区',
    maintenanceUnit: '北京电信运维部',
    lastTestTime: '2024-01-11 14:00',
    trendData: { coverage: [89, 90, 90], rsrp: [-102, -101, -101], sinr: [16, 17, 17], downlink: [240, 245, 250] },
    nearbyStations: [
      { name: '天安门基站', distance: 200, operator: '电信', band: '800MHz', rsrp: -95, attribution: '自建' },
      { name: '西单基站', distance: 340, operator: '联通', band: '1800MHz', rsrp: -103, attribution: '共享' },
      { name: '王府井基站', distance: 450, operator: '移动', band: '2100MHz', rsrp: -106, attribution: '共享' }
    ],
    workOrders: []
  },
  { 
    id: 13, 
    name: '中国人民大学', 
    lng: 116.307428, 
    lat: 39.91423, 
    type: '学校', 
    area: '海淀区', 
    coverage: 85,
    rsrp: -108,
    sinr: 13,
    uploadSpeed: 40,
    downloadSpeed: 200,
    latency: 42,
    improvement: -1.2,
    responsibleGrid: '海淀网格C区',
    maintenanceUnit: '北京移动运维部',
    lastTestTime: '2024-01-10 11:15',
    trendData: { coverage: [87, 86, 85], rsrp: [-105, -107, -108], sinr: [15, 14, 13], downlink: [220, 210, 200] },
    nearbyStations: [
      { name: '人大基站', distance: 250, operator: '移动', band: '2600MHz', rsrp: -100, attribution: '自建' },
      { name: '中关村基站', distance: 380, operator: '联通', band: '1800MHz', rsrp: -110, attribution: '共享' },
      { name: '魏公村基站', distance: 460, operator: '电信', band: '800MHz', rsrp: -112, attribution: '共享' }
    ],
    workOrders: []
  },
  { 
    id: 14, 
    name: '北京朝阳医院', 
    lng: 116.437428, 
    lat: 39.92923, 
    type: '医院', 
    area: '朝阳区', 
    coverage: 87,
    rsrp: -104,
    sinr: 14,
    uploadSpeed: 48,
    downloadSpeed: 210,
    latency: 36,
    improvement: -0.8,
    responsibleGrid: '朝阳网格A区',
    maintenanceUnit: '北京联通运维部',
    lastTestTime: '2024-01-09 16:30',
    trendData: { coverage: [88, 88, 87], rsrp: [-102, -103, -104], sinr: [16, 15, 14], downlink: [225, 218, 210] },
    nearbyStations: [
      { name: '朝阳医院基站', distance: 180, operator: '联通', band: '1800MHz', rsrp: -98, attribution: '自建' },
      { name: '三里屯基站', distance: 320, operator: '移动', band: '2100MHz', rsrp: -106, attribution: '共享' },
      { name: '呼家楼基站', distance: 440, operator: '电信', band: '2600MHz', rsrp: -108, attribution: '共享' }
    ],
    workOrders: []
  },
  { 
    id: 15, 
    name: '北京南苑机场', 
    lng: 116.417428, 
    lat: 39.77923, 
    type: '交通枢纽', 
    area: '丰台区', 
    coverage: 82,
    rsrp: -112,
    sinr: 11,
    uploadSpeed: 35,
    downloadSpeed: 180,
    latency: 45,
    improvement: -2.5,
    responsibleGrid: '丰台网格C区',
    maintenanceUnit: '北京电信运维部',
    lastTestTime: '2024-01-08 10:00',
    trendData: { coverage: [85, 83, 82], rsrp: [-108, -110, -112], sinr: [14, 12, 11], downlink: [200, 190, 180] },
    nearbyStations: [
      { name: '南苑基站', distance: 300, operator: '电信', band: '800MHz', rsrp: -105, attribution: '自建' },
      { name: '大红门基站', distance: 450, operator: '联通', band: '1800MHz', rsrp: -115, attribution: '共享' },
      { name: '角门基站', distance: 480, operator: '移动', band: '2100MHz', rsrp: -118, attribution: '共享' }
    ],
    workOrders: [
      { orderNo: 'WO-20240108-001', createTime: '2024-01-08 09:00', type: '覆盖优化', status: '进行中', result: '规划新增基站' }
    ]
  }
]

// 类型选项
const typeOptions = [
  { label: '全部类型', value: '' },
  { label: '医院', value: '医院' },
  { label: '交通枢纽', value: '交通枢纽' },
  { label: '场馆', value: '场馆' },
  { label: '学校', value: '学校' }
]

// 行政区选项
const areaOptions = [
  { label: '全部区域', value: '' },
  { label: '东城区', value: '东城区' },
  { label: '西城区', value: '西城区' },
  { label: '朝阳区', value: '朝阳区' },
  { label: '海淀区', value: '海淀区' },
  { label: '丰台区', value: '丰台区' },
  { label: '顺义区', value: '顺义区' }
]

// 地图相关
const mapContainer = ref(null)
let map = null
let markers = []
let satelliteLayer = null
let roadLayer = null
let currentLayerIndex = 0
const baseLayers = ['amap://styles/normal', 'amap://styles/satellite', 'amap://styles/whitesmoke', 'amap://styles/darkblue']

// 状态
const searchText = ref('')
const filters = reactive({
  type: '',
  area: ''
})
const selectedLocation = ref(null)
const currentLayerName = ref('标准地图')

// 计算属性：过滤后的场所列表
const filteredLocations = computed(() => {
  let result = mockLocations
  
  if (searchText.value) {
    result = result.filter(loc => 
      loc.name.toLowerCase().includes(searchText.value.toLowerCase())
    )
  }
  
  if (filters.type) {
    result = result.filter(loc => loc.type === filters.type)
  }
  
  if (filters.area) {
    result = result.filter(loc => loc.area === filters.area)
  }
  
  return result
})

// 已覆盖数量（覆盖率 >= 90%）
const coveredCount = computed(() => {
  return filteredLocations.value.filter(loc => loc.coverage >= 90).length
})

// 获取类型标签颜色
const getTypeTagType = (type) => {
  const typeMap = {
    '医院': 'danger',
    '交通枢纽': 'warning',
    '场馆': 'success',
    '学校': 'primary'
  }
  return typeMap[type] || 'info'
}

// 获取覆盖率样式
const getCoverageClass = (coverage) => {
  if (coverage >= 90) return 'good'
  if (coverage >= 80) return 'medium'
  return 'poor'
}

// 地图初始化函数（必须在全局作用域定义）
const initAMAPCallback = () => {
  if (!mapContainer.value) return
  
  map = new AMap.Map(mapContainer.value, {
    zoom: 12,
    center: [116.397428, 39.90923],
    viewMode: '3D',
    pitch: 45,
    rotation: 0,
    mapStyle: baseLayers[currentLayerIndex]
  })
  
  // 添加控件
  map.addControl(new AMap.ToolBar())
  map.addControl(new AMap.Scale())
  map.addControl(new AMap.ControlBar({
    showZoomBar: true,
    showControlButton: true
  }))
  
  // 渲染标记
  renderMarkers()
  
  // 渲染自定义标记
  renderCustomMarkers()
  
  // 地图点击事件
  map.on('click', (e) => {
    if (addMarkerMode.value) {
      createCustomMarker(e.lnglat.lng, e.lnglat.lat)
    } else {
      selectedLocation.value = null
    }
  })
}

// 初始化地图
const initMap = () => {
  if (!mapContainer.value) return
  
  // 在脚本加载前先定义全局回调函数
  window.initAMAP = initAMAPCallback
  
  // 检查高德地图是否已加载
  if (window.AMap) {
    initAMAPCallback()
    return
  }
  
  // 加载高德地图API
  const script = document.createElement('script')
  script.src = `https://webapi.amap.com/maps?v=2.0&key=${AMAP_KEY}&callback=initAMAP`
  script.async = true
  script.defer = true
  document.head.appendChild(script)
}

// 渲染场所标记
const renderMarkers = () => {
  if (!map) return
  
  // 清除旧标记
  markers.forEach(marker => marker.setMap(null))
  markers = []
  
  // 添加新标记
  filteredLocations.value.forEach(location => {
    const marker = new AMap.Marker({
      position: [location.lng, location.lat],
      icon: new AMap.Icon({
        size: new AMap.Size(32, 32),
        image: `https://webapi.amap.com/theme/v1.3/markers/b/${getCoverageClass(location.coverage) === 'good' ? 'green' : getCoverageClass(location.coverage) === 'medium' ? 'orange' : 'red' }/star.png`,
        imageSize: new AMap.Size(32, 32)
      }),
      cursor: 'pointer',
      clickable: true,
      zIndex: 10
    })
    
    marker.on('click', (e) => {
      e.stopPropagation()
      selectedLocation.value = location
      showInfoWindow(location)
    })
    
    marker.setMap(map)
    markers.push(marker)
  })
}

// 渲染自定义红色标记
const renderCustomMarkers = () => {
  if (!map) return
  
  // 清除旧标记
  customMarkerObjects.value.forEach(marker => marker.setMap(null))
  customMarkerObjects.value = []
  
  // 添加自定义标记
  customMarkers.value.forEach(markerData => {
    const marker = new AMap.Marker({
      position: [markerData.lng, markerData.lat],
      icon: new AMap.Icon({
        size: new AMap.Size(40, 40),
        image: 'https://webapi.amap.com/theme/v1.3/markers/b/red/marker.png',
        imageSize: new AMap.Size(40, 40)
      }),
      cursor: 'pointer',
      clickable: true,
      zIndex: 20,
      draggable: true
    })
    
    marker.on('click', (e) => {
      e.stopPropagation()
      showCustomMarkerInfo(markerData)
    })
    
    marker.on('dragend', (e) => {
      const lnglat = e.lnglat
      const markerIndex = customMarkers.value.findIndex(m => m.id === markerData.id)
      if (markerIndex > -1) {
        customMarkers.value[markerIndex].lng = lnglat.lng
        customMarkers.value[markerIndex].lat = lnglat.lat
      }
    })
    
    marker.setMap(map)
    customMarkerObjects.value.push(marker)
  })
}

// 创建自定义标记
const createCustomMarker = (lng, lat) => {
  const newMarker = {
    id: Date.now(),
    name: `标记点${customMarkers.value.length + 1}`,
    lng: lng,
    lat: lat,
    description: ''
  }
  customMarkers.value.push(newMarker)
  renderCustomMarkers()
  showMarkerDialog.value = false
  ElMessage.success('标记点创建成功')
}

// 显示场所信息窗口
const showInfoWindow = (location) => {
  if (!map) return
  
  const infoWindow = new AMap.InfoWindow({
    content: `
      <div class="info-window">
        <h3>${location.name}</h3>
        <p><strong>类型：</strong>${location.type}</p>
        <p><strong>区域：</strong>${location.area}</p>
        <p><strong>覆盖评估：</strong><span class="${getCoverageClass(location.coverage)}">${location.coverage}%</span></p>
        <p><strong>RSRP：</strong>${location.rsrp || '-'} dBm</p>
        <p><strong>SINR：</strong>${location.sinr || '-'} dB</p>
        <button class="report-btn" onclick="window.showDetailReport(${location.id})">查看详细报告</button>
      </div>
    `,
    offset: new AMap.Pixel(0, -30)
  })
  
  infoWindow.open(map, [location.lng, location.lat])
}

// 显示自定义标记信息窗口
const showCustomMarkerInfo = (markerData) => {
  if (!map) return
  
  const infoWindow = new AMap.InfoWindow({
    content: `
      <div class="info-window custom-marker-window">
        <h3>📍 ${markerData.name}</h3>
        ${markerData.description ? `<p>${markerData.description}</p>` : ''}
        <p><strong>经度：</strong>${markerData.lng.toFixed(6)}</p>
        <p><strong>纬度：</strong>${markerData.lat.toFixed(6)}</p>
        <div class="info-window-actions">
          <button class="info-btn edit-btn" onclick="window.editMarker(${markerData.id})">编辑</button>
          <button class="info-btn delete-btn" onclick="window.deleteMarker(${markerData.id})">删除</button>
        </div>
      </div>
    `,
    offset: new AMap.Pixel(0, -35)
  })
  
  infoWindow.open(map, [markerData.lng, markerData.lat])
}

// 显示详细报告
const showDetailReport = (locationId) => {
  const location = mockLocations.find(l => l.id === locationId)
  if (location) {
    reportPlace.value = location
    showReport.value = true
  }
}

// 暴露给全局，供信息窗口按钮调用
window.showDetailReport = showDetailReport
window.editMarker = editCustomMarker
window.deleteMarker = deleteCustomMarker

// 编辑自定义标记
const editCustomMarker = (marker) => {
  markerForm.id = marker.id
  markerForm.name = marker.name
  markerForm.lng = marker.lng
  markerForm.lat = marker.lat
  markerForm.description = marker.description || ''
  showMarkerDialog.value = true
}

// 删除自定义标记
const deleteCustomMarker = (marker) => {
  const index = customMarkers.value.findIndex(m => m.id === marker.id)
  if (index > -1) {
    customMarkers.value.splice(index, 1)
    renderCustomMarkers()
    ElMessage.success('标记点删除成功')
  }
}

// 保存标记
const saveMarker = () => {
  if (!markerForm.name) {
    ElMessage.warning('请输入标记名称')
    return
  }
  
  const existingIndex = customMarkers.value.findIndex(m => m.id === markerForm.id)
  
  if (existingIndex >= 0) {
    customMarkers.value[existingIndex] = { ...markerForm }
  } else {
    customMarkers.value.push({ ...markerForm, id: Date.now() })
  }
  
  renderCustomMarkers()
  showMarkerDialog.value = false
  ElMessage.success('标记点保存成功')
}

// 清除所有自定义标记
const clearAllCustomMarkers = () => {
  customMarkers.value = []
  renderCustomMarkers()
  ElMessage.success('已清除所有自定义标记')
}

// 聚焦到自定义标记
const focusOnCustomMarker = (marker) => {
  if (!map) return
  map.setZoomAndCenter(15, [marker.lng, marker.lat])
  showCustomMarkerInfo(marker)
}

// 搜索处理
const handleSearch = () => {
  renderMarkers()
}

// 筛选变化处理
const handleFilterChange = () => {
  renderMarkers()
}

// 切换底图
const switchBaseLayer = () => {
  if (!map) return
  currentLayerIndex = (currentLayerIndex + 1) % baseLayers.length
  
  const layerNames = ['标准地图', '卫星影像', '浅色地图', '深色地图']
  currentLayerName.value = layerNames[currentLayerIndex]
  
  // 如果是卫星图，需要添加卫星图层
  if (baseLayers[currentLayerIndex] === 'amap://styles/satellite') {
    // 隐藏默认图层
    map.setMapStyle('amap://styles/blank')
    
    // 创建卫星图层
    if (!satelliteLayer) {
      satelliteLayer = new AMap.TileLayer.Satellite()
    }
    satelliteLayer.setMap(map)
    
    // 添加路网图层
    if (!roadLayer) {
      roadLayer = new AMap.TileLayer.RoadNet()
    }
    roadLayer.setMap(map)
  } else {
    // 移除卫星图层和路网图层
    if (satelliteLayer) {
      satelliteLayer.setMap(null)
    }
    if (roadLayer) {
      roadLayer.setMap(null)
    }
    // 设置普通底图样式
    map.setMapStyle(baseLayers[currentLayerIndex])
  }
}

// 放大
const zoomIn = () => {
  if (!map) return
  map.zoomIn()
}

// 缩小
const zoomOut = () => {
  if (!map) return
  map.zoomOut()
}

// 重置视图
const resetView = () => {
  if (!map) return
  map.setZoomAndCenter(12, [116.397428, 39.90923])
}

// 聚焦到某个场所
const focusOnLocation = (location) => {
  if (!map) return
  selectedLocation.value = location
  map.setZoomAndCenter(15, [location.lng, location.lat])
  showInfoWindow(location)
}

// 切换添加标记模式
const toggleAddMarkerMode = () => {
  addMarkerMode.value = !addMarkerMode.value
}

// 生命周期
onMounted(() => {
  initMap()
})

onUnmounted(() => {
  if (map) {
    map.destroy()
  }
})
</script>

<style scoped>
.coverage-assessment {
  width: 100%;
  height: 100%;
  position: relative;
  display: flex;
  flex-direction: column;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  background: rgba(10, 22, 40, 0.95);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  z-index: 100;
}

.toolbar-left h2 {
  margin: 0;
  color: #fff;
  font-size: 18px;
  font-weight: 600;
}

.toolbar-right {
  display: flex;
  gap: 10px;
}

.toolbar-right .el-button.active {
  background: #f56c6c;
  border-color: #f56c6c;
}

.map-container {
  flex: 1;
  width: 100%;
}

.add-mode-hint {
  position: absolute;
  top: 70px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1000;
}

.control-panel {
  position: absolute;
  top: 70px;
  right: 20px;
  width: 320px;
  z-index: 1000;
}

.panel-card {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
  background: rgba(255, 255, 255, 0.95);
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.search-section {
  margin-bottom: 16px;
}

.filter-section {
  margin-bottom: 16px;
}

.button-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.button-group .el-button {
  flex: 1;
  min-width: 70px;
}

.statistics {
  display: flex;
  align-items: center;
  justify-content: space-around;
  padding: 12px 0;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 16px;
}

.statistics .el-divider {
  height: 40px;
}

.location-list {
  border-top: 1px solid #ebeef5;
  padding-top: 12px;
}

.custom-marker-list {
  border-top: 1px solid #ebeef5;
  padding-top: 12px;
  margin-top: 12px;
}

.list-title {
  font-size: 14px;
  font-weight: 600;
  color: #606266;
  margin-bottom: 12px;
}

.location-item {
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s;
  margin-bottom: 8px;
}

.location-item:hover {
  background: #ecf5ff;
}

.location-item.active {
  background: #409eff;
  color: #fff;
}

.location-item.active .location-info .el-tag {
  background: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.3);
}

.location-item.active .coverage {
  color: #fff !important;
}

.location-name {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 4px;
}

.location-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.marker-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s;
  margin-bottom: 6px;
  background: rgba(245, 108, 108, 0.1);
}

.marker-item:hover {
  background: rgba(245, 108, 108, 0.2);
}

.marker-name {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
}

.marker-actions {
  display: flex;
  gap: 4px;
}

.coverage {
  font-size: 14px;
  font-weight: 600;
}

.coverage.good {
  color: #67c23a;
}

.coverage.medium {
  color: #e6a23c;
}

.coverage.poor {
  color: #f56c6c;
}

:deep(.info-window) {
  padding: 12px;
  min-width: 240px;
  background: rgba(255, 255, 255, 0.98);
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

:deep(.info-window h3) {
  margin: 0 0 10px 0;
  color: #303133;
  font-size: 16px;
}

:deep(.info-window p) {
  margin: 5px 0;
  color: #606266;
  font-size: 14px;
}

:deep(.info-window .report-btn) {
  display: block;
  width: 100%;
  margin-top: 12px;
  padding: 8px 12px;
  background: #409eff;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  text-align: center;
  transition: background 0.3s;
}

:deep(.info-window .report-btn:hover) {
  background: #66b1ff;
}

:deep(.info-window .info-window-actions) {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

:deep(.info-window .info-btn) {
  flex: 1;
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  text-align: center;
  transition: all 0.3s;
}

:deep(.info-window .edit-btn) {
  background: #409eff;
  color: #fff;
}

:deep(.info-window .edit-btn:hover) {
  background: #66b1ff;
}

:deep(.info-window .delete-btn) {
  background: #f56c6c;
  color: #fff;
}

:deep(.info-window .delete-btn:hover) {
  background: #f78989;
}

:deep(.info-window .good) {
  color: #67c23a;
  font-weight: 600;
}

:deep(.info-window .medium) {
  color: #e6a23c;
  font-weight: 600;
}

:deep(.info-window .poor) {
  color: #f56c6c;
  font-weight: 600;
}

:deep(.info-window.custom-marker-window) {
  min-width: 200px;
}
</style>