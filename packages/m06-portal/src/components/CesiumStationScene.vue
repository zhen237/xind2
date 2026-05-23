<template>
  <div class="cesium-station-scene">
    <!-- 顶部工具栏 -->
    <el-card class="toolbar-card">
      <div class="toolbar">
        <div class="left-tools">
          <el-button 
            :type="addMode ? 'primary' : 'default'" 
            @click="toggleAddMode"
            icon="Plus"
          >
            {{ addMode ? '退出添加' : '添加天线' }}
          </el-button>
          <el-button @click="zoomIn" icon="ZoomIn">放大</el-button>
          <el-button @click="zoomOut" icon="ZoomOut">缩小</el-button>
          <el-button @click="resetView" icon="Refresh">复位</el-button>
          <el-button @click="flyToStation" icon="MapPin">飞向基站</el-button>
        </div>
        <div class="center-info" v-if="addMode">
          <el-tag type="warning">添加模式：点击场景中的位置放置天线</el-tag>
        </div>
        <div class="center-info" v-else>
          <el-tag type="success">当前基站：{{ stationName }}</el-tag>
        </div>
      </div>
    </el-card>

    <div class="main-content">
      <!-- Cesium场景容器 -->
      <div class="cesium-container" ref="cesiumContainer"></div>

      <!-- 侧边栏 -->
      <div class="side-panel">
        <!-- 天线列表 -->
        <el-card title="天线设备列表" class="antenna-list-card">
          <div class="search-bar">
            <el-input 
              v-model="searchKeyword" 
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
              <div class="antenna-info">
                <span class="antenna-name">{{ antenna.name }}</span>
                <span class="antenna-coord">
                  {{ antenna.lng.toFixed(6) }}, {{ antenna.lat.toFixed(6) }}, {{ antenna.height }}m
                </span>
              </div>
              <div class="antenna-actions">
                <el-button size="small" @click="locateAntenna(antenna)" icon="MapPin">定位</el-button>
                <el-button size="small" type="danger" @click="deleteAntenna(antenna)" icon="Delete">删除</el-button>
              </div>
            </div>
            <div v-if="filteredAntennas.length === 0" class="empty-state">
              暂无天线设备
            </div>
          </div>
        </el-card>

        <!-- 添加天线表单 -->
        <el-card title="手动添加天线" class="add-form-card">
          <el-form :model="newAntennaForm" label-width="70px">
            <el-form-item label="天线名称">
              <el-input v-model="newAntennaForm.name" placeholder="请输入天线名称" />
            </el-form-item>
            <el-form-item label="经度">
              <el-input v-model.number="newAntennaForm.lng" placeholder="经度" />
            </el-form-item>
            <el-form-item label="纬度">
              <el-input v-model.number="newAntennaForm.lat" placeholder="纬度" />
            </el-form-item>
            <el-form-item label="高度(m)">
              <el-input v-model.number="newAntennaForm.height" placeholder="高度" />
            </el-form-item>
            <el-form-item label="天线类型">
              <el-select v-model="newAntennaForm.type">
                <el-option label="全向天线" value="omni" />
                <el-option label="定向天线" value="directional" />
                <el-option label="智能天线" value="smart" />
              </el-select>
            </el-form-item>
            <div class="form-actions">
              <el-button @click="resetForm">重置</el-button>
              <el-button type="primary" @click="addAntennaManually" icon="Plus">添加</el-button>
            </div>
          </el-form>
        </el-card>

        <!-- 操作说明 -->
        <el-card title="操作说明">
          <div class="tips">
            <ul>
              <li><strong>鼠标左键拖拽</strong>：旋转视角</li>
              <li><strong>鼠标滚轮</strong>：缩放场景</li>
              <li><strong>鼠标右键拖拽</strong>：平移场景</li>
              <li><strong>点击"添加天线"</strong>：进入添加模式</li>
              <li><strong>右键点击天线</strong>：删除天线</li>
            </ul>
          </div>
        </el-card>
      </div>
    </div>

    <!-- 设备名称输入弹窗 -->
    <el-dialog 
      title="输入天线名称" 
      :visible.sync="showNameDialog" 
      width="400px"
      :close-on-click-modal="false"
    >
      <el-form :model="tempAntenna" label-width="80px">
        <el-form-item label="天线名称">
          <el-input v-model="tempAntenna.name" placeholder="请输入天线名称" />
        </el-form-item>
        <el-form-item label="天线类型">
          <el-select v-model="tempAntenna.type">
            <el-option label="全向天线" value="omni" />
            <el-option label="定向天线" value="directional" />
            <el-option label="智能天线" value="smart" />
          </el-select>
        </el-form-item>
        <el-form-item label="高度(m)">
          <el-input v-model.number="tempAntenna.height" placeholder="高度" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="cancelAdd">取消</el-button>
        <el-button type="primary" @click="confirmAdd">确认添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';

// 组件引用
const cesiumContainer = ref(null);
const searchKeyword = ref('');
const addMode = ref(false);
const showNameDialog = ref(false);
const cesiumViewer = ref(null);

// 基站信息
const stationName = ref('北京测试基站');
const stationPosition = reactive({
  lng: 116.397428,
  lat: 39.90923,
  height: 100 // 基站塔高度
});

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

// 临时天线数据（用于点击添加）
const tempAntenna = reactive({
  name: '',
  lng: 0,
  lat: 0,
  height: 90,
  type: 'omni'
});

// 过滤后的天线列表
const filteredAntennas = computed(() => {
  if (!searchKeyword.value) return antennas.value;
  return antennas.value.filter(ant => 
    ant.name.toLowerCase().includes(searchKeyword.value.toLowerCase())
  );
});

// 获取天线类型颜色
const getAntennaColor = (type) => {
  const colors = {
    'omni': '#3b82f6',        // 蓝色 - 全向天线
    'directional': '#22c55e',  // 绿色 - 定向天线
    'smart': '#a855f7'        // 紫色 - 智能天线
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
  if (!cesiumContainer.value) return;

  try {
    // 创建Cesium视图
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

    // 设置背景颜色
    cesiumViewer.value.scene.backgroundColor = Cesium.Color.fromCssColorString('#0a1628');

    // 设置相机位置
    const cameraPosition = Cesium.Cartesian3.fromDegrees(
      stationPosition.lng, 
      stationPosition.lat, 
      250
    );
    
    cesiumViewer.value.camera.setView({
      destination: cameraPosition,
      orientation: {
        heading: 0,
        pitch: Cesium.Math.toRadians(-45),
        roll: 0
      }
    });

    // 添加基站塔
    addStationTower();

    // 添加通信厂区3D模型
    addCommunicationSiteModel();

    // 添加地面网格
    addGroundGrid();

    // 添加预设天线
    antennas.value.forEach(antenna => {
      addAntennaEntity(antenna);
    });

    // 添加点击事件
    cesiumViewer.value.scene.screenSpaceEventHandler.setInputAction(
      (event) => {
        handleSceneClick(event);
      },
      Cesium.ScreenSpaceEventType.LEFT_CLICK
    );

    // 添加右键点击事件（用于删除）
    cesiumViewer.value.scene.screenSpaceEventHandler.setInputAction(
      (event) => {
        handleRightClick(event);
      },
      Cesium.ScreenSpaceEventType.RIGHT_CLICK
    );

    console.log('Cesium场景初始化完成');
  } catch (error) {
    console.error('Cesium初始化失败:', error);
    ElMessage.error('Cesium加载失败，请检查浏览器控制台');
  }
};

// 添加基站塔（使用圆柱体+球体组合）
const addStationTower = () => {
  if (!cesiumViewer.value) return;

  const center = Cesium.Cartesian3.fromDegrees(
    stationPosition.lng,
    stationPosition.lat,
    0
  );

  // 创建塔基平台
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

  // 创建塔身（圆柱体）
  const towerHeight = stationPosition.height;
  const towerEntity = cesiumViewer.value.entities.add({
    position: Cesium.Cartesian3.fromDegrees(
      stationPosition.lng,
      stationPosition.lat,
      towerHeight / 2
    ),
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

  // 创建塔顶平台
  const topPlatformEntity = cesiumViewer.value.entities.add({
    position: Cesium.Cartesian3.fromDegrees(
      stationPosition.lng,
      stationPosition.lat,
      towerHeight + 1
    ),
    box: {
      dimensions: new Cesium.Cartesian3(10, 10, 2),
      material: Cesium.Color.fromCssColorString('#2d3748'),
      outline: true,
      outlineColor: Cesium.Color.WHITE,
      outlineWidth: 2
    }
  });

  // 添加基站标签
  const labelEntity = cesiumViewer.value.entities.add({
    position: Cesium.Cartesian3.fromDegrees(
      stationPosition.lng,
      stationPosition.lat,
      towerHeight + 15
    ),
    label: {
      text: stationName.value,
      font: '18px sans-serif',
      fillColor: Cesium.Color.WHITE,
      outlineColor: Cesium.Color.BLACK,
      outlineWidth: 3,
      style: Cesium.LabelStyle.FILL_AND_OUTLINE,
      verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
      disableDepthTestDistance: Number.POSITIVE_INFINITY
    }
  });
};

// 添加通信厂区3D模型
const addCommunicationSiteModel = () => {
  if (!cesiumViewer.value) return;

  // 使用用户导出的Blender模型
  const modelUrl = '/models/communication_site.glb';

  // 模型位置（与基站位置偏移，确保模型在视野内）
  const modelPosition = Cesium.Cartesian3.fromDegrees(
    stationPosition.lng - 0.002,
    stationPosition.lat - 0.001,
    0
  );

  // 创建模型实体
  const modelEntity = cesiumViewer.value.entities.add({
    position: modelPosition,
    model: {
      uri: modelUrl,
      scale: 1, // 模型缩放比例
      minimumPixelSize: 50, // 最小像素大小
      maximumScale: 200, // 最大缩放比例
      heightReference: Cesium.HeightReference.CLAMP_TO_GROUND, // 贴合地面
      runAnimations: false // 是否运行动画
    }
  });

  console.log('正在加载通信厂区模型:', modelUrl);

  // 监听模型加载完成事件
  if (cesiumViewer.value.scene && cesiumViewer.value.scene.primitives) {
    const loadPromise = cesiumViewer.value.scene.primitives.modelReadyPromise(modelEntity.model);

    if (loadPromise) {
      loadPromise.then(() => {
        console.log('通信厂区模型加载完成');
        ElMessage.success('通信厂区3D模型加载成功');
      }).catch((error) => {
        console.error('模型加载失败:', error);
        ElMessage.error('3D模型加载失败，请检查模型文件');
      });
    }
  }

  // 备用：使用onTick监听加载状态
  let checkCount = 0;
  const checkInterval = setInterval(() => {
    if (modelEntity.model && modelEntity.model.ready) {
      clearInterval(checkInterval);
      console.log('通信厂区模型加载完成（轮询检测）');
    } else if (checkCount > 100) {
      clearInterval(checkInterval);
      console.warn('模型加载超时');
    }
    checkCount++;
  }, 100);
};

// 添加地面网格
const addGroundGrid = () => {
  if (!cesiumViewer.value) return;

  const gridSize = 150;
  const step = 30;
  const lng = stationPosition.lng;
  const lat = stationPosition.lat;

  for (let i = -gridSize; i <= gridSize; i += step) {
    // 水平网格线
    const hStart = Cesium.Cartesian3.fromDegrees(
      lng - gridSize * 0.00005,
      lat + i * 0.00005,
      0.5
    );
    const hEnd = Cesium.Cartesian3.fromDegrees(
      lng + gridSize * 0.00005,
      lat + i * 0.00005,
      0.5
    );
    const hColor = i === 0 ? Cesium.Color.YELLOW.withAlpha(0.8) : Cesium.Color.WHITE.withAlpha(0.2);

    cesiumViewer.value.entities.add({
      polyline: {
        positions: [hStart, hEnd],
        width: 2,
        material: hColor
      }
    });

    // 垂直网格线
    const vStart = Cesium.Cartesian3.fromDegrees(
      lng + i * 0.00005,
      lat - gridSize * 0.00005,
      0.5
    );
    const vEnd = Cesium.Cartesian3.fromDegrees(
      lng + i * 0.00005,
      lat + gridSize * 0.00005,
      0.5
    );
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
  if (!cesiumViewer.value) return;

  const position = Cesium.Cartesian3.fromDegrees(
    antenna.lng,
    antenna.lat,
    antenna.height
  );

  // 创建天线模型（使用球体+圆柱体组合）
  const entity = cesiumViewer.value.entities.add({
    id: `antenna_${antenna.id}`,
    antennaId: antenna.id,
    position: position,
    // 天线底座
    cylinder: {
      length: 3,
      topRadius: 0.5,
      bottomRadius: 0.8,
      material: Cesium.Color.fromCssColorString('#64748b'),
      outline: true,
      outlineColor: Cesium.Color.WHITE,
      outlineWidth: 1
    },
    // 天线主体（立方体）
    box: {
      dimensions: new Cesium.Cartesian3(2, 2, 4),
      material: Cesium.Color.fromCssColorString(antenna.color || getAntennaColor(antenna.type)),
      outline: true,
      outlineColor: Cesium.Color.WHITE,
      outlineWidth: 1
    },
    // 天线标签
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
      show: false // 默认隐藏，悬停时显示
    }
  });

  console.log(`天线 ${antenna.name} 已添加到场景`);
};

// 更新天线实体位置
const updateAntennaEntity = (antenna) => {
  if (!cesiumViewer.value) return;

  const entities = cesiumViewer.value.entities.values;
  for (let i = 0; i < entities.length; i++) {
    const entity = entities[i];
    if (entity.antennaId === antenna.id) {
      const newPosition = Cesium.Cartesian3.fromDegrees(
        antenna.lng,
        antenna.lat,
        antenna.height
      );
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
  if (!cesiumViewer.value) return;

  const entities = cesiumViewer.value.entities.values;
  for (let i = entities.length - 1; i >= 0; i--) {
    const entity = entities[i];
    if (entity.antennaId === antennaId) {
      cesiumViewer.value.entities.remove(entity);
      console.log(`天线ID ${antennaId} 已从场景移除`);
      break;
    }
  }
};

// 处理场景点击
const handleSceneClick = (event) => {
  if (!addMode.value) return;

  const ray = cesiumViewer.value.camera.getPickRay(event.position);
  if (!ray) return;

  // 计算与地面的交点
  const globe = cesiumViewer.value.scene.globe;
  const intersection = globe.pick(ray, cesiumViewer.value.scene);

  if (intersection) {
    const cartographic = Cesium.Cartographic.fromCartesian(intersection);
    const lng = Cesium.Math.toDegrees(cartographic.longitude);
    const lat = Cesium.Math.toDegrees(cartographic.latitude);

    // 设置临时天线位置
    tempAntenna.lng = lng;
    tempAntenna.lat = lat;
    tempAntenna.height = 90;
    tempAntenna.name = '';

    // 显示名称输入对话框
    showNameDialog.value = true;
  }
};

// 处理右键点击（删除天线）
const handleRightClick = (event) => {
  const pickedObject = cesiumViewer.value.scene.pick(event.position);
  
  if (pickedObject && pickedObject.id && pickedObject.id.antennaId) {
    const antennaId = pickedObject.id.antennaId;
    const antenna = antennas.value.find(a => a.id === antennaId);
    
    if (antenna) {
      ElMessageBox.confirm(`确定删除天线 "${antenna.name}" 吗？`, '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        deleteAntenna(antenna);
      }).catch(() => {
        ElMessage.info('已取消删除');
      });
    }
  }
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

// 手动添加天线
const addAntennaManually = () => {
  if (!newAntennaForm.name.trim()) {
    ElMessage.warning('请输入天线名称');
    return;
  }
  if (!newAntennaForm.lng || !newAntennaForm.lat) {
    ElMessage.warning('请输入经纬度');
    return;
  }

  const newAntenna = {
    id: Date.now(),
    name: newAntennaForm.name,
    lng: newAntennaForm.lng,
    lat: newAntennaForm.lat,
    height: newAntennaForm.height || 90,
    type: newAntennaForm.type,
    color: getAntennaColor(newAntennaForm.type)
  };

  antennas.value.push(newAntenna);
  addAntennaEntity(newAntenna);
  
  resetForm();
  ElMessage.success('天线添加成功');
};

// 重置表单
const resetForm = () => {
  newAntennaForm.name = '';
  newAntennaForm.lng = stationPosition.lng;
  newAntennaForm.lat = stationPosition.lat;
  newAntennaForm.height = 90;
  newAntennaForm.type = 'omni';
};

// 定位天线
const locateAntenna = (antenna) => {
  if (!cesiumViewer.value) return;

  const position = Cesium.Cartesian3.fromDegrees(
    antenna.lng,
    antenna.lat,
    antenna.height + 30
  );

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
  // 从数组中删除
  const index = antennas.value.findIndex(a => a.id === antenna.id);
  if (index > -1) {
    antennas.value.splice(index, 1);
  }

  // 从场景中删除
  removeAntennaEntity(antenna.id);

  ElMessage.success('删除成功');
};

// 放大
const zoomIn = () => {
  if (cesiumViewer.value) {
    cesiumViewer.value.camera.zoomIn(1.2);
  }
};

// 缩小
const zoomOut = () => {
  if (cesiumViewer.value) {
    cesiumViewer.value.camera.zoomOut(1.2);
  }
};

// 复位视图
const resetView = () => {
  if (!cesiumViewer.value) return;

  const cameraPosition = Cesium.Cartesian3.fromDegrees(
    stationPosition.lng,
    stationPosition.lat,
    250
  );

  cesiumViewer.value.camera.setView({
    destination: cameraPosition,
    orientation: {
      heading: 0,
      pitch: Cesium.Math.toRadians(-45),
      roll: 0
    }
  });
};

// 飞向基站
const flyToStation = () => {
  resetView();
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
  background: #0a1628;
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

.left-tools {
  display: flex;
  gap: 10px;
}

.center-info {
  flex: 1;
  text-align: center;
}

.main-content {
  flex: 1;
  display: flex;
  margin: 0 10px 10px;
  gap: 10px;
  min-height: 0;
}

.cesium-container {
  flex: 1;
  border-radius: 8px;
  overflow: hidden;
}

.side-panel {
  width: 360px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow-y: auto;
  z-index: 100;
}

.antenna-list-card, .add-form-card {
  flex-shrink: 0;
}

.search-bar {
  margin-bottom: 12px;
}

.antenna-list {
  max-height: 350px;
  overflow-y: auto;
}

.antenna-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  border-bottom: 1px solid #f0f0f0;
  transition: background 0.2s;
}

.antenna-item:hover {
  background: #f8fafc;
}

.antenna-item:last-child {
  border-bottom: none;
}

.antenna-info {
  flex: 1;
  min-width: 0;
}

.antenna-name {
  display: block;
  font-weight: 500;
  font-size: 14px;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.antenna-coord {
  display: block;
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.antenna-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

.empty-state {
  text-align: center;
  padding: 30px;
  color: #909399;
  font-size: 14px;
}

.form-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 15px;
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
  margin: 8px 0;
}
</style>