<template>
  <div class="design-visualization">
    <!-- 顶部工具栏 -->
    <div class="top-bar">
      <div class="toolbar-left">
        <el-button
          type="success"
          size="default"
          :loading="creatingProject"
          @click="openCreateProjectDialog"
          style="font-weight: 600;"
        >
          <el-icon><FolderAdd /></el-icon> 创建项目
        </el-button>
        <el-button
          type="primary"
          size="default"
          :loading="loading"
          title="选择已有项目加载到地图（项目 = 顶层容器）"
          @click="handleLoadProject"
        >
          <el-icon><FolderOpened /></el-icon> 加载项目
        </el-button>
        <el-tag
          v-if="loadedProjectId"
          size="default"
          type="info"
          effect="dark"
          :title="designInfo?.schemeName || ''"
          style="margin-left: 8px;"
        >
          <template v-if="designInfo?.projectName">{{ designInfo.projectName }}（#{{ loadedProjectId }}）</template>
          <template v-else>当前项目：#{{ loadedProjectId }}</template>
        </el-tag>
        <span class="toolbar-divider"></span>
        <el-button
          type="primary"
          size="default"
          :loading="creatingTask"
          :disabled="!loadedProjectId"
          :title="loadedProjectId ? `为项目 #${loadedProjectId} 创建任务` : '请先创建或加载一个项目'"
          @click="openCreateTaskDialog"
          style="font-weight: 600;"
        >
          <el-icon><Plus /></el-icon> 创建任务
        </el-button>
        <span class="toolbar-divider"></span>
        <el-button
          type="success"
          size="small"
          :loading="loading"
          title="按当前项目方案把站点渲染到地图"
          @click="showSites"
        >
          <el-icon><View /></el-icon> 显示站点
        </el-button>
        <el-button
          type="warning"
          :loading="submitting"
          :disabled="sites.length === 0 || !!lastSubmittedHash"
          size="small"
          :title="lastSubmittedHash ? '当前数据已送审，加载或生成新数据后可再次送审' : '把当前站点数据推送到 S3 智能审查模块'"
          @click="submitToS3Review"
        >
          <el-icon><Upload /></el-icon> {{ lastSubmittedHash ? '已送审 S3' : '送审 S3 审查' }}
        </el-button>
        <el-dropdown trigger="click" size="small">
          <el-button size="small">
            <el-icon><MoreFilled /></el-icon> 更多
            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item :disabled="sites.length === 0" @click="handleClearSites">
                <el-icon><Delete /></el-icon> 清除站点
              </el-dropdown-item>
              <el-dropdown-item divided @click="generateHeatmap">
                <el-icon><TrendCharts /></el-icon> 生成热力图
              </el-dropdown-item>
              <el-dropdown-item @click="clearHeatmap">
                <el-icon><Delete /></el-icon> 清除热力图
              </el-dropdown-item>
              <el-dropdown-item @click="$router.push('/ftth')">
                <el-icon><Connection /></el-icon> FTTH 交付物
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <!-- 统计信息（顶部状态条，B 项：上移顶部） -->
    <div v-if="stats.total > 0" class="top-status-bar">
      <div class="stat-item"><span class="stat-label">总站点</span><span class="stat-val">{{ stats.total }}</span></div>
      <span class="stat-sep"></span>
      <div class="stat-item"><span class="stat-label">有效</span><span class="stat-val success">{{ stats.valid }}</span></div>
      <span class="stat-sep"></span>
      <div class="stat-item"><span class="stat-label">无效</span><span class="stat-val danger">{{ stats.invalid }}</span></div>
      <span class="stat-sep"></span>
      <div class="stat-item"><span class="stat-label">平均RSRP</span><span class="stat-val">{{ stats.avgRsrp }} dBm</span></div>
    </div>

    <!-- 状态信息（左下角） -->
    <div class="status-info">
      <span class="site-count">站点: {{ siteCount }}</span>
      <span class="status-text">{{ statusText }}</span>
      <el-dropdown
        trigger="click"
        class="location-dropdown"
        @command="handleLocationChange"
      >
        <span class="location-selector">
          <el-icon><Location /></el-icon>
          {{ currentLocationName }}
          <el-icon><ArrowDown /></el-icon>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item
              command="yuncheng"
              :disabled="currentLocation === 'yuncheng'"
            >
              📍 运城学院 (默认)
            </el-dropdown-item>
            <el-dropdown-item
              command="wuhan"
              :disabled="currentLocation === 'wuhan'"
            >
              📍 武汉
            </el-dropdown-item>
            <el-dropdown-item
              command="beijing"
              :disabled="currentLocation === 'beijing'"
            >
              📍 北京
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>

    <!-- 左侧面板 -->
    <div class="left-panel">
      <!-- 分组一：设计操作（原 assist + ops） -->
      <div class="panel-section">
        <div
          class="panel-title panel-title-clickable"
          @click="toggleSection('designOps')"
        >
          <el-icon><MagicStick /></el-icon> 设计操作
          <el-icon class="panel-chevron" :class="{ 'is-collapsed': collapsed.designOps }">
            <ArrowDown />
          </el-icon>
        </div>
        <div
          class="panel-content panel-scroll"
          v-show="!collapsed.designOps"
        >
          <!-- 智能辅助设计（原 assist 全部内容） -->
          <div class="form-item">
            <span class="form-label">模板:</span>
            <el-select
              v-model="generateParams.templateType"
              placeholder="选择模板"
              size="small"
              class="form-full-width"
            >
              <el-option
                v-for="t in templates"
                :key="t.id"
                :label="t.name"
                :value="t.category"
              />
            </el-select>
          </div>
          <div class="form-item">
            <span class="form-label">中心经度:</span>
            <el-input
              v-model="generateParams.centerLongitude"
              size="small"
              class="form-full-width"
              :placeholder="DEFAULT_LOCATION.longitude.toString()"
            />
          </div>
          <div class="form-item">
            <span class="form-label">中心纬度:</span>
            <el-input
              v-model="generateParams.centerLatitude"
              size="small"
              class="form-full-width"
              :placeholder="DEFAULT_LOCATION.latitude.toString()"
            />
          </div>
          <div class="form-item">
            <span class="form-label">覆盖半径(m):</span>
            <el-input
              v-model="generateParams.coverageRadius"
              size="small"
              class="form-full-width"
              placeholder="500"
            />
          </div>
          <div class="form-item">
            <span class="form-label">网格大小(m):</span>
            <el-input
              v-model="generateParams.gridSize"
              size="small"
              class="form-full-width"
              placeholder="200"
            />
          </div>
          <div class="form-item">
            <span class="form-label">扇区数:</span>
            <el-select
              v-model="generateParams.sectorCount"
              size="small"
              class="form-full-width"
            >
              <el-option
                label="1扇区"
                :value="1"
              />
              <el-option
                label="3扇区"
                :value="3"
              />
              <el-option
                label="6扇区"
                :value="6"
              />
            </el-select>
          </div>
          <!-- 验证错误/警告提示 -->
          <div
            v-if="fieldErrors.general?.length"
            class="validation-errors"
          >
            <div
              v-for="(err, i) in fieldErrors.general"
              :key="'e'+i"
            >
              ⚠ {{ err }}
            </div>
          </div>
          <div
            v-if="fieldWarnings.general?.length"
            class="validation-warnings"
          >
            <div
              v-for="(warn, i) in fieldWarnings.general"
              :key="'w'+i"
            >
              ⚠ {{ warn }}
            </div>
          </div>
          <el-button
            size="small"
            class="form-full-width form-mt-8"
            :loading="generating"
            title="从零生成蜂窝网格（空白规划，不依赖 QGIS 数据）"
            @click="generateDesign"
          >
            空白网格规划
          </el-button>

          <!-- 次级标题：方案操作（原 ops） -->
          <div class="sub-group-title">方案操作</div>
          <el-button
            size="small"
            class="form-full-width form-mt-8"
            @click="savePlan"
          >
            <el-icon><Download /></el-icon> 保存方案（GeoJSON）
          </el-button>
        </div>
      </div>

      <!-- 分组一点五：设计任务（常驻任务列表，GET /design/tasks） -->
      <div class="panel-section">
        <div
          class="panel-title panel-title-clickable"
          @click="toggleSection('taskList')"
        >
          <el-icon><Tickets /></el-icon> 设计任务
          <span class="task-total-badge">{{ designTaskList.length }}</span>
          <el-icon class="panel-chevron" :class="{ 'is-collapsed': collapsed.taskList }">
            <ArrowDown />
          </el-icon>
        </div>
        <div v-show="!collapsed.taskList" class="panel-content panel-scroll">
          <div class="task-toolbar">
            <el-button
              size="small"
              text
              type="primary"
              :loading="taskListLoading"
              @click="loadDesignTasks"
            >
              <el-icon><Refresh /></el-icon> 刷新
            </el-button>
          </div>
          <div v-if="taskListLoading && designTaskList.length === 0" class="task-empty">
            任务加载中...
          </div>
          <div v-else-if="!loadedProjectId" class="task-empty">
            请先「加载项目」或「创建项目」，任务隶属于具体项目
          </div>
          <div v-else-if="designTaskList.length === 0" class="task-empty">
            暂无任务，点击顶部「创建任务」为本项目添加
          </div>
          <div
            v-for="t in designTaskList"
            :key="t.id"
            class="task-item"
            :class="{ 'task-item-current': isTaskCurrent(t) }"
          >
            <div class="task-item-head">
              <span class="task-item-name" :title="t.taskName">
                #{{ t.id }} {{ t.taskName || t.taskNo }}
              </span>
              <el-tag v-if="isTaskCurrent(t)" type="primary" size="small" effect="dark">
                当前
              </el-tag>
            </div>
            <div class="task-item-meta">
              <el-tag :type="taskStatus(t.status).type" size="small" effect="light">
                {{ taskStatus(t.status).label }}
              </el-tag>
              <el-tag v-if="t.localDataFlag" size="small" effect="plain" type="primary">本地数据</el-tag>
              <span class="task-item-no">{{ t.taskNo }}</span>
              <span class="task-item-time">{{ formatTaskTime(t.updatedAt || t.createdAt) }}</span>
            </div>
            <div class="task-item-actions">
              <el-button
                size="small"
                type="primary"
                link
                @click="pickGeoJSONForTask(t)"
              >
                <el-icon><FolderOpened /></el-icon> 加载数据
              </el-button>
              <el-button
                size="small"
                type="info"
                link
                :disabled="t.status !== 'completed'"
                @click="viewTaskResult(t)"
              >
                <el-icon><View /></el-icon> 查看成果
              </el-button>
              <el-button
                size="small"
                type="primary"
                link
                :loading="t._running"
                :disabled="t.status === 'generating'"
                @click="runDesignTask(t)"
              >
                <el-icon><VideoPlay /></el-icon> {{ t.status === 'completed' ? '重新执行' : '执行' }}
              </el-button>
              <el-button
                size="small"
                type="danger"
                link
                :loading="t._deleting"
                @click="deleteDesignTask(t)"
              >
                <el-icon><Delete /></el-icon> 删除
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <!-- 分组二：显示控制（原 coverage + layers + legend） -->
      <div class="panel-section">
        <div
          class="panel-title panel-title-clickable"
          @click="toggleSection('displayControl')"
        >
          <el-icon><View /></el-icon> 显示控制
          <el-icon class="panel-chevron" :class="{ 'is-collapsed': collapsed.displayControl }">
            <ArrowDown />
          </el-icon>
        </div>
        <div
          class="panel-content panel-scroll"
          v-show="!collapsed.displayControl"
        >
          <!-- 覆盖控制 -->
          <div class="sub-group-title">覆盖控制</div>
          <el-checkbox
            v-model="showCoverage"
            @change="toggleLayer('coverage', showCoverage)"
          >
            覆盖范围
          </el-checkbox>
          <el-checkbox
            v-model="showLabels"
            @change="toggleLayer('label', showLabels)"
          >
            基站标签
          </el-checkbox>
          <el-checkbox
            v-model="showMachineRoomLabels"
            @change="toggleMachineRoomLabels(showMachineRoomLabels)"
          >
            机房标签
          </el-checkbox>
          <el-checkbox
            v-model="showFtth"
            @change="toggleFtthOverlay(showFtth)"
          >
            <el-icon style="color: #22d3ee; margin-right: 4px">
              <Connection />
            </el-icon>FTTH 叠加
          </el-checkbox>
          <div class="slider-row">
            <span>透明度:</span>
            <el-slider
              v-model="coverageOpacity"
              :min="0"
              :max="100"
              class="slider-width"
              @change="updateCoverageOpacity"
            />
          </div>

          <!-- 图层控制 -->
          <div class="sub-group-title">图层控制</div>
          <el-checkbox
            v-model="showSiteMarkers"
            @change="toggleLayer('site', showSiteMarkers)"
          >
            站点标记
          </el-checkbox>
          <el-checkbox
            v-model="showConnections"
            @change="toggleConnections(showConnections)"
          >
            管线连线
          </el-checkbox>
          <el-checkbox
            v-model="showBackbone"
            @change="toggleBackbone(showBackbone)"
          >
            机房骨干树 (MST)
          </el-checkbox>
          <el-checkbox
            v-model="showTowers"
            @change="toggleLayer('tower', showTowers)"
          >
            塔桅
          </el-checkbox>

          <!-- 图例 -->
          <div class="sub-group-title">图例</div>
          <div
            v-for="(color, index) in legendColors"
            v-once
            :key="index"
            class="legend-item"
          >
            <span
              class="legend-dot"
              :style="{ backgroundColor: color.color }"
            />
            <span>{{ color.label }}</span>
          </div>
          <div class="legend-divider" />
          <div class="legend-item">
            <span
              class="legend-dot"
              style="background-color: #888;"
            />
            <span>塔桅</span>
          </div>
          <div class="legend-item">
            <span
              class="legend-dot"
              style="background-color: rgba(0,100,255,0.3);"
            />
            <span>覆盖范围</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧面板 -->
    <div class="right-panel">
      <!-- 设计信息 -->
      <div
        v-if="designInfo"
        class="panel-section"
      >
        <div class="panel-title">
          <el-icon><Document /></el-icon> 设计信息
        </div>
        <div class="panel-content">
          <div class="info-row">
            <span class="label">方案ID:</span>
            <span class="value">{{ designInfo.id ?? designInfo.projectId ?? '-' }}</span>
          </div>
          <div class="info-row">
            <span class="label">项目ID:</span>
            <span class="value">{{ designInfo.projectId ?? designInfo.id ?? '-' }}</span>
          </div>
          <div class="info-row">
            <span class="label">方案:</span>
            <span class="value">{{ designInfo.schemeName }}</span>
          </div>
          <div class="info-row">
            <span class="label">来源任务:</span>
            <span class="value">{{ designInfo.taskNo ? `#${designInfo.taskNo}` : '-' }}</span>
          </div>
          <div class="info-row">
            <span class="label">数据源:</span>
            <span class="value">
              <template v-if="localDataSourceTask">
                <el-tag size="small" type="primary" effect="light">本地 GeoJSON · 任务 #{{ localDataSourceTask }}</el-tag>
              </template>
              <template v-else-if="currentTaskId">
                <el-tag size="small" type="success" effect="light">任务 #{{ currentTaskId }} 成果</el-tag>
              </template>
              <template v-else>-</template>
            </span>
          </div>
          <div class="info-row">
            <span class="label">频段:</span>
            <span class="value">{{ designInfo.frequencyBand }}</span>
          </div>
          <div class="info-row">
            <span class="label">塔高:</span>
            <span class="value">{{ designInfo.towerHeight }}m</span>
          </div>
          <div class="info-row">
            <span class="label">站点:</span>
            <span class="value">{{ designInfo.totalSites }}个</span>
          </div>
          <div class="info-row">
            <span class="label">有效:</span>
            <span class="value success">{{ designInfo.validSites }}</span>
          </div>
          <div class="info-row">
            <span class="label">无效:</span>
            <span class="value danger">{{ designInfo.invalidSites }}</span>
          </div>
        </div>
      </div>

      <!-- 站点详情 -->
      <div
        v-if="selectedSite"
        class="panel-section"
      >
        <div class="panel-title">
          <el-icon><Location /></el-icon> 站点详情
          <el-button
            type="text"
            size="small"
            class="close-btn"
            @click="selectedSite = null"
          >
            <el-icon><Close /></el-icon>
          </el-button>
        </div>
        <div class="panel-content">
          <div class="info-row">
            <span class="label">ID:</span>
            <span class="value">{{ selectedSite.siteId }}</span>
          </div>
          <div class="info-row">
            <span class="label">坐标:</span>
            <span class="value">{{ selectedSite.longitude.toFixed(4) }}, {{ selectedSite.latitude.toFixed(4) }}</span>
          </div>
          <div class="info-row">
            <span class="label">塔高:</span>
            <span class="value">{{ selectedSite.towerHeight }}m</span>
          </div>
          <div class="info-row">
            <span class="label">RSRP:</span>
            <span
              class="value"
              :class="getRsrpClass(selectedSite.rsrp)"
            >{{ selectedSite.rsrp }} dBm</span>
          </div>
          <div class="info-row">
            <span class="label">状态:</span>
            <el-tag
              :type="selectedSite.isValid === 1 ? 'success' : 'danger'"
              size="small"
            >
              {{ selectedSite.isValid === 1 ? '正常' : '故障' }}
            </el-tag>
          </div>
          <div class="info-row">
            <span class="label">覆盖:</span>
            <span class="value">~1.5km</span>
          </div>
          <div class="info-row">
            <span class="label">天线:</span>
            <span class="value">3个/3扇区</span>
          </div>
          <div class="info-row">
            <span class="label">建设:</span>
            <span class="value">2026-05-20</span>
          </div>
          <div class="info-row">
            <span class="label">维护:</span>
            <span class="value">烽火通信</span>
          </div>
          <div class="action-buttons">
            <el-button
              type="primary"
              size="small"
              @click="flyToSite(selectedSite)"
            >
              <el-icon><Location /></el-icon> 飞到站点
            </el-button>
            <el-button
              size="small"
              @click="showSiteCoverage(selectedSite)"
            >
              <el-icon><View /></el-icon> 查看覆盖
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部站点列表 -->
    <div
      v-if="sites.length > 0"
      class="bottom-panel"
    >
      <div class="panel-title">
        <el-icon><List /></el-icon> 站点列表 ({{ filteredSites.length }}/{{ sites.length }})
        <div class="list-controls">
          <el-select
            v-model="filterValid"
            size="small"
            class="filter-select"
          >
            <el-option
              label="全部"
              value="all"
            />
            <el-option
              label="正常"
              value="valid"
            />
            <el-option
              label="故障"
              value="invalid"
            />
          </el-select>
          <el-select
            v-model="sortBy"
            size="small"
            class="filter-select"
          >
            <el-option
              label="ID排序"
              value="siteId"
            />
            <el-option
              label="RSRP排序"
              value="rsrp"
            />
            <el-option
              label="经度排序"
              value="longitude"
            />
          </el-select>
        </div>
      </div>
      <div class="site-list-container">
        <el-button
          class="scroll-btn scroll-left"
          :disabled="listScrollLeft <= 0"
          aria-label="向左滚动站点列表"
          @click="scrollList('left')"
        >
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <div
          ref="siteListRef"
          class="site-list-scroll"
        >
          <div
            v-for="site in filteredSites"
            :key="site.siteId"
            v-memo="[selectedSite?.siteId === site.siteId, site.rsrp, site.isValid, expandedSiteId === site.siteId]"
            class="site-card"
            :class="{ active: selectedSite?.siteId === site.siteId }"
            @click="selectSite(site)"
          >
            <div class="site-card-header">
              <span class="site-id">{{ site.siteId }}</span>
              <el-tag
                :type="site.isValid === 1 || site.isValid === true ? 'success' : 'danger'"
                size="small"
              >
                {{ site.isValid === 1 || site.isValid === true ? '正常' : '故障' }}
              </el-tag>
            </div>
            <div class="site-card-body">
              <span
                class="rsrp"
                :class="getRsrpClass(site.rsrp)"
              >{{ site.rsrp }} dBm</span>
              <span class="coords">{{ Number(site.longitude).toFixed(2) }}, {{ Number(site.latitude).toFixed(2) }}</span>
            </div>
            <div
              class="site-card-footer"
              @click.stop="toggleSiteDevices(site.siteId)"
            >
              <el-icon><ArrowDown v-if="expandedSiteId !== site.siteId" /><ArrowUp v-else /></el-icon>
              <span>设备 {{ deviceCountBySite[site.siteId] || 0 }}</span>
            </div>
            <div
              v-if="expandedSiteId === site.siteId"
              class="site-devices"
            >
              <div
                v-for="dev in expandedDevices"
                :key="dev.positionId || dev.deviceName"
                class="site-device-item"
              >
                <span class="dev-name">{{ dev.deviceName }}</span>
                <span class="dev-type">{{ dev.deviceType }}</span>
                <span
                  v-if="dev.azimuth != null && dev.azimuth !== ''"
                  class="dev-az"
                >方位 {{ dev.azimuth }}°</span>
              </div>
            </div>
          </div>
        </div>
        <el-button
          class="scroll-btn scroll-right"
          aria-label="向右滚动站点列表"
          @click="scrollList('right')"
        >
          <el-icon><ArrowRight /></el-icon>
        </el-button>
      </div>
    </div>

    <!-- Cesium容器 -->
    <div
      id="cesiumContainer"
      class="cesium-container"
    />

    <!-- P1: Cesium 引擎初始化加载态（先于阻塞主线程的初始化显示） -->
    <div
      v-if="cesiumLoading"
      class="map-loading-overlay"
    >
      <div class="map-loading-spinner" />
      <span>正在加载三维地图引擎...</span>
    </div>

    <!-- P0: 生成中遮罩（地图可见加载态，而非只弹 toast） -->
    <div
      v-if="generating"
      class="map-loading-overlay"
    >
      <div class="map-loading-spinner" />
      <span>正在生成三维通信基站方案...</span>
    </div>

    <!-- P1: 生成回执横幅（回显实际使用的参数，便于核对） -->
    <div
      v-if="lastReceipt"
      class="gen-receipt"
    >
      <div class="gen-receipt-title">
        <el-icon><Check /></el-icon> 已生成 {{ lastReceipt.siteCount }} 个基站
        <el-tag
          size="small"
          :type="lastReceipt.source === 'backend' ? 'success' : 'info'"
          class="gen-receipt-source"
        >
          {{ lastReceipt.source === 'backend' ? '后端生成' : '本地预览' }}
        </el-tag>
      </div>
      <div class="gen-receipt-body">
        <span>类型：{{ receiptTypeLabel }}</span>
        <span>位置：{{ lastReceipt.location }}</span>
        <span>覆盖半径：{{ lastReceipt.coverageRadius }}m</span>
        <span>扇区：{{ lastReceipt.sectorCount }}</span>
        <span>频段：{{ lastReceipt.frequencyBand }}</span>
        <span>塔高：{{ lastReceipt.towerHeight }}m</span>
      </div>
      <button
        class="gen-receipt-close"
        aria-label="关闭回执"
        @click="dismissReceipt"
      >
        ×
      </button>
    </div>

    <!-- 加载数据：项目选择弹窗（居中显眼，不默认，必须手动选择） -->
    <el-dialog
      v-model="loadProjectDialogVisible"
      title="选择要加载的项目"
      width="480px"
      align-center
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      class="load-project-dialog"
      @closed="cancelLoadProject"
    >
      <div class="load-project-body">
        <p class="load-project-tip">
          <el-icon><InfoFilled /></el-icon>
          请选择一个项目，再点击"确定"加载设计数据：
        </p>
        <el-select
          v-model="loadSelectedProjectId"
          placeholder="请选择项目"
          size="large"
          filterable
          clearable
          :loading="loadProjectListLoading"
          style="width: 100%"
        >
          <el-option
            v-for="opt in loadProjectOptions"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
        <p
          v-if="!loadProjectListLoading && loadProjectOptions.length === 0"
          class="load-project-empty"
        >
          暂无项目，请先在 QGIS 插件中同步数据以创建项目。
        </p>
        <div class="load-project-local">
          <el-divider>或</el-divider>
          <input
            ref="localGeoJSONInput"
            type="file"
            accept=".geojson,.json,application/geo+json"
            style="display: none"
            @change="handleLocalGeoJSONSelected"
          >
          <el-button
            plain
            @click="openLocalGeoJSONPicker"
          >
            <el-icon><FolderOpened /></el-icon>
            加载本地 GeoJSON 文件
          </el-button>
        </div>
      </div>
      <template #footer>
        <el-button @click="cancelLoadProject">
          取消
        </el-button>
        <el-button
          type="primary"
          :disabled="!loadSelectedProjectId"
          @click="confirmLoadProject"
        >
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 创建项目（容器） -->
    <el-dialog
      v-model="createProjectDialogVisible"
      title="创建项目（项目是顶层容器）"      width="480"
      :close-on-click-modal="false"
    >
      <el-alert type="info" :closable="false" style="margin-bottom:12px;font-size:12px;">
        项目是顶层容器，创建后可点击顶部「创建任务」在其下添加子任务，
        任务执行时会自动设计 → 自动送 S3 审查。
      </el-alert>
      <el-form :model="createProjectForm" label-width="84">
        <el-form-item label="项目名称" required>
          <el-input v-model="createProjectForm.projectName" placeholder="如：运城移动通信基建项目" maxlength="80" show-word-limit />
        </el-form-item>
        <el-form-item label="项目编码">
          <el-input v-model="createProjectForm.projectCode" placeholder="可选，如：YC-2026-01" maxlength="50" />
        </el-form-item>
        <el-form-item label="区域">
          <el-input v-model="createProjectForm.regionCode" placeholder="可选，如：山西运城" maxlength="50" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="createProjectForm.description" type="textarea" :rows="2" placeholder="可选，项目备注" maxlength="200" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createProjectDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creatingProject" @click="submitCreateProject">
          <el-icon><FolderAdd /></el-icon> 创建并进入项目
        </el-button>
      </template>
    </el-dialog>

    <!-- 任务级本地 GeoJSON 文件选择（隐藏 input） -->
    <input
      ref="taskGeoJSONInput"
      type="file"
      accept=".geojson,.json,application/geo+json"
      style="display: none"
      @change="handleTaskGeoJSONSelected"
    >
  </div>
</template>

<script>
export default { name: 'DesignView' }
</script>
<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'
import * as Cesium from 'cesium'
import { createViewer } from '@/composables/useCesiumCore.js'
import { ElMessage, ElMessageBox } from 'element-plus'
import { DEFAULT_LOCATION, getPresetLocation } from '@/config/location.js'
import { registerDefaultShortcuts, shortcutManager } from '@/utils/shortcutManager.js'
import { useDesignState } from '@/composables/useDesignState.js'
import { useSiteManager, LEGEND_COLORS } from '@/composables/useSiteManager.js'
import { useProjectManager } from '@/composables/useProjectManager.js'
import { useCoverageAnalysis } from '@/composables/useCoverageAnalysis.js'
import { useFtthDataset } from '@/composables/useFtthDataset.js'
import { logger } from '@/utils/logger.js'
import { designAPI, projectAPI } from '@/utils/request.js'
import { exportAsGeoJSON } from '@/utils/exportUtils.js'

// ── 共享状态 ──────────────────────────────────────────────
const viewer = ref(null)
const cesiumLoading = ref(true)  // Cesium 引擎初始加载态（挂载时先显示遮罩）
const siteListRef = ref(null)
const listScrollLeft = ref(0)
const _timers = []
const coverageOpacity = ref(50)  // 热力图默认透明度 50%（原 15% 在卫星底图下几乎看不见）
const designInfo = ref(null)
const currentLocation = ref('yuncheng')

// ── 左侧各分组折叠状态（key 对应各 panel-section） ────────
const collapsed = reactive({
  designOps: false,      // 设计操作（默认展开）
  taskList: false,       // 设计任务（常驻任务列表，默认展开）
  displayControl: true,  // 显示控制（默认折叠）
})

// ── 设计任务列表（常驻，GET /design/tasks） ────────────────
const designTaskList = ref([])
const taskListLoading = ref(false)

const TASK_STATUS_MAP = {
  draft: { label: '草稿', type: 'info' },
  generating: { label: '生成中', type: 'warning' },
  completed: { label: '已完成', type: 'success' },
  failed: { label: '失败', type: 'danger' }
}
const taskStatus = (s) => TASK_STATUS_MAP[s] || { label: s || '未知', type: 'info' }

// 当前任务追踪：
// ① 本会话/本地执行过的任务（持久化到 localStorage，刷新不丢）；
// ② 已加载方案 projectId 与任务 projectId 匹配 → 自动识别为当前任务
const currentTaskId = ref(Number(localStorage.getItem('m03_current_task_id')) || null)

function isTaskCurrent(t) {
  if (currentTaskId.value != null && Number(currentTaskId.value) === Number(t.id)) return true
  const pid = designInfo.value?.projectId
  if (pid != null && t.projectId != null && Number(t.projectId) === Number(pid)) return true
  // 任务主线：加载的方案带 taskNo 时，精确匹配来源任务
  if (designInfo.value?.taskNo && t.taskNo && designInfo.value.taskNo === t.taskNo) return true
  return false
}

// 已加载的项目 ID（任务主线：加载数据 → 选项目 → 创建任务）
const loadedProjectId = computed(() => {
  return designInfo.value?.projectId || designInfo.value?.id || null
})
const creatingTask = ref(false)

// ── 创建项目弹窗（项目 = m03_project 顶层容器） ──
const createProjectDialogVisible = ref(false)
const createProjectForm = reactive({
  projectName: '',
  projectCode: '',
  regionCode: '',
  description: ''
})
const creatingProject = ref(false)

function openCreateProjectDialog() {
  createProjectForm.projectName = ''
  createProjectForm.projectCode = ''
  createProjectForm.regionCode = ''
  createProjectForm.description = ''
  createProjectDialogVisible.value = true
}

async function submitCreateProject() {
  const name = String(createProjectForm.projectName || '').trim()
  if (!name) {
    ElMessage.error('请填写项目名称')
    return
  }
  creatingProject.value = true
  try {
    const resp = await projectAPI.create({
      projectName: name,
      projectCode: createProjectForm.projectCode || null,
      regionCode: createProjectForm.regionCode || null,
      description: createProjectForm.description || null
    })
    const newProjectId = resp?.data?.id
    ElMessage.success(`项目已创建：${resp?.data?.projectName || name} (id=${newProjectId})`)
    createProjectDialogVisible.value = false
    if (newProjectId) {
      // 创建后自动进入项目（加载项目 + 方案 + 任务）
      await loadProjectById(newProjectId)
      await loadDesignTasks()
    }
  } catch (e) {
    // 拦截器已弹错误提示
  } finally {
    creatingProject.value = false
  }
}

// 顶部「加载项目」按钮：选择项目 → 加载项目+方案+任务
async function handleLoadProject() {
  await loadDesignData()
  await loadDesignTasks()
}

// 加载指定 ID 的项目到 designInfo（用于刚创建的项目自动加载）—— 走 useDesignState 的聚合加载
async function loadDesignDataById(projectId) {
  await loadProjectById(projectId)
  await loadDesignTasks()
}

/** 顶部导航「创建任务」按钮：基于当前加载的项目 + 设计参数创建任务。 */
function openCreateTaskDialog() {
  const projectId = loadedProjectId.value
  if (!projectId) {
    ElMessage.warning('请先创建或加载一个项目')
    return
  }
  submitCreateTask()
}

async function submitCreateTask() {
  const projectId = loadedProjectId.value
  if (!projectId) {
    ElMessage.warning('请先创建或加载一个项目')
    return
  }
  const params = {
    templateType: generateParams.templateType,
    centerLongitude: Number(generateParams.centerLongitude),
    centerLatitude: Number(generateParams.centerLatitude),
    coverageRadius: Number(generateParams.coverageRadius),
    gridSize: generateParams.gridSize,
    sectorCount: generateParams.sectorCount,
    towerHeight: Number(generateParams.towerHeight),
    frequencyBand: generateParams.frequencyBand
  }
  if (!isFinite(params.centerLongitude) || !isFinite(params.centerLatitude)) {
    ElMessage.error('设计参数中的中心经纬度无效，请检查「设计操作」面板')
    return
  }
  const projectName = designInfo.value?.schemeName || `项目 #${projectId}`
  const autoName = `${projectName} · ${params.templateType || 'macro'}`
  // 任务名是贯穿 S3 审查 / S4 BOM / S5 施工监控的标识，创建前让用户确认/修改
  let taskName = ''
  try {
    const { value } = await ElMessageBox.prompt(
      '该任务名称将贯穿 S3 智能审查、S4 BOM 清单、S5 施工监控，请确认或修改：',
      '创建设计任务',
      {
        inputValue: autoName,
        confirmButtonText: '创建',
        cancelButtonText: '取消',
        inputPlaceholder: '请输入任务名称',
        inputValidator: (v) => (v && v.trim() ? true : '任务名称不能为空'),
        inputErrorMessage: '任务名称不能为空'
      }
    )
    taskName = value.trim()
  } catch {
    return // 用户取消 → 不创建
  }
  creatingTask.value = true
  try {
    const resp = await designAPI.createDesignTask({
      taskName,
      projectId: String(projectId),
      paramsJson: JSON.stringify(params)
    })
    ElMessage.success(`任务已创建${resp?.data?.taskNo ? '：' + resp.data.taskNo : ''}`)
    loadDesignTasks()
  } catch (e) {
    // 拦截器已弹错误提示
  } finally {
    creatingTask.value = false
  }
}

async function deleteDesignTask(task) {
  try {
    await ElMessageBox.confirm(
      `确认删除任务 #${task.id}「${task.taskName || task.taskNo}」？\n将级联删除该任务的所有设备布局数据，且不可恢复。`,
      '删除设计任务',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }
  task._deleting = true
  try {
    await designAPI.deleteDesignTask(task.id)
    ElMessage.success(`任务 #${task.id} 已删除`)
    loadDesignTasks()
  } catch (e) {
    // 拦截器已弹错误
  } finally {
    task._deleting = false
  }
}

/** 查看任务成果：按 taskId 拉 resultJson 解析后的设计数据，直接上地图（不依赖方案表）。
 *  resultJson 为空但存在任务级本地数据（localDataJson）时，用本地 GeoJSON 恢复。 */
async function viewTaskResult(task) {
  try {
    const resp = await designAPI.getTaskResult(task.id)
    const payload = resp?.data
    const result = payload?.result
    // 未执行（resultJson 空）但有持久化本地数据 → 恢复本地 GeoJSON
    if ((!result || !Array.isArray(result.sites) || result.sites.length === 0)
        && payload?.localDataJson) {
      try {
        const ok = await loadLocalGeoJSON(JSON.parse(payload.localDataJson))
        if (ok) {
          // 恢复后保留项目上下文
          const pid = designInfo.value?.projectId || designInfo.value?.id || null
          if (pid != null) {
            designInfo.value = { ...designInfo.value, projectId: pid, id: pid }
          }
          localDataSourceTask.value = task.id
          currentTaskId.value = task.id
          localStorage.setItem('m03_current_task_id', String(task.id))
          ElMessage.success(`已从任务 #${task.id} 恢复本地数据（${sites.value.length} 个站点）`)
          return
        }
      } catch (e) {
        ElMessage.error('恢复本地数据失败：' + (e?.message || e))
        return
      }
    }
    if (!payload || !result || !Array.isArray(result.sites) || result.sites.length === 0) {
      ElMessage.warning(`任务 #${task.id} 暂无成果数据（可能未执行成功）`)
      return
    }
    clearSites()
    // DesignData.sites (SiteData) → 站点列表结构（与 m03_site 查询结果对齐，供 addSitesToMap 消费）
    sites.value = (result.sites || []).map((s, i) => ({
      id: i + 1,
      siteId: s.siteId || s.site_id || `SITE-${i + 1}`,
      siteName: s.siteName || s.site_name || `站点${i + 1}`,
      longitude: Number(s.longitude),
      latitude: Number(s.latitude),
      towerHeight: Number(s.towerHeight ?? s.tower_height ?? 30),
      siteType: s.siteType || s.site_type || 'MACRO',
      scenario: (s.scenario || 'URBAN').toUpperCase(),
      rsrp: s.rsrp != null ? Number(s.rsrp) : null,
      isValid: s.isValid !== false,
    }))
    siteCount.value = sites.value.length
    designInfo.value = {
      ...(designInfo.value || {}),
      id: null,
      projectId: task.projectId ?? null,
      taskNo: payload.taskNo,
      taskName: payload.taskName,
      schemeName: result.schemeName || task.taskName,
      towerHeight: result.towerHeight,
      totalSites: result.totalSites ?? sites.value.length,
      validSites: result.validSites ?? null,
      invalidSites: result.invalidSites ?? null,
    }
    currentTaskId.value = task.id
    localStorage.setItem('m03_current_task_id', String(task.id))
    localDataSourceTask.value = null
    addSitesToMap()
    zoomToSites()
    ElMessage.success(`已加载任务 #${task.id}（${payload.taskNo || ''}）的设计成果，${sites.value.length} 个站点`)
  } catch (e) {
    ElMessage.error('查看成果失败: ' + (e?.message || e))
  }
}

function formatTaskTime(t) {
  if (!t) return '-'
  const s = String(t)
  return s.length > 16 ? s.slice(0, 16).replace('T', ' ') : s.replace('T', ' ')
}

// ── 任务级本地 GeoJSON 加载（数据源绑定到具体任务） ───────
const taskGeoJSONInput = ref(null)
const pendingTaskForGeoJSON = ref(null)
// 当前地图数据来自本地文件的任务（用于设计信息面板展示「数据源」）
const localDataSourceTask = ref(null)

function pickGeoJSONForTask(task) {
  pendingTaskForGeoJSON.value = task
  taskGeoJSONInput.value?.click()
}

async function handleTaskGeoJSONSelected() {
  const task = pendingTaskForGeoJSON.value
  const file = taskGeoJSONInput.value?.files?.[0]
  taskGeoJSONInput.value.value = ''
  pendingTaskForGeoJSON.value = null
  if (!task || !file) return
  try {
    const text = await file.text()
    const geojson = JSON.parse(text)
    if (geojson?.type !== 'FeatureCollection') {
      ElMessage.warning('文件格式错误：需要 GeoJSON FeatureCollection')
      return
    }
    // 加载前记住项目上下文（loadLocalGeoJSON 会把 designInfo.projectId 置空）
    const pid = designInfo.value?.projectId || designInfo.value?.id || null
    const projectName = designInfo.value?.projectName || null
    const ok = await loadLocalGeoJSON(geojson)
    if (ok) {
      // 绑定到任务：标记当前任务 + 数据源
      currentTaskId.value = task.id
      localStorage.setItem('m03_current_task_id', String(task.id))
      localDataSourceTask.value = task.id
      // 恢复项目上下文（任务隶属于项目，不能因本地加载丢失）
      if (pid != null) {
        designInfo.value = { ...designInfo.value, projectId: pid, id: pid, projectName }
      }
      ElMessage.success(`已把本地 GeoJSON 加载到任务 #${task.id}（${sites.value.length} 个站点）`)
      // 持久化：保存到任务（刷新/重进项目可恢复）
      try {
        await designAPI.saveTaskLocalData(task.id, text)
        task.localDataFlag = true
        ElMessage.success(`任务 #${task.id} 的本地数据已保存`)
      } catch (e) {
        // 保存失败不阻塞查看（拦截器已提示）
      }
    }
  } catch (e) {
    ElMessage.error('GeoJSON 解析失败：' + (e?.message || e))
  }
}

async function loadDesignTasks() {
  taskListLoading.value = true
  try {
    // 任务列表按当前项目过滤（项目 = 顶层容器）
    const params = loadedProjectId.value ? { projectId: loadedProjectId.value } : {}
    const resp = await designAPI.listDesignTasks(params)
    // 响应拦截器已返回 {code,message,data}；保留 _running 局部标记
    const list = (resp && resp.data) || []
    designTaskList.value = list.map((t) => ({
      ...t,
      _running: designTaskList.value.find((old) => old.id === t.id)?._running || false
    }))
  } catch (e) {
    logger.warn('设计任务列表加载失败', e)
  } finally {
    taskListLoading.value = false
  }
}

async function runDesignTask(task) {
  try {
    await ElMessageBox.confirm(
      `确认执行设计任务 #${task.id}「${task.taskName || task.taskNo}」？将调用设计引擎生成设备布局并落库。`,
      '执行设计任务',
      { confirmButtonText: '执行', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }
  task._running = true
  try {
    await designAPI.executeDesignTask(task.id)
    currentTaskId.value = task.id
    localStorage.setItem('m03_current_task_id', String(task.id))
    ElMessage.success(`任务 #${task.id} 执行完成，已标记为当前任务`)
  } catch (e) {
    // 拦截器已弹错误提示，这里补充状态刷新
  } finally {
    task._running = false
    loadDesignTasks()
  }
}
function toggleSection(key) {
  collapsed[key] = !collapsed[key]
}

// ── FTTH 叠加层 ─────────────────────────────────────
const showFtth = ref(false)
const ftthData = ref(null)           // { boites, cables, sites, imbs }
let _ftthEntities = []               // FTTH 实体引用（用于清除）
const { path: ftthPath } = useFtthDataset()

// 共享响应式参数 (供 designState 和 projectManager 共同使用)
const generateParams = reactive({
  templateType: 'macro',
  centerLongitude: DEFAULT_LOCATION.longitude.toString(),
  centerLatitude: DEFAULT_LOCATION.latitude.toString(),
  coverageRadius: DEFAULT_LOCATION.defaultCoverageRadius.toString(),
  gridSize: DEFAULT_LOCATION.defaultGridSize.toString(),
  sectorCount: DEFAULT_LOCATION.defaultSectorCount,
  frequencyBand: '3.5GHz',
  towerHeight: 35
})

/** Safe setTimeout that gets cleaned up on unmount */
const _safeSetTimeout = (fn, delay) => {
  const id = setTimeout(() => {
    const idx = _timers.indexOf(id)
    if (idx > -1) _timers.splice(idx, 1)
    fn()
  }, delay)
  _timers.push(id)
  return id
}

// ── 组合式函数初始化 ──────────────────────────────────────
// 1. 站点管理 (提供 sites 给其他模块)
const {
  sites, selectedSite, siteCount, searchText, filterValid, sortBy,
  filteredSites, stats,
  showConnections,
  showBackbone,
  showMachineRoomLabels,
  addSitesToMap, bindClickHandler, deleteSite, removeSiteEntities,
  clearSites, zoomToSites, selectSite, highlightSite,
  flyToSite, showSiteCoverage, searchSite, getRsrpClass,
  drawConnections, setHubPoint, setMachineRooms, machineRooms, findNearestRoom,
  clearConnections, toggleConnections, toggleBackbone, toggleMachineRoomLabels, cleanupEntities,
} = useSiteManager({ viewer, coverageOpacity })

// 2. 覆盖分析 (依赖 viewer 和 sites)
// T8: 将 QGIS 设计的射频参数（频段/覆盖半径/场景）下发给 3D 热力图，强化 QGIS↔3D 同步
const frequencyMHz = computed(() => {
  const band = designInfo.value?.frequencyBand
  if (!band) return 2100
  const map = {
    'fdd-lte-800': 850, 'fdd-lte-900': 900, 'fdd-lte-1800': 1800,
    'tdd-lte-2300': 2300, 'tdd-lte-2600': 2600, '5g-n79': 4900, '5g-n41': 2500,
    '700mhz': 700, '3.5ghz': 3500, '2.1ghz': 2100,
  }
  return map[band.toLowerCase()] || 2100
})

const {
  showSiteMarkers, showTowers, showCoverage, showLabels,
  animationEnabled, coverageMetrics, coverageGaps,
  showCoverageReport, generateHeatmap, clearHeatmap, exportMapScreenshot,
  toggleLayer, updateCoverageOpacity, toggleAnimation, cleanupAnimation,
} = useCoverageAnalysis({
  viewer, sites, coverageOpacity,
  frequencyMHz: frequencyMHz.value,
  coverageRadius: Number(generateParams.coverageRadius) || 500,
  environment: 'URBAN',
})

// 3. 项目管理 (先于 designState 初始化，提供 operationHistory)
const {
  projectDialogVisible, projects, currentProjectName, activeProjectId,
  operationHistory,
  saveProject, loadProject, deleteProject, scheduleAutoSave,
  exportProject, undo, redo, cleanup: cleanupProject,
} = useProjectManager({
  sites, generateParams, designInfo, currentLocation, stats,
  clearSites, addSitesToMap, zoomToSites,
})

// 4. 设计状态 (依赖 viewer, sites, siteCount, operationHistory, generateParams)
const {
  currentLocationName, loading, generating,
  statusText, currentSchemeId, templates, fieldErrors, fieldWarnings,
  updateLocation, handleLocationChange, validateFields, promptProjectId,
  loadDesignData, loadProjectById, showSites, loadLocalGeoJSON, loadTemplates, generateDesign,
  submitToS3Review, submitting, lastSubmittedHash,
  lastReceipt, restoreDraft, clearDraft,
  loadProjectDialogVisible, loadProjectOptions, loadSelectedProjectId,
  loadProjectListLoading, confirmLoadProject, cancelLoadProject,
  deviceLayout,
} = useDesignState({
  viewer, sites, siteCount, generateParams, designInfo, currentLocation,
  clearSites, addSitesToMap, zoomToSites, operationHistory, _safeSetTimeout,
  setHubPoint, setMachineRooms,
})

// ── 本地 GeoJSON 加载 ─────────────────────────────────────
const localGeoJSONInput = ref(null)

function openLocalGeoJSONPicker() {
  localGeoJSONInput.value?.click()
}

async function handleLocalGeoJSONSelected(event) {
  const file = event.target.files?.[0]
  if (!file) return

  try {
    const text = await file.text()
    const geojson = JSON.parse(text)
    const ok = await loadLocalGeoJSON(geojson)
    if (ok) {
      loadProjectDialogVisible.value = false
    }
  } catch (error) {
    ElMessage.error('文件解析失败: ' + (error.message || error))
  } finally {
    // 允许重复选择同一文件
    event.target.value = ''
  }
}

// ── 图例颜色 ──────────────────────────────────────────────
const legendColors = LEGEND_COLORS

// P1: 回执里的类型中文标签
const receiptTypeLabel = computed(() => {
  const map = { macro: '宏站', micro: '微站', indoor: '室内站' }
  return lastReceipt.value ? (map[lastReceipt.value.templateType] || lastReceipt.value.templateType) : ''
})

// P1: 关闭生成回执
function dismissReceipt() {
  lastReceipt.value = null
}

// ── B线: 拓扑引擎设备清单（按站点展开查看） ──
const expandedSiteId = ref(null)
function toggleSiteDevices(siteId) {
  expandedSiteId.value = expandedSiteId.value === siteId ? null : siteId
}
const deviceCountBySite = computed(() => {
  const m = {}
  ;(deviceLayout.value || []).forEach(d => {
    if (d.parentDevice) m[d.parentDevice] = (m[d.parentDevice] || 0) + 1
  })
  return m
})
const expandedDevices = computed(() => {
  const id = expandedSiteId.value
  if (!id) return []
  return (deviceLayout.value || []).filter(d => d.parentDevice === id)
})

// 清除所有站点 + 相关状态（避免回执/设计信息残留）
function handleClearSites() {
  // 先给反馈，确保即使下面 clearSites 抛异常用户也能感知到点击生效了
  ElMessage.info('已清除所有站点')
  try {
    clearSites()
  } catch (e) {
    logger.warn('Design', 'clearSites 异常，已强制复位状态', e)
    // 兜底：实体移除失败时，至少把响应式数据清掉，保证 UI 与状态一致
    sites.value = []
    siteCount.value = 0
  }
  lastReceipt.value = null
  designInfo.value = null
  statusText.value = '就绪'
  clearDraft() // 一并清掉草稿，避免刷新后“复活”
}

// P2: 保存方案为 GeoJSON（不依赖后端，本地直接下载）
function savePlan() {
  if (!sites.value || sites.value.length === 0) {
    ElMessage.warning('当前没有可导出的站点，请先在 QGIS 插件生成方案并加载数据')
    return
  }
  exportAsGeoJSON({ sites: sites.value }, `m03-design-${Date.now()}`)
  ElMessage.success('方案已导出为 GeoJSON 文件')
}

// ── 快捷键帮助 ────────────────────────────────────────────
const showShortcutHelp = () => {
  shortcutManager.showHelp((message, options = {}) => {
    ElMessageBox.alert(message, '快捷键列表', {
      confirmButtonText: '知道了',
      ...options
    })
  })
}

// ── 滚动站点列表 ──────────────────────────────────────────
const scrollList = (direction) => {
  if (!siteListRef.value) return
  const scrollAmount = 200
  if (direction === 'left') {
    siteListRef.value.scrollLeft -= scrollAmount
  } else {
    siteListRef.value.scrollLeft += scrollAmount
  }
  listScrollLeft.value = siteListRef.value.scrollLeft
}

// ── 初始化 Cesium ─────────────────────────────────────────
const initCesium = () => {
  try {
    viewer.value = createViewer('cesiumContainer', {
      animation: false,
      timeline: false,
      baseLayerPicker: false,
      fullscreenButton: false,
      vrButton: false,
      geocoder: false,
      homeButton: true,
      infoBox: true,
      sceneModePicker: false,
      selectionIndicator: true,
      navigationHelpButton: false,
      navigationInstructionsInitiallyVisible: false
    })

    const config = getPresetLocation(currentLocation.value)
    viewer.value.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(
        config.longitude, config.latitude, DEFAULT_LOCATION.cameraHeight
      )
    })

    statusText.value = '就绪'
    cesiumLoading.value = false
  } catch (error) {
    logger.error('Design', 'Cesium初始化失败', error)
    statusText.value = '初始化失败'
    cesiumLoading.value = false
  }
}

// ── 生命周期 ──────────────────────────────────────────────
onMounted(async () => {
  cesiumLoading.value = true
  await nextTick()
  // 等一帧让加载遮罩先绘制，再执行阻塞主线程的 Cesium 初始化
  await new Promise((r) => requestAnimationFrame(() => r()))
  initCesium()
  loadTemplates()
  // 任务列表按当前项目过滤，未加载项目时不预载（避免全局一锅粥）

  // P2: 自动恢复上次生成的草稿（刷新不丢）
  if (viewer.value) {
    const restored = restoreDraft()
    if (restored) {
      addSitesToMap()
      zoomToSites()
      ElMessage.info('已恢复上次生成的草稿方案')
    }
  }

  registerDefaultShortcuts({
    clearSites, zoomToSites, undo, redo,
    toggleLayer, handleLocationChange, showShortcutHelp
  })

  ElMessage.info({
    message: '按 ? 查看快捷键 | 加载数据后可查看覆盖热力图',
    duration: 5000
  })
})

// ── FTTH 叠加层：加载 + 渲染 + 清除 ──────────────────
// FTTH 术语人话化辅助（让点选实体弹出的信息框是中文，而非法语缩写）
function ftthTypeLabel(type) {
  const t = String(type || '').toUpperCase()
  if (t === 'PBO') return 'PBO 入户光节点'
  if (t === 'BPE') return 'BPE 楼栋/路边分光箱'
  if (t === 'SITE' || t === 'PM') return 'PM 小区光汇聚点'
  if (t === 'IMB') return 'IMB 楼栋'
  return type || '未知'
}
function ftthFonctionLabel(f) {
  const t = String(f || '').toUpperCase()
  if (t === 'PBO') return '光纤到户最后一公里'
  if (t === 'BPE') return '楼栋/路边分光'
  if (t === 'PM') return '小区光汇聚'
  return f || '—'
}
function ftthCableLabel(t) {
  const tt = String(t || '').toUpperCase()
  if (tt === 'TRANSPORT') return '干线光缆（局站↔小区）'
  if (tt === 'DISTRIBUTION') return '配线光缆（PM↔分光箱）'
  if (tt === 'DROP') return '入户光缆（分光箱↔用户）'
  return t || '未知'
}
function ftthCoord(lon, lat) {
  const n = Number(lon); const a = Number(lat)
  if (!Number.isFinite(n) || !Number.isFinite(a)) return 'NA'
  return `东经 ${n.toFixed(5)}°, 北纬 ${a.toFixed(5)}°`
}
function ftthBoiteDesc(b) {
  const lon = Math.abs(Number(b.x)) > 90 ? Number(b.y) : Number(b.x)
  const lat = Math.abs(Number(b.x)) > 90 ? Number(b.x) : Number(b.y)
  return `<div style="padding:6px;font-size:12px;line-height:1.7">
    <b>${b.code || '箱体'}</b><br/>
    类型：${ftthTypeLabel(b.type)}<br/>
    功能：${ftthFonctionLabel(b.fonction)}<br/>
    容量：${b.capacite_fo ?? '—'} 芯光纤<br/>
    ${b.logements ? `覆盖户数：${b.logements} 户<br/>` : ''}
    归属汇聚点：${b.pm || 'NA'}<br/>
    工程类型：${b.ptec || 'NA'}<br/>
    地址：${b.adresse || 'NA'}<br/>
    坐标：${ftthCoord(lon, lat)}
  </div>`
}
function ftthSiteDesc(s) {
  return `<div style="padding:6px;font-size:12px;line-height:1.7">
    <b>${s.code || s.id || '局端站点'}</b><br/>
    类型：PM 小区光汇聚点<br/>
    坐标：${ftthCoord(s.x, s.y)}
  </div>`
}
function ftthCableDesc(c) {
  return `<div style="padding:6px;font-size:12px;line-height:1.7">
    <b>${c.code || '光缆'}</b><br/>
    类型：${ftthCableLabel(c.type_cable)}<br/>
    容量：${c.capacite_fo ?? c.capacite ?? '—'} 芯光纤<br/>
    长度：${c.longueur ?? '—'} m<br/>
    归属汇聚点：${c.pm || 'NA'}<br/>
    起点：${c.origine || 'NA'}<br/>
    终点：${c.extremite || 'NA'}
  </div>`
}

const toggleFtthOverlay = async (show) => {
  if (!viewer.value) return

  // 清除已有 FTTH 实体
  for (const e of _ftthEntities) {
    viewer.value.entities.remove(e)
  }
  _ftthEntities = []

  if (!show) {
    console.log('[FTTH] 叠加层已关闭')
    return
  }

  // 加载 FTTH 数据（静态 JSON，与 Ftth.vue 同源）
  try {
    const resp = await fetch(ftthPath('ftth-data.json'))
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    ftthData.value = await resp.json()
    console.log(`[FTTH] 数据已加载: ${ftthData.value.boites?.length || 0} 箱, `
                + `${ftthData.value.cables?.length || 0} 缆, `
                + `${ftthData.value.sites?.length || 0} 站`
                + `${ftthData.value.imbs ? ', ' + ftthData.value.imbs.length + ' 楼栋' : ' (无IMB字段)'}`)
    // 数据结构诊断
    if (ftthData.value.sites?.[0]) {
      const s = ftthData.value.sites[0]
      console.log(`[FTTH] sites[0] 坐标: x=${s.x}, y=${s.y} → 判定为 ${Math.abs(s.x) > 90 ? 'x=纬度(需交换)' : 'x=经度(正常)'}`)
    }
    if (ftthData.value.cables?.[0]) {
      const c = ftthData.value.cables[0]
      console.log(`[FTTH] cables[0] from=${JSON.stringify(c.from)} to=${JSON.stringify(c.to)}`)
    }
  } catch (e) {
    console.warn('[FTTH] 数据加载失败:', e.message)
    ElMessage.warning('FTTH 数据不可用，请确认 datasets 目录存在')
    showFtth.value = false
    return
  }

  const d = ftthData.value
  if (!d) return

  // 颜色体系（艳色/高饱和，在暗色卫星底图上醒目）
  const C_FTTH = {
    PBO: Cesium.Color.fromCssColorString('#00d4ff'),   // 终端箱 - 艳青
    BPE: Cesium.Color.fromCssColorString('#ff8c00'),   // 分支箱 - 艳橙
    SITE: Cesium.Color.fromCssColorString('#ffd700'),   // PM 站点 - 艳金
    IMB: Cesium.Color.fromCssColorString('#ff3eb5'),    // 楼栋 - 艳粉
    CABLE_PM1: Cesium.Color.fromCssColorString('#1e90ff'),
    CABLE_PM2: Cesium.Color.fromCssColorString('#a020f0'),
    CABLE_TRANS: Cesium.Color.fromCssColorString('#00e676'),
  }

  // 1. PM/SITE 站点（浅色小圆点，无柱/无标签）
  for (const s of (d.sites || [])) {
    if (s.x == null || s.y == null) continue
    const lon = Math.abs(s.x) > 90 ? s.y : s.x   // x>90 说明 x 是纬度
    const lat = Math.abs(s.x) > 90 ? s.x : s.y
    _ftthEntities.push(viewer.value.entities.add({
      position: Cesium.Cartesian3.fromDegrees(lon, lat, 0),
      ftthKind: 'site',
      description: ftthSiteDesc(s),
      point: { pixelSize: 7, color: C_FTTH.SITE.withAlpha(0.95),
               outlineColor: Cesium.Color.WHITE.withAlpha(0.3), outlineWidth: 1,
               disableDepthTestDistance: Number.POSITIVE_INFINITY },
    }))
  }

  // 2. 光交箱 BOITE（浅色小圆点，无柱/无标签）
  for (const b of (d.boites || [])) {
    if (b.x == null || b.y == null) continue
    const color = C_FTTH[b.type] || Cesium.Color.WHITE
    _ftthEntities.push(viewer.value.entities.add({
      position: Cesium.Cartesian3.fromDegrees(b.x, b.y, 0),
      ftthKind: 'boite',
      boiteData: b,
      description: ftthBoiteDesc(b),
      point: { pixelSize: 5, color: color.withAlpha(0.95),
               outlineColor: Cesium.Color.WHITE.withAlpha(0.25), outlineWidth: 1,
               disableDepthTestDistance: Number.POSITIVE_INFINITY },
    }))
  }

  // 3. IMB 楼栋点（粉色小点，若有）
  for (const imb of (d.imbs || [])) {
    if (imb.x == null || imb.y == null) continue
    _ftthEntities.push(viewer.value.entities.add({
      position: Cesium.Cartesian3.fromDegrees(imb.x, imb.y, 50),
      ftthKind: 'imb',
      description: `<div style="padding:6px;font-size:12px;line-height:1.7"><b>${imb.code || imb.id || '楼栋'}</b><br/>类型：IMB 楼栋<br/>角色：承载入户光节点（PBO）的建筑</div>`,
      point: { pixelSize: 6, color: C_FTTH.IMB.withAlpha(0.95),
               outlineColor: Cesium.Color.WHITE, outlineWidth: 1 },
    }))
  }

  // 4. 光缆连线（发光折线）
  // 注意：ftth-data.json 中 cables.from 是 [纬度, 经度]，cables.to 是 [经度, 纬度]
  for (const c of (d.cables || [])) {
    const f = c.from
    const t = c.to
    if (!f || !t) continue
    const isTrans = (c.type_cable || '') === 'TRANSPORT'
    const cableColor = isTrans ? C_FTTH.CABLE_TRANS
      : (c.pm === 'JAD-MAR-0002' ? C_FTTH.CABLE_PM2 : C_FTTH.CABLE_PM1)
    // 自动检测 from/to 坐标顺序：若第一个值 > 90 则为纬度（经度范围 ±180，纬度范围 ±90）
    const fLon = Math.abs(f[0]) > 90 ? f[1] : f[0]
    const fLat = Math.abs(f[0]) > 90 ? f[0] : f[1]
    const tLon = Math.abs(t[0]) > 90 ? t[1] : t[0]
    const tLat = Math.abs(t[0]) > 90 ? t[0] : t[1]
    _ftthEntities.push(viewer.value.entities.add({
      ftthKind: 'cable',
      cableData: c,
      description: ftthCableDesc(c),
      polyline: {
        positions: [
          Cesium.Cartesian3.fromDegrees(fLon, fLat, 0),
          Cesium.Cartesian3.fromDegrees(tLon, tLat, 0),
        ],
        width: isTrans ? 2 : 1.5,
        material: new Cesium.PolylineGlowMaterialProperty({
          glowPower: 0.15, color: cableColor.withAlpha(0.8),
        }),
        arcType: Cesium.ArcType.GEODESIC,
      },
    }))
  }

  // 局端站点(SITE/PM)只连最近的一个机房，只画一条线（与 QGIS 插件一致）
  // sites 坐标 x/y 若 x>90 则 x 为纬度，需交换；与 boites 归一化逻辑一致
  const ftthPointColor = Cesium.Color.fromCssColorString('#00d4ff')
  const rooms = machineRooms.value && machineRooms.value.length > 0 ? machineRooms.value : []
  if (rooms.length > 0 && (d.sites || []).length > 0) {
    const linkTargets = []
    for (const s of d.sites) {
      if (s.x == null || s.y == null) continue
      const isLatLonSwap = Math.abs(s.x) > 90
      const sLon = isLatLonSwap ? s.y : s.x
      const sLat = isLatLonSwap ? s.x : s.y
      linkTargets.push({ lon: sLon, lat: sLat, type: 'SITE', name: s.code || s.id || '局端站点' })
    }
    // 所有 SITE-机房对中只保留距离最近的一对，只画一条线
    let best = null
    for (const p of linkTargets) {
      const room = findNearestRoom ? findNearestRoom(p.lon, p.lat) : null
      if (!room) continue
      const dLon = p.lon - Number(room.longitude ?? room.lon)
      const dLat = p.lat - Number(room.latitude ?? room.lat)
      const dist = Math.sqrt(dLon * dLon + dLat * dLat)
      if (!best || dist < best.dist) best = { p, room, dist }
    }
    if (best) {
      const { p, room } = best
      const rLon = Number(room.longitude ?? room.lon)
      const rLat = Number(room.latitude ?? room.lat)
      _ftthEntities.push(viewer.value.entities.add({
        ftthKind: 'ftth-room-link',
        polyline: {
          positions: [
            Cesium.Cartesian3.fromDegrees(p.lon, p.lat, 0),
            Cesium.Cartesian3.fromDegrees(rLon, rLat, 0),
          ],
          width: 1.5,
          material: new Cesium.PolylineDashMaterialProperty({
            color: ftthPointColor.withAlpha(0.75),
            dashLength: 8,
          }),
          clampToGround: true,
        },
        description: `<div style="padding:4px;font-size:12px"><b>${p.name}</b><br/>类型: ${p.type}<br/>上联: ${room.name || '机房'}</div>`,
      }))
    }
  }

  // 缩放到包含 FTTH 数据的范围
  if (d.boites?.length || d.sites?.length) {
    let minLon = Infinity, minLat = Infinity, maxLon = -Infinity, maxLat = -Infinity
    // 自动归一化 (lon, lat)
    const norm = (x, y) => {
      if (x == null || y == null) return null
      return Math.abs(x) > 90 ? [y, x] : [x, y]  // x>90 → x 是纬度，交换
    }
    const consider = (x, y) => {
      const p = norm(x, y)
      if (!p) return
      minLon = Math.min(minLon, p[0]); maxLon = Math.max(maxLon, p[0])
      minLat = Math.min(minLat, p[1]); maxLat = Math.max(maxLat, p[1])
    }
    for (const b of (d.boites || [])) consider(b.x, b.y)
    for (const s of (d.sites || [])) consider(s.x, s.y)
    if (isFinite(minLon)) {
      viewer.value.camera.flyTo({
        destination: Cesium.Rectangle.fromDegrees(
          minLon - 0.01, minLat - 0.01, maxLon + 0.01, maxLat + 0.01
        ),
        duration: 1.5,
      })
    }
  }

  ElMessage.success(`FTTH 叠加: ${(d.boites || []).length} 箱 + ${(d.cables || []).length} 缆 + ${(d.sites || []).length} 站`)
}

onUnmounted(() => {
  // 清理定时器
  _timers.forEach(id => clearTimeout(id))
  _timers.length = 0
  cleanupProject()

  // 清理动画事件
  cleanupAnimation()

  // 清理站点实体
  cleanupEntities()

  // 清理 FTTH 叠加实体
  if (viewer.value) {
    for (const e of _ftthEntities) viewer.value.entities.remove(e)
    _ftthEntities = []
  }

  // 销毁 Viewer
  if (viewer.value) {
    viewer.value.destroy()
    viewer.value = null
  }

  // 销毁快捷键管理器
  shortcutManager.destroy()
})
</script>

<!-- 非scoped: CSS自定义属性必须设在 :root 上，scoped会给选择器加 [data-v-xxx]
     导致 :root[data-v-xxx] 永远不匹配 <html>，变量全部失效 -->
<style>
/* ── 全局CSS变量（布局尺寸） ──────────────────────────────── */
:root {
  --panel-left-width: 240px;
  --panel-right-width: 240px;
  --panel-bottom-height: 160px;
  --panel-top-offset: 92px;
}
@media (max-width: 1366px) {
  :root {
    --panel-left-width: 210px;
    --panel-right-width: 200px;
    --panel-bottom-height: 130px;
  }
}
@media (max-width: 1024px) {
  :root {
    --panel-left-width: 0px;
    --panel-right-width: 0px;
    --panel-bottom-height: 120px;
  }
}

/* ── 加载数据：项目选择弹窗（居中显眼） ─────────────────── */
.load-project-dialog .el-dialog__title {
  font-weight: 600;
}
.load-project-body {
  padding: 4px 2px;
}
.load-project-tip {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0 0 14px;
  font-size: 14px;
  color: var(--el-text-color-regular, #606266);
}
.load-project-tip .el-icon {
  color: var(--el-color-primary, #409eff);
  font-size: 16px;
}
.load-project-empty {
  margin: 12px 0 0;
  font-size: 13px;
  color: var(--el-color-warning, #e6a23c);
}
.load-project-local {
  margin-top: 8px;
  text-align: center;
}
.load-project-local .el-divider {
  margin: 18px 0 14px;
  font-size: 12px;
  color: var(--el-text-color-secondary, #909399);
}
.load-project-local .el-button {
  width: 100%;
}
</style>

<style scoped>
/* ================================================================
   M03 Design View — 暗色科技主题 (统一 global.css 设计系统)
   ================================================================ */

.design-visualization {
  width: 100%;
  height: 100%;
  position: relative;
  font-family: var(--font-sans, 'Microsoft YaHei', sans-serif);
}

/* ── 响应式布局变量（已移至非scoped style块的 :root 中） ──── */

/* ── 顶部工具栏 ──────────────────────────────────────────── */
.top-bar {
  position: absolute;
  top: 0;
  left: 0;
  right: 150px;
  z-index: 1000;
  background: var(--bg-glass, rgba(10, 15, 26, 0.92));
  padding: 6px 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--border-color, rgba(0, 212, 255, 0.15));
  border-radius: 0 0 8px 0;
}

.toolbar-left {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}

.toolbar-divider {
  display: inline-block;
  width: 1px;
  height: 22px;
  background: var(--border-color, rgba(0, 212, 255, 0.25));
  margin: 0 4px;
  flex: 0 0 auto;
}

.toolbar-center {
  flex: 1;
  display: flex;
  justify-content: center;
}

.toolbar-right {
  display: flex;
  gap: 12px;
  align-items: center;
  color: var(--text-primary, #fff);
  font-size: 12px;
}

/* ── 状态信息 ────────────────────────────────────────────── */
.status-info {
  position: absolute;
  bottom: 12px;
  left: calc(var(--panel-left-width) + 20px);
  z-index: 1000;
  background: var(--bg-glass, rgba(10, 15, 26, 0.85));
  color: var(--text-primary, #fff);
  padding: 6px 12px;
  border-radius: var(--radius-sm, 4px);
  font-size: 12px;
  display: flex;
  gap: 15px;
  border: 1px solid var(--border-color, rgba(0, 212, 255, 0.12));
}

.site-count {
  background: var(--primary-color, #00d4ff);
  color: #0a0f1a;
  padding: 2px 8px;
  border-radius: var(--radius-sm, 4px);
  font-weight: 600;
}

.status-text {
  color: var(--text-muted, #7f8c8d);
}

/* ── 位置选择器 ──────────────────────────────────────────── */
.location-selector {
  background: rgba(72, 149, 239, 0.25);
  padding: 2px 10px;
  border-radius: var(--radius-sm, 4px);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: var(--text-primary, #fff);
  transition: all 0.3s;
  border: 1px solid rgba(72, 149, 239, 0.3);
}

.location-selector:hover {
  background: rgba(72, 149, 239, 0.4);
  border-color: rgba(72, 149, 239, 0.6);
  transform: scale(1.05);
}

/* ── 面板布局 (响应式) ───────────────────────────────────── */
.left-panel {
  position: absolute;
  top: var(--panel-top-offset);
  left: 10px;
  bottom: 10px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 8px;          /* 区块间距压缩 */
  width: var(--panel-left-width);
  overflow-y: auto;
  padding: 0 4px 8px 0; /* 上边距由 top 控制 */
  /* 细滚动条 */
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 212, 255, 0.3) transparent;
}

.right-panel {
  position: absolute;
  top: var(--panel-top-offset);
  right: 10px;
  bottom: 10px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: var(--panel-right-width);
  overflow-y: auto;
  padding-right: 4px;
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 212, 255, 0.3) transparent;
}

/* ── WebKit 细滚动条（Chrome / Edge） ─────────────────────── */
.left-panel::-webkit-scrollbar,
.right-panel::-webkit-scrollbar {
  width: 4px;
}
.left-panel::-webkit-scrollbar-track,
.right-panel::-webkit-scrollbar-track {
  background: transparent;
}
.left-panel::-webkit-scrollbar-thumb,
.right-panel::-webkit-scrollbar-thumb {
  background: rgba(0, 212, 255, 0.3);
  border-radius: 2px;
}
.left-panel::-webkit-scrollbar-thumb:hover,
.right-panel::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 212, 255, 0.5);
}

/* ── 面板通用 — 暗色主题（紧凑版） ───────────────────────── */
.panel-section {
  background: var(--bg-glass, rgba(10, 15, 26, 0.92));
  border: 1px solid var(--border-color, rgba(0, 212, 255, 0.12));
  border-radius: var(--radius-md, 6px);   /* 圆角微缩 */
  box-shadow: var(--shadow-md, 0 2px 8px rgba(0, 0, 0, 0.3));
  overflow: hidden;
  backdrop-filter: blur(8px);
}

.panel-title {
  background: var(--bg-tertiary, #1a2a4a);
  color: var(--primary-color, #00d4ff);
  padding: 6px 10px;       /* 压缩：8→6 */
  font-size: 12px;         /* 压缩：13→12 */
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 5px;               /* 压缩：6→5 */
  border-bottom: 1px solid var(--border-glow, rgba(0, 212, 255, 0.18));
}

/* P1: 左侧分组可折叠 —— 标题可点击 + 右侧旋转 chevron */
.panel-title-clickable { cursor: pointer; user-select: none; }
.panel-chevron { margin-left: auto; transition: transform 0.2s; font-size: 16px; }
.panel-chevron.is-collapsed { transform: rotate(-90deg); }

/* B 项：顶部状态条（统计信息上移） */
.top-status-bar {
  position: absolute;
  top: 52px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1000;
  display: flex;
  gap: 18px;
  align-items: center;
  background: var(--bg-glass, rgba(10, 15, 26, 0.92));
  border: 1px solid var(--border-color, rgba(0, 212, 255, 0.15));
  border-radius: var(--radius-md, 6px);
  padding: 5px 16px;
  backdrop-filter: blur(10px);
  box-shadow: var(--shadow-md, 0 2px 8px rgba(0, 0, 0, 0.3));
  font-size: 12px;
  color: var(--text-secondary, #b0bec5);
  white-space: nowrap;
}
.top-status-bar .stat-item { display: flex; align-items: baseline; gap: 5px; }
.top-status-bar .stat-label { color: var(--text-muted, #7f8c8d); }
.top-status-bar .stat-val { font-weight: 700; color: var(--text-primary, #fff); font-size: 14px; }
.top-status-bar .stat-val.success { color: var(--success-color, #67c23a); }
.top-status-bar .stat-val.danger { color: var(--danger-color, #f56c6c); }
.top-status-bar .stat-sep { width: 1px; height: 16px; background: var(--border-color, rgba(0, 212, 255, 0.2)); }

/* A/E 项：组内次级标题（暗色主题，复用既有变量） */
.sub-group-title {
  margin: 10px 0 6px;
  padding: 4px 0;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted, #7f8c8d);
  border-top: 1px dashed var(--border-color, rgba(0, 212, 255, 0.18));
  letter-spacing: .5px;
}
/* 组内首个次级标题紧贴面板标题，去掉上边框避免双分隔 */
.panel-content > .sub-group-title:first-child {
  border-top: none;
  margin-top: 0;
}

.panel-content {
  padding: 8px 10px;       /* 压缩：10→8, 12→10 */
  color: var(--text-secondary, #b0bec5);
}

/* ── 面板内容：右侧始终显示滚动条 ─────────────────── */
.panel-content.panel-scroll {
  max-height: 22vh;       /* 缩小：确保每个面板都有可拖动的滚动条滑块 */
  overflow-y: scroll;     /* 始终显示滚动条轨道 */
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 212, 255, 0.55) rgba(0, 212, 255, 0.12);
}

/* ── 设计任务列表 ── */
.task-total-badge {
  margin-left: 4px;
  font-size: 10px;
  line-height: 1.4;
  padding: 0 6px;
  border-radius: 8px;
  background: rgba(0, 212, 255, 0.18);
  color: #00d4ff;
}
.task-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 2px;
}
.task-empty {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.45);
  text-align: center;
  padding: 10px 0;
}
.task-item {
  border: 1px solid rgba(0, 212, 255, 0.18);
  border-radius: 6px;
  padding: 6px 8px;
  margin-bottom: 6px;
  transition: border-color 0.2s;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.task-item:hover {
  border-color: rgba(0, 212, 255, 0.55);
}
.task-item-current {
  border-color: rgba(0, 212, 255, 0.85);
  background: rgba(0, 212, 255, 0.08);
  box-shadow: 0 0 0 1px rgba(0, 212, 255, 0.35) inset;
}
.task-item-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}
.task-item-name {
  font-size: 12px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.88);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.task-item-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  font-size: 11px;
}
.task-item-no {
  color: rgba(0, 212, 255, 0.7);
  font-family: ui-monospace, Menlo, Consolas, monospace;
}
.task-item-time {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
  margin-left: auto;
}
.task-item-actions {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  border-top: 1px dashed rgba(0, 212, 255, 0.12);
  padding-top: 4px;
  margin-top: 2px;
}
.task-item-actions .el-button {
  padding: 2px 6px;
  font-size: 11px;
}
.panel-content.panel-scroll::-webkit-scrollbar {
  width: 8px;             /* 加宽：方便鼠标拖拽 */
}
.panel-content.panel-scroll::-webkit-scrollbar-track {
  background: rgba(0, 212, 255, 0.08);   /* 轨道可见 */
  border-radius: 4px;
}
.panel-content.panel-scroll::-webkit-scrollbar-thumb {
  background: rgba(0, 212, 255, 0.55);
  border-radius: 4px;
}
.panel-content.panel-scroll::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 212, 255, 0.8);
}

/* ── 图层控制（紧凑） ────────────────────────────────────── */
.panel-content .el-checkbox {
  display: block;
  margin-bottom: 4px;       /* 压缩：6→4 */
  font-size: 12px;
}

.slider-row {
  display: flex;
  align-items: center;
  gap: 6px;                /* 压缩：8→6 */
  margin-top: 6px;         /* 压缩：8→6 */
  font-size: 11px;         /* 压缩：12→11 */
  color: var(--text-secondary, #b0bec5);
}

/* ── 参数化设计表单（紧凑） ──────────────────────────────── */
.form-item {
  margin-bottom: 6px;      /* 压缩：8→6 */
}

.form-label {
  font-size: 11px;         /* 保持紧凑 */
  color: var(--text-muted, #7f8c8d);
  display: block;
  margin-bottom: 2px;      /* 压缩：4→2 */
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ── 验证错误提示（紧凑） ────────────────────────────────── */
.validation-errors {
  background: rgba(245, 108, 108, 0.12);
  border: 1px solid var(--danger-color, #f56c6c);
  border-radius: var(--radius-sm, 4px);
  padding: 5px 8px;        /* 压缩 */
  margin: 6px 0;
  font-size: 10px;
  color: var(--danger-color, #f56c6c);
  line-height: 1.5;
}

.validation-warnings {
  background: rgba(230, 162, 60, 0.12);
  border: 1px solid var(--warning-color, #e6a23c);
  border-radius: var(--radius-sm, 4px);
  padding: 5px 8px;
  margin: 6px 0;
  font-size: 10px;
  color: var(--warning-color, #e6a23c);
  line-height: 1.5;
}

/* ── 图例（紧凑） ────────────────────────────────────────── */
.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;                /* 压缩：8→6 */
  margin-bottom: 4px;      /* 压缩：6→4 */
  font-size: 11px;         /* 压缩：12→11 */
  color: var(--text-primary, #fff);
}

.legend-dot {
  width: 12px;             /* 压缩：14→12 */
  height: 12px;
  border-radius: 2px;      /* 压缩：3→2 */
  border: 1px solid var(--border-color, rgba(0, 212, 255, 0.2));
  flex-shrink: 0;
}

.legend-divider {
  height: 1px;
  background: var(--border-color, rgba(0, 212, 255, 0.12));
  margin: 5px 0;           /* 压缩：8→5 */
}

/* ── 信息行（紧凑） ──────────────────────────────────────── */
.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;      /* 压缩：6→4 */
  font-size: 11px;         /* 压缩：12→11 */
}

.info-row .label {
  color: var(--text-muted, #7f8c8d);
}

.info-row .value {
  color: var(--text-primary, #fff);
  font-weight: 500;
}

.info-row .value.success {
  color: var(--success-color, #67c23a);
}

.info-row .value.danger {
  color: var(--danger-color, #f56c6c);
}

/* ── RSRP 颜色 ───────────────────────────────────────────── */
.rsrp-excellent { color: #00cc00 !important; font-weight: bold; }
.rsrp-good      { color: #aacc00 !important; }
.rsrp-fair      { color: #ff8800 !important; }
.rsrp-poor      { color: #ff3333 !important; font-weight: bold; }

/* ── 操作按钮 ────────────────────────────────────────────── */
.action-buttons {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

.close-btn {
  margin-left: auto;
  color: var(--text-primary, #fff);
}

/* ── 底部站点列表 ────────────────────────────────────────── */
.bottom-panel {
  position: absolute;
  bottom: 10px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1000;
  background: var(--bg-glass, rgba(10, 15, 26, 0.92));
  border: 1px solid var(--border-color, rgba(0, 212, 255, 0.12));
  border-radius: var(--radius-md, 8px);
  box-shadow: var(--shadow-md, 0 4px 16px rgba(0, 0, 0, 0.3));
  width: min(650px, calc(100vw - var(--panel-left-width) - var(--panel-right-width) - 40px));
  max-height: var(--panel-bottom-height);
  backdrop-filter: blur(8px);
}

.bottom-panel .panel-title {
  padding: 6px 12px;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.list-controls {
  display: flex;
  gap: 4px;
}

.site-list-container {
  display: flex;
  align-items: center;
  padding: 8px;
  gap: 4px;
}

.scroll-btn {
  width: 30px;
  height: 60px;
  padding: 0;
  flex-shrink: 0;
}

.scroll-left  { border-radius: 4px 0 0 4px; }
.scroll-right { border-radius: 0 4px 4px 0; }

.site-list-scroll {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  max-height: 100px;
  flex: 1;
  scroll-behavior: smooth;
}

.site-list-scroll::-webkit-scrollbar { height: 6px; }
.site-list-scroll::-webkit-scrollbar-thumb {
  background: var(--border-color, rgba(0, 212, 255, 0.2));
  border-radius: 3px;
}
.site-list-scroll::-webkit-scrollbar-track {
  background: var(--bg-secondary, #0d1b2a);
  border-radius: 3px;
}

.site-card {
  min-width: 120px;
  padding: 6px 10px;
  background: var(--bg-secondary, #0d1b2a);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid var(--border-color, rgba(0, 212, 255, 0.1));
}

.site-card:hover {
  background: var(--bg-tertiary, #1a2a4a);
  border-color: var(--primary-color, #00d4ff);
  box-shadow: var(--shadow-glow, 0 0 8px rgba(0, 212, 255, 0.2));
}

.site-card.active {
  background: var(--bg-tertiary, #1a2a4a);
  border-color: var(--primary-color, #00d4ff);
  box-shadow: var(--shadow-glow, 0 0 12px rgba(0, 212, 255, 0.3));
}

.site-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.site-id {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary, #fff);
}

.site-card-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.rsrp {
  font-size: 11px;
  font-weight: 500;
}

.coords {
  font-size: 10px;
  color: var(--text-muted, #7f8c8d);
}

/* B线: 站点卡片底部「设备清单」展开入口 + 设备列表 */
.site-card-footer {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 4px;
  padding-top: 4px;
  border-top: 1px dashed var(--border-color, #2a3a4d);
  font-size: 11px;
  color: var(--accent, #4aa3ff);
  cursor: pointer;
  user-select: none;
}
.site-card-footer:hover { color: var(--accent-hover, #6fb6ff); }
.site-devices {
  margin-top: 4px;
  padding: 4px 6px;
  background: var(--bg-elevated, rgba(255,255,255,0.04));
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-height: 120px;
  overflow-y: auto;
}
.site-device-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 10px;
  line-height: 1.4;
}
.dev-name { color: var(--text-primary, #e6f1ff); font-weight: 500; }
.dev-type { color: var(--text-muted, #7f8c8d); }
.dev-az { color: var(--accent, #4aa3ff); margin-left: auto; }

/* ── 布局辅助类 ──────────────────────────────────────────── */
.form-full-width { width: 100%; }
.form-mt-8 { margin-top: 6px; }   /* 压缩：8→6 */
.search-input { width: 200px; }
.filter-select { width: 80px; }
.slider-width { width: 100px; }
.location-dropdown { margin-left: 10px; }

/* ── Cesium容器 ──────────────────────────────────────────── */
.cesium-container {
  width: 100%;
  height: 100%;
}

/* P0: 生成中遮罩（地图可见加载态） */
.map-loading-overlay {
  position: absolute;
  inset: 0;
  z-index: 1500;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  background: rgba(8, 18, 32, 0.62);
  color: var(--text-primary, #e6f1ff);
  font-size: 14px;
  backdrop-filter: blur(2px);
}
.map-loading-spinner {
  width: 38px;
  height: 38px;
  border: 3px solid rgba(0, 212, 255, 0.25);
  border-top-color: var(--primary-color, #00d4ff);
  border-radius: 50%;
  animation: m03-spin 0.9s linear infinite;
}
@keyframes m03-spin {
  to { transform: rotate(360deg); }
}

/* P1: 生成回执横幅 */
.gen-receipt {
  position: absolute;
  top: 56px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 900;
  pointer-events: none; /* 双保险：即使视觉上与其他层重叠也绝不吞掉点击 */
  max-width: 90%;
  background: var(--bg-secondary, #0d1b2a);
  border: 1px solid var(--primary-color, #00d4ff);
  border-radius: 10px;
  padding: 10px 38px 10px 14px;
  box-shadow: var(--shadow-glow, 0 0 14px rgba(0, 212, 255, 0.25));
  color: var(--text-primary, #e6f1ff);
  font-size: 13px;
}
.gen-receipt-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  color: var(--primary-color, #00d4ff);
  margin-bottom: 6px;
}
.gen-receipt-source {
  margin-left: 6px;
}
.gen-receipt-body {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 14px;
  color: var(--text-secondary, #9fb3c8);
}
.gen-receipt-close {
  position: absolute;
  top: 6px;
  right: 8px;
  border: none;
  background: transparent;
  color: var(--text-muted, #6b7d92);
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
}
.gen-receipt-close:hover {
  color: var(--text-primary, #e6f1ff);
}

/* ── 响应式（:root 变量已移至非scoped style块） ─────────── */
@media (max-width: 1024px) {
  .left-panel, .right-panel { display: none; }
}
</style>
