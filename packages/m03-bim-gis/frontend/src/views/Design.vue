<template>
  <div class="design-page" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
    <!-- 背景粒子效果 -->
    <div class="bg-particles">
      <div v-for="i in 30" :key="i" class="particle" :style="getParticleStyle(i)"></div>
    </div>

    <!-- 顶部悬浮工具栏 -->
    <header class="toolbar">
      <div class="toolbar-left">
        <div class="logo-section">
          <div class="logo-icon">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
              <path d="M2 17L12 22L22 17" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
              <path d="M2 12L12 17L22 12" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
            </svg>
          </div>
          <div class="logo-text">
            <span class="logo-title">M03 BIM+GIS</span>
            <span class="logo-subtitle">三维设计引擎</span>
          </div>
        </div>

        <div class="mode-switch">
          <button
            class="mode-btn"
            :class="{ active: mapMode === '3D' }"
            @click="toggleMapMode('3D')"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
            </svg>
            <span>3D 地图</span>
          </button>
          <button
            class="mode-btn"
            :class="{ active: mapMode === 'STATION' }"
            @click="toggleMapMode('STATION')"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="4" y="2" width="16" height="20" rx="2"/>
              <path d="M12 6v4M8 10h8M12 14v4"/>
            </svg>
            <span>基站环境</span>
          </button>
        </div>
      </div>

      <div class="toolbar-center">
        <div class="status-indicators">
          <div class="status-item" v-if="selectedStation">
            <span class="status-dot active"></span>
            <span class="status-text">{{ selectedStation.name }}</span>
          </div>
          <div class="status-item" v-if="mapMode === 'STATION'">
            <span class="status-dot warning"></span>
            <span class="status-text">天线: {{ stationAntennas.length }}</span>
          </div>
          <div class="status-item">
            <span class="status-dot info"></span>
            <span class="status-text">{{ mapMode === '3D' ? '地图模式' : '基站模式' }}</span>
          </div>
        </div>
      </div>

      <div class="toolbar-right">
        <button class="tool-btn" @click="zoomIn" title="放大">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35M11 8v6M8 11h6"/>
          </svg>
        </button>
        <button class="tool-btn" @click="zoomOut" title="缩小">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35M8 11h6"/>
          </svg>
        </button>
        <button class="tool-btn" @click="resetView" title="复位视角">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
            <path d="M3 3v5h5"/>
          </svg>
        </button>
        <div class="toolbar-divider"></div>
        <button class="tool-btn" :class="{ active: addMode }" @click="toggleAddMode" title="添加设备">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/><path d="M12 8v8M8 12h8"/>
          </svg>
        </button>
        <button class="tool-btn" v-if="mapMode === 'STATION'" @click="backToMap" title="返回地图">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 12H5M12 19l-7-7 7-7"/>
          </svg>
        </button>
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="main-content">
      <!-- 侧边栏 -->
      <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
        <button class="sidebar-toggle" @click="sidebarCollapsed = !sidebarCollapsed">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path v-if="!sidebarCollapsed" d="M15 18l-6-6 6-6"/>
            <path v-else d="M9 18l6-6-6-6"/>
          </svg>
        </button>

        <div class="sidebar-content" v-show="!sidebarCollapsed">
          <!-- 3D 模式：设备列表 -->
          <div v-if="mapMode === '3D'" class="sidebar-section">
            <div class="section-header">
              <h3>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
                  <circle cx="12" cy="10" r="3"/>
                </svg>
                设备列表
              </h3>
              <span class="device-count">{{ filteredDevices.length }}</span>
            </div>

            <div class="search-box">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
              </svg>
              <input v-model="searchKeyword" placeholder="搜索设备名称..." />
            </div>

            <div class="device-list">
              <div
                v-for="device in filteredDevices"
                :key="device.id"
                class="device-card"
                @click="locateDevice(device)"
              >
                <div class="device-card-header">
                  <div class="device-icon" :style="{ background: getDeviceColor(device.coverage) }">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M5.12 19.18A10 10 0 0 1 2 12C2 6.48 6.48 2 12 2s10 4.48 10 10a10 10 0 0 1-3.12 7.18"/>
                      <path d="M8.46 15.54A5 5 0 0 1 7 12a5 5 0 0 1 10 0 5 5 0 0 1-1.46 3.54"/>
                      <circle cx="12" cy="12" r="1"/>
                    </svg>
                  </div>
                  <div class="device-info">
                    <span class="device-name">{{ device.name }}</span>
                    <span class="device-type">{{ device.placeType }}</span>
                  </div>
                  <div class="device-coverage" :style="{ color: getDeviceColor(device.coverage) }">
                    {{ device.coverage }}%
                  </div>
                </div>
                <div class="device-card-body">
                  <div class="device-meta">
                    <span class="meta-item">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
                        <circle cx="12" cy="10" r="3"/>
                      </svg>
                      {{ device.area }}
                    </span>
                    <span class="meta-item">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
                      </svg>
                      {{ device.rsrp }} dBm
                    </span>
                  </div>
                  <div class="device-actions">
                    <button class="action-btn locate" @click.stop="locateDevice(device)" title="定位">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/>
                      </svg>
                    </button>
                    <button class="action-btn enter" @click.stop="enterStation(device)" title="进入基站">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4M10 17l5-5-5-5M15 12H3"/>
                      </svg>
                    </button>
                    <button class="action-btn delete" @click.stop="deleteDevice(device)" title="删除">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                      </svg>
                    </button>
                  </div>
                </div>
              </div>

              <div v-if="filteredDevices.length === 0" class="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
                  <circle cx="12" cy="10" r="3"/>
                </svg>
                <p>暂无设备数据</p>
                <span>点击上方 + 按钮添加设备</span>
              </div>
            </div>
          </div>

          <!-- 基站模式：标签页 -->
          <div v-if="mapMode === 'STATION'" class="sidebar-section">
            <div class="tab-switcher">
              <button
                v-for="tab in tabs"
                :key="tab.id"
                class="tab-btn"
                :class="{ active: activeTab === tab.id }"
                @click="activeTab = tab.id"
              >
                <component :is="tab.icon" />
                <span>{{ tab.label }}</span>
              </button>
            </div>

            <!-- 基站管理 -->
            <div v-if="activeTab === 'stations'" class="tab-content">
              <div class="search-box">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
                </svg>
                <input v-model="searchKeyword" placeholder="搜索基站名称..." />
              </div>

              <div class="station-list">
                <div
                  v-for="station in nearbyStations"
                  :key="station.id"
                  class="station-card"
                  :class="{ active: selectedStation?.id === station.id }"
                  @click="switchStation(station)"
                >
                  <div class="station-card-header">
                    <div class="station-icon">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="4" y="2" width="16" height="20" rx="2"/>
                        <path d="M12 6v4M8 10h8M12 14v4"/>
                      </svg>
                    </div>
                    <div class="station-info">
                      <span class="station-name">{{ station.name }}</span>
                      <span class="station-coord">{{ station.lng.toFixed(6) }}, {{ station.lat.toFixed(6) }}</span>
                    </div>
                  </div>
                  <div class="station-actions">
                    <button class="action-btn edit" @click.stop="editStation(station)">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                      </svg>
                    </button>
                    <button class="action-btn delete" @click.stop="deleteBaseStation(station)">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                      </svg>
                    </button>
                  </div>
                </div>
              </div>

              <button class="add-btn" @click="handleAddBaseStationClick">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"/><path d="M12 8v8M8 12h8"/>
                </svg>
                <span>添加基站模型</span>
              </button>
            </div>

            <!-- 天线设备 -->
            <div v-if="activeTab === 'antennas'" class="tab-content">
              <div class="search-box">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
                </svg>
                <input v-model="antennaKeyword" placeholder="搜索天线名称..." />
              </div>

              <div class="antenna-list">
                <div
                  v-for="antenna in filteredAntennas"
                  :key="antenna.id"
                  class="antenna-card"
                >
                  <div class="antenna-card-header">
                    <div class="antenna-icon" :style="{ background: getAntennaColor(antenna.type) }">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M5.12 19.18A10 10 0 0 1 2 12C2 6.48 6.48 2 12 2s10 4.48 10 10a10 10 0 0 1-3.12 7.18"/>
                        <path d="M8.46 15.54A5 5 0 0 1 7 12a5 5 0 0 1 10 0 5 5 0 0 1-1.46 3.54"/>
                        <circle cx="12" cy="12" r="1"/>
                      </svg>
                    </div>
                    <div class="antenna-info">
                      <div class="antenna-header">
                        <span class="antenna-name">{{ antenna.name }}</span>
                        <span class="antenna-badge" :class="getAntennaTypeClass(antenna.type)">
                          {{ antenna.type }}
                        </span>
                      </div>
                      <span class="antenna-coord">X:{{ antenna.x }} Y:{{ antenna.y }} Z:{{ antenna.z }}</span>
                    </div>
                  </div>
                  <div class="antenna-actions">
                    <button class="action-btn locate" @click="locateAntenna(antenna)" title="定位">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/>
                      </svg>
                    </button>
                    <button class="action-btn edit" @click="editAntenna(antenna)" title="编辑">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                      </svg>
                    </button>
                    <button class="action-btn delete" @click="deleteAntenna(antenna)" title="删除">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                      </svg>
                    </button>
                  </div>
                </div>

                <div v-if="filteredAntennas.length === 0" class="empty-state">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M5.12 19.18A10 10 0 0 1 2 12C2 6.48 6.48 2 12 2s10 4.48 10 10a10 10 0 0 1-3.12 7.18"/>
                    <path d="M8.46 15.54A5 5 0 0 1 7 12a5 5 0 0 1 10 0 5 5 0 0 1-1.46 3.54"/>
                    <circle cx="12" cy="12" r="1"/>
                  </svg>
                  <p>暂无天线设备</p>
                  <span>点击下方按钮添加</span>
                </div>
              </div>

              <button class="add-btn primary" @click="handleAddAntennaClick">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"/><path d="M12 8v8M8 12h8"/>
                </svg>
                <span>添加天线设备</span>
              </button>
            </div>

            <!-- 视图控制 -->
            <div v-if="activeTab === 'view'" class="tab-content">
              <div class="view-section">
                <h4>视角预设</h4>
                <div class="preset-grid">
                  <button class="preset-btn" @click="setCesiumView('top')">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M12 19V5M5 12l7-7 7 7"/>
                    </svg>
                    <span>俯视图</span>
                  </button>
                  <button class="preset-btn" @click="setCesiumView('front')">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <circle cx="12" cy="12" r="3"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2"/>
                    </svg>
                    <span>前视图</span>
                  </button>
                  <button class="preset-btn" @click="setCesiumView('side')">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M21 12H3M12 3l-9 9 9 9"/>
                    </svg>
                    <span>侧视图</span>
                  </button>
                  <button class="preset-btn" @click="setCesiumView('iso')">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <rect x="3" y="3" width="18" height="18" rx="2"/>
                      <path d="M3 12h18M12 3v18"/>
                    </svg>
                    <span>等轴测</span>
                  </button>
                </div>
              </div>

              <div class="view-section">
                <h4>显示设置</h4>
                <div class="setting-item">
                  <label class="toggle-switch">
                    <input type="checkbox" v-model="showLabels" @change="toggleLabels" />
                    <span class="toggle-slider"></span>
                  </label>
                  <div class="setting-text">
                    <span class="setting-name">显示标签</span>
                    <span class="setting-desc">在天线上方显示名称标识</span>
                  </div>
                </div>
                <div class="setting-item">
                  <label class="toggle-switch">
                    <input type="checkbox" v-model="autoRotate" @change="toggleAutoRotate" />
                    <span class="toggle-slider"></span>
                  </label>
                  <div class="setting-text">
                    <span class="setting-name">自动旋转</span>
                    <span class="setting-desc">场景自动绕中心旋转</span>
                  </div>
                </div>
                <div class="setting-item">
                  <label class="toggle-switch">
                    <input type="checkbox" v-model="showCoverage" @change="toggleCoverage" />
                    <span class="toggle-slider"></span>
                  </label>
                  <div class="setting-text">
                    <span class="setting-name">信号覆盖热力图</span>
                    <span class="setting-desc">在地面显示 RSRP 覆盖色块</span>
                  </div>
                </div>
                <div class="setting-item" v-if="showCoverage">
                  <label class="toggle-switch">
                    <input type="checkbox" v-model="showSignalValues" @change="toggleSignalValues" />
                    <span class="toggle-slider"></span>
                  </label>
                  <div class="setting-text">
                    <span class="setting-name">显示信号值</span>
                    <span class="setting-desc">在热力图上标注 RSRP 数值</span>
                  </div>
                </div>
              </div>

              <div class="view-section" v-if="showCoverage">
                <h4>图例 (RSRP)</h4>
                <div class="legend-grid">
                  <div class="legend-item">
                    <span class="legend-color" style="background: #00ff88;"></span>
                    <span>≥ -80 dBm (优)</span>
                  </div>
                  <div class="legend-item">
                    <span class="legend-color" style="background: #ffaa00;"></span>
                    <span>-90 ~ -80 dBm (良)</span>
                  </div>
                  <div class="legend-item">
                    <span class="legend-color" style="background: #ff4444;"></span>
                    <span>-100 ~ -90 dBm (中)</span>
                  </div>
                  <div class="legend-item">
                    <span class="legend-color" style="background: #880000;"></span>
                    <span>< -100 dBm (差)</span>
                  </div>
                </div>
              </div>

              <div class="view-section">
                <h4>操作说明</h4>
                <div class="tips-list">
                  <div class="tip-item">
                    <kbd>左键拖拽</kbd>
                    <span>旋转视角</span>
                  </div>
                  <div class="tip-item">
                    <kbd>滚轮</kbd>
                    <span>缩放场景</span>
                  </div>
                  <div class="tip-item">
                    <kbd>右键拖拽</kbd>
                    <span>平移场景</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 操作说明 (3D模式) -->
          <div v-if="mapMode === '3D'" class="sidebar-section tips-section">
            <div class="section-header">
              <h3>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>
                </svg>
                操作说明
              </h3>
            </div>
            <div class="tips-list">
              <div class="tip-item">
                <kbd>左键拖拽</kbd>
                <span>旋转视角</span>
              </div>
              <div class="tip-item">
                <kbd>滚轮</kbd>
                <span>缩放地图</span>
              </div>
              <div class="tip-item">
                <kbd>右键拖拽</kbd>
                <span>平移地图</span>
              </div>
              <div class="tip-item">
                <kbd>点击标记</kbd>
                <span>查看基站信息</span>
              </div>
              <div class="tip-item">
                <kbd>进入基站</kbd>
                <span>查看三维环境</span>
              </div>
            </div>
          </div>
        </div>
      </aside>

      <!-- 地图容器 -->
      <div class="map-wrapper">
        <!-- 3D 地图 -->
        <div v-show="mapMode === '3D'" class="map-container" ref="mapContainer"></div>

        <!-- 添加模式提示 -->
        <div class="add-mode-overlay" v-if="addMode && mapMode === '3D'">
          <div class="add-mode-hint">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/><path d="M12 8v8M8 12h8"/>
            </svg>
            <span>添加模式：点击地图选择位置</span>
          </div>
        </div>

        <!-- 基站环境 -->
        <div v-if="mapMode === 'STATION'" class="station-container">
          <div class="cesium-container" id="cesiumContainer">
            <!-- 坐标显示 -->
            <div class="coordinate-display">
              <div class="coord-item">
                <span class="coord-label">经度</span>
                <span class="coord-value">{{ currentLng.toFixed(6) }}</span>
              </div>
              <div class="coord-divider"></div>
              <div class="coord-item">
                <span class="coord-label">纬度</span>
                <span class="coord-value">{{ currentLat.toFixed(6) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 坐标信息 (3D模式) -->
        <div v-if="mapMode === '3D'" class="map-coordinates">
          <span class="coord-label">LNG</span>
          <span class="coord-value">{{ currentLng.toFixed(6) }}</span>
          <span class="coord-divider">|</span>
          <span class="coord-label">LAT</span>
          <span class="coord-value">{{ currentLat.toFixed(6) }}</span>
        </div>
      </div>
    </main>

    <!-- 添加设备面板 -->
    <div v-if="addMode" class="add-panel-overlay" @click.self="cancelAddDevice">
      <div class="add-panel">
        <div class="add-panel-header">
          <h3>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/><path d="M12 8v8M8 12h8"/>
            </svg>
            添加设备
          </h3>
          <button class="close-btn" @click="cancelAddDevice">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>
        <div class="add-panel-body">
          <div class="form-group">
            <label>设备名称</label>
            <input v-model="pendingDevice.name" placeholder="请输入设备名称" class="form-input" />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>经度</label>
              <input v-model.number="pendingDevice.lng" type="number" step="0.000001" placeholder="点击地图选择或手动输入" class="form-input" />
            </div>
            <div class="form-group">
              <label>纬度</label>
              <input v-model.number="pendingDevice.lat" type="number" step="0.000001" placeholder="点击地图选择或手动输入" class="form-input" />
            </div>
          </div>
        </div>
        <div class="add-panel-footer">
          <button class="btn btn-secondary" @click="cancelAddDevice">取消</button>
          <button class="btn btn-primary" @click="confirmAddDevice">保存设备</button>
        </div>
      </div>
    </div>

    <!-- 基站信息面板 -->
    <transition name="panel-slide">
      <div v-if="showInfoPanel && selectedDevice" class="station-info-overlay">
        <div class="station-info-panel">
          <div class="panel-close-bar">
            <button class="panel-close-btn" @click="showInfoPanel = false">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M18 6L6 18M6 6l12 12"/>
              </svg>
            </button>
          </div>

          <div class="panel-hero">
            <div class="panel-hero-glow"></div>
            <div class="panel-station-badge" :style="{ background: getCoverageGradient(selectedDevice.coverage) }">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="4" y="2" width="16" height="20" rx="2"/>
                <path d="M12 6v4M8 10h8M12 14v4"/>
              </svg>
            </div>
            <div class="panel-hero-text">
              <h2 class="panel-station-name">{{ selectedDevice.name }}</h2>
              <div class="panel-station-tags">
                <span class="panel-tag type-tag">{{ selectedDevice.placeType }}</span>
                <span class="panel-tag area-tag">{{ selectedDevice.area }}</span>
                <span class="panel-tag grid-tag">{{ selectedDevice.grid }}</span>
              </div>
            </div>
            <div class="panel-coverage-ring" :style="{ '--pct': selectedDevice.coverage }">
              <svg viewBox="0 0 80 80">
                <circle cx="40" cy="40" r="34" class="ring-bg"/>
                <circle cx="40" cy="40" r="34" class="ring-fill" :style="{ strokeDashoffset: 214 - 214 * selectedDevice.coverage / 100, stroke: getCoverageColor(selectedDevice.coverage) }"/>
              </svg>
              <span class="ring-text">{{ selectedDevice.coverage }}<small>%</small></span>
            </div>
          </div>

          <div class="panel-metrics">
            <div class="metric-card" v-for="m in metricCards" :key="m.key">
              <div class="metric-icon" :style="{ background: m.gradient }">
                <component :is="m.icon" />
              </div>
              <div class="metric-body">
                <span class="metric-value" :class="m.valueClass">{{ m.value(selectedDevice) }}</span>
                <span class="metric-label">{{ m.label }}</span>
              </div>
            </div>
          </div>

          <div class="panel-detail-toggle" @click="detailExpanded = !detailExpanded">
            <div class="toggle-header">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="toggle-icon" :class="{ rotated: detailExpanded }">
                <path d="M9 18l6-6-6-6"/>
              </svg>
              <span>详细设备档案</span>
              <span class="toggle-hint">{{ detailExpanded ? '收起' : '展开' }}</span>
            </div>
          </div>

          <transition name="expand">
            <div v-if="detailExpanded" class="panel-detail-body">
              <div class="detail-section">
                <h4 class="detail-section-title">信号质量</h4>
                <div class="detail-grid">
                  <div class="detail-item">
                    <span class="detail-k">平均 RSRP</span>
                    <span class="detail-v" :class="getRsrpClass(selectedDevice.rsrp)">{{ selectedDevice.rsrp }} dBm</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-k">SINR</span>
                    <span class="detail-v">{{ selectedDevice.sinr }} dB</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-k">覆盖提升</span>
                    <span class="detail-v" :class="selectedDevice.improvement > 0 ? 'text-success' : 'text-danger'">{{ selectedDevice.improvement > 0 ? '+' : '' }}{{ selectedDevice.improvement }} dB</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-k">覆盖率</span>
                    <span class="detail-v">{{ selectedDevice.coverage }}%</span>
                  </div>
                </div>
              </div>
              <div class="detail-section">
                <h4 class="detail-section-title">传输性能</h4>
                <div class="detail-grid">
                  <div class="detail-item">
                    <span class="detail-k">上行速率</span>
                    <span class="detail-v text-primary">{{ selectedDevice.upSpeed }} Mbps</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-k">下行速率</span>
                    <span class="detail-v text-primary">{{ selectedDevice.downSpeed }} Mbps</span>
                  </div>
                </div>
              </div>
              <div class="detail-section">
                <h4 class="detail-section-title">运维信息</h4>
                <div class="detail-grid">
                  <div class="detail-item">
                    <span class="detail-k">维护单位</span>
                    <span class="detail-v">{{ selectedDevice.maintainer }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-k">最近测试</span>
                    <span class="detail-v">{{ selectedDevice.lastTest }}</span>
                  </div>
                  <div class="detail-item detail-full">
                    <span class="detail-k">所属网格</span>
                    <span class="detail-v">{{ selectedDevice.grid }}</span>
                  </div>
                  <div class="detail-item detail-full">
                    <span class="detail-k">地理位置</span>
                    <span class="detail-v mono">{{ selectedDevice.lng.toFixed(6) }}, {{ selectedDevice.lat.toFixed(6) }}</span>
                  </div>
                </div>
              </div>
            </div>
          </transition>
        </div>
      </div>
    </transition>

    <!-- 基站编辑弹窗 -->
    <div v-if="showStationDialog" class="dialog-overlay" @click.self="showStationDialog = false">
      <div class="dialog">
        <div class="dialog-header">
          <h3>基站信息</h3>
          <button class="close-btn" @click="showStationDialog = false">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>
        <div class="dialog-body">
          <div class="form-group">
            <label>基站名称 <span class="required">*</span></label>
            <input v-model="stationForm.name" placeholder="请输入基站名称" class="form-input" />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>经度</label>
              <input v-model.number="stationForm.lng" placeholder="经度" class="form-input" />
            </div>
            <div class="form-group">
              <label>纬度</label>
              <input v-model.number="stationForm.lat" placeholder="纬度" class="form-input" />
            </div>
          </div>
          <div class="form-group">
            <label>塔高 (m)</label>
            <input v-model.number="stationForm.height" placeholder="塔高" class="form-input" />
          </div>
        </div>
        <div class="dialog-footer">
          <button class="btn btn-secondary" @click="showStationDialog = false">取消</button>
          <button class="btn btn-primary" @click="confirmAddBaseStation">确认保存</button>
        </div>
      </div>
    </div>

    <!-- 天线编辑弹窗 -->
    <div v-if="showAntennaDialog" class="dialog-overlay" @click.self="showAntennaDialog = false">
      <div class="dialog dialog-lg">
        <div class="dialog-header">
          <h3>天线信息</h3>
          <button class="close-btn" @click="showAntennaDialog = false">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>
        <div class="dialog-body">
          <div class="form-group">
            <label>天线名称 <span class="required">*</span></label>
            <input v-model="antennaForm.name" placeholder="请输入天线名称" class="form-input" />
          </div>
          <div class="form-group">
            <label>天线类型</label>
            <select v-model="antennaForm.type" class="form-select">
              <option value="全向天线">全向天线</option>
              <option value="定向天线">定向天线</option>
              <option value="智能天线">智能天线</option>
            </select>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>位置 X</label>
              <input v-model.number="antennaForm.x" placeholder="X坐标" class="form-input" />
            </div>
            <div class="form-group">
              <label>位置 Y</label>
              <input v-model.number="antennaForm.y" placeholder="Y坐标" class="form-input" />
            </div>
            <div class="form-group">
              <label>位置 Z</label>
              <input v-model.number="antennaForm.z" placeholder="Z坐标（高度）" class="form-input" />
            </div>
          </div>
          <div class="form-group">
            <label>模型缩放</label>
            <input v-model.number="antennaForm.scale" placeholder="缩放比例" class="form-input" />
          </div>
          <div class="form-group">
            <label>模型文件</label>
            <div class="file-upload">
              <button type="button" class="upload-btn" @click="triggerFileUpload">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/>
                </svg>
                <span>选择本地 glb 文件</span>
              </button>
              <input
                type="file"
                ref="fileInput"
                accept=".glb"
                style="display: none"
                @change="handleFileUpload"
              />
              <span class="file-name" v-if="antennaForm.modelFile">{{ antennaForm.modelFile }}</span>
            </div>
          </div>

          <div class="form-divider">
            <span>信号参数</span>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>发射功率 (dBm)</label>
              <input v-model.number="antennaForm.power" type="number" min="20" max="50" class="form-input" />
            </div>
            <div class="form-group">
              <label>方向角 (°)</label>
              <input v-model.number="antennaForm.azimuth" type="number" min="0" max="360" class="form-input" />
              <span class="form-hint">0=北, 90=东</span>
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>下倾角 (°)</label>
              <input v-model.number="antennaForm.tilt" type="number" min="0" max="15" class="form-input" />
            </div>
            <div class="form-group">
              <label>天线增益 (dBi)</label>
              <input v-model.number="antennaForm.gain" type="number" min="0" max="25" class="form-input" />
            </div>
          </div>
        </div>
        <div class="dialog-footer">
          <button class="btn btn-secondary" @click="showAntennaDialog = false">取消</button>
          <button class="btn btn-primary" @click="confirmAddAntenna">确认保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, h } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';

// 防抖 & 节流工具
const debounce = (fn, delay = 300) => {
  let timer = null;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
};
const throttle = (fn, delay = 350) => {
  let last = 0;
  return (...args) => {
    const now = Date.now();
    if (now - last >= delay) {
      last = now;
      fn(...args);
    }
  };
};

// 图标组件
const MapIcon = {
  render() {
    return h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
      h('path', { d: 'M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z' }),
      h('circle', { cx: '12', cy: '10', r: '3' })
    ]);
  }
};

const AntennaIcon = {
  render() {
    return h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
      h('path', { d: 'M5.12 19.18A10 10 0 0 1 2 12C2 6.48 6.48 2 12 2s10 4.48 10 10a10 10 0 0 1-3.12 7.18' }),
      h('path', { d: 'M8.46 15.54A5 5 0 0 1 7 12a5 5 0 0 1 10 0 5 5 0 0 1-1.46 3.54' }),
      h('circle', { cx: '12', cy: '12', r: '1' })
    ]);
  }
};

const SettingsIcon = {
  render() {
    return h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
      h('circle', { cx: '12', cy: '12', r: '3' }),
      h('path', { d: 'M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z' })
    ]);
  }
};

// 信息面板图标
const SignalIcon = {
  render() {
    return h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
      h('path', { d: 'M22 12h-4l-3 9L9 3l-3 9H2' })
    ]);
  }
};
const UploadIcon = {
  render() {
    return h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
      h('path', { d: 'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4' }),
      h('polyline', { points: '17,8 12,3 7,8' }),
      h('line', { x1: '12', y1: '3', x2: '12', y2: '15' })
    ]);
  }
};
const MaintainerIcon = {
  render() {
    return h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
      h('path', { d: 'M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2' }),
      h('circle', { cx: '9', cy: '7', r: '4' }),
      h('path', { d: 'M23 21v-2a4 4 0 0 0-3-3.87' }),
      h('path', { d: 'M16 3.13a4 4 0 0 1 0 7.75' })
    ]);
  }
};
const ClockIcon = {
  render() {
    return h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
      h('circle', { cx: '12', cy: '12', r: '10' }),
      h('polyline', { points: '12,6 12,12 16,14' })
    ]);
  }
};

const metricCards = [
  {
    key: 'rsrp',
    label: '平均 RSRP',
    icon: SignalIcon,
    gradient: 'linear-gradient(135deg, #00ff88, #00cc66)',
    valueClass: (d) => getRsrpClass(d.rsrp),
    value: (d) => `${d.rsrp} dBm`
  },
  {
    key: 'upspeed',
    label: '上行速率',
    icon: UploadIcon,
    gradient: 'linear-gradient(135deg, #00d4ff, #0099cc)',
    valueClass: () => 'text-primary',
    value: (d) => `${d.upSpeed} Mbps`
  },
  {
    key: 'maintainer',
    label: '维护单位',
    icon: MaintainerIcon,
    gradient: 'linear-gradient(135deg, #ffaa00, #ee8800)',
    valueClass: () => 'text-warning',
    value: (d) => d.maintainer
  },
  {
    key: 'lastTest',
    label: '最近测试',
    icon: ClockIcon,
    gradient: 'linear-gradient(135deg, #a78bfa, #7c3aed)',
    valueClass: () => 'text-purple',
    value: (d) => d.lastTest
  }
];

const tabs = [
  { id: 'stations', label: '基站管理', icon: MapIcon },
  { id: 'antennas', label: '天线设备', icon: AntennaIcon },
  { id: 'view', label: '视图控制', icon: SettingsIcon }
];

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
const showCoverage = ref(false);
const showSignalValues = ref(false);
const coverageEntities = ref([]);
const signalLabelEntities = ref([]);
const sidebarCollapsed = ref(false);
const showInfoPanel = ref(false);
const selectedDevice = ref(null);
const detailExpanded = ref(false);
let draggingEntity = null;
let dragHandler = null;

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
  modelFile: 'old_antenna.glb',
  power: 43,
  azimuth: 0,
  tilt: 6,
  gain: 15
});

const TIANDITU_KEY = 'b0e573b5f5da44c19a0744cdfb313294';

let cesiumMapViewer = null;
let tempEntity = null;
let clickHandler = null;

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

const getParticleStyle = (i) => ({
  left: `${Math.random() * 100}%`,
  top: `${Math.random() * 100}%`,
  animationDelay: `${Math.random() * 20}s`,
  animationDuration: `${15 + Math.random() * 20}s`
});

const initMap = () => {
  if (!mapContainer.value) {
    console.error('Map container is null');
    return;
  }

  if (cesiumMapViewer) {
    cesiumMapViewer.destroy();
    cesiumMapViewer = null;
  }

  try {
    // 禁用 Cesium Ion 默认 token
    Cesium.Ion.defaultAccessToken = undefined;

    cesiumMapViewer = new Cesium.Viewer(mapContainer.value, {
      baseLayer: false,
      baseLayerPicker: false,
      geocoder: false,
      homeButton: false,
      sceneModePicker: false,
      navigationHelpButton: false,
      animation: false,
      timeline: false,
      fullscreenButton: false,
      vrButton: false,
      infoBox: false,
      selectionIndicator: false
    });

    // 等待 viewer 就绪后再添加图层
    cesiumMapViewer.scene.globe.depthTestAgainstTerrain = false;

    // 移除默认底图，添加天地图
    addTiandituLayers();

    // 触发 resize 事件以确保地图正确渲染
    window.dispatchEvent(new Event('resize'));

    console.log('Cesium map initialized successfully');
  } catch (error) {
    console.error('Failed to initialize Cesium map:', error);
    return;
  }

  // 设置初始视角
  cesiumMapViewer.camera.setView({
    destination: Cesium.Cartesian3.fromDegrees(116.397428, 39.90923, 15000),
    orientation: {
      heading: Cesium.Math.toRadians(0),
      pitch: Cesium.Math.toRadians(-45),
      roll: 0
    }
  });

  // 添加点击事件处理器
  const handler = new Cesium.ScreenSpaceEventHandler(cesiumMapViewer.scene.canvas);
  handler.setInputAction((event) => {
    if (!cesiumMapViewer) return;
    const picked = cesiumMapViewer.scene.pick(event.position);
    if (Cesium.defined(picked) && picked.id) {
      const entity = picked.id;
      if (entity.deviceId) {
        const device = devices.value.find(d => d.id === entity.deviceId);
        if (device && !addMode.value) {
          showDeviceInfoWindow(device, event.position);
        }
      }
    } else {
      if (addMode.value) {
        const ray = cesiumMapViewer.camera.getPickRay(event.position);
        const cartesian = cesiumMapViewer.scene.globe.pick(ray, cesiumMapViewer.scene);
        if (cartesian) {
          const cartographic = Cesium.Cartographic.fromCartesian(cartesian);
          const lng = Cesium.Math.toDegrees(cartographic.longitude);
          const lat = Cesium.Math.toDegrees(cartographic.latitude);
          pendingDevice.value = {
            ...pendingDevice.value,
            lng: lng,
            lat: lat
          };
          updateTempMarker(lng, lat);
        }
      }
    }
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

  // 鼠标移动事件
  handler.setInputAction((event) => {
    if (!cesiumMapViewer) return;
    const ray = cesiumMapViewer.camera.getPickRay(event.endPosition);
    if (ray) {
      const cartesian = cesiumMapViewer.scene.globe.pick(ray, cesiumMapViewer.scene);
      if (cartesian) {
        const cartographic = Cesium.Cartographic.fromCartesian(cartesian);
        currentLng.value = Cesium.Math.toDegrees(cartographic.longitude);
        currentLat.value = Cesium.Math.toDegrees(cartographic.latitude);
      }
    }
  }, Cesium.ScreenSpaceEventType.MOUSE_MOVE);

  // 加载设备数据
  loadDevices();

  console.log('Map initialization complete');
};

const addTiandituLayers = () => {
  if (!cesiumMapViewer) return;

  try {
    const imageryLayers = cesiumMapViewer.imageryLayers;

    // 移除所有默认底图
    imageryLayers.removeAll();

    // 添加天地图影像底图
    const baseLayer = new Cesium.UrlTemplateImageryProvider({
      url: `https://t{s}.tianditu.gov.cn/img_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=img&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk=${TIANDITU_KEY}`,
      subdomains: ['0', '1', '2', '3', '4', '5', '6', '7'],
      maximumLevel: 18,
      credit: '天地图'
    });
    imageryLayers.addImageryProvider(baseLayer);

    // 添加天地图注记图层
    const labelLayer = new Cesium.UrlTemplateImageryProvider({
      url: `https://t{s}.tianditu.gov.cn/cia_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=cia&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk=${TIANDITU_KEY}`,
      subdomains: ['0', '1', '2', '3', '4', '5', '6', '7'],
      maximumLevel: 18,
      credit: '天地图注记'
    });
    imageryLayers.addImageryProvider(labelLayer);

    console.log('Tianditu layers added successfully');
  } catch (error) {
    console.error('Failed to add Tianditu layers:', error);
    // 备用方案：使用 OpenStreetMap
    try {
      const osmLayer = new Cesium.UrlTemplateImageryProvider({
        url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        subdomains: ['a', 'b', 'c'],
        maximumLevel: 18,
        credit: 'OpenStreetMap'
      });
      cesiumMapViewer.imageryLayers.addImageryProvider(osmLayer);
      console.log('Using OpenStreetMap as fallback');
    } catch (fallbackError) {
      console.error('Failed to add fallback layer:', fallbackError);
    }
  }
};

const loadDevices = async () => {
  devices.value = [
    {
      id: 1, name: '北京协和医院', lng: 116.397428, lat: 39.90923, type: 'station',
      placeType: '医院', area: '东城区', coverage: 98, rsrp: -85, sinr: 25,
      upSpeed: 85, downSpeed: 350, improvement: 3.5,
      grid: '东城网格A区', maintainer: '北京联通运维部', lastTest: '2024-01-15 14:30'
    },
    {
      id: 2, name: '北京站', lng: 116.427428, lat: 39.90423, type: 'station',
      placeType: '交通枢纽', area: '东城区', coverage: 95, rsrp: -92, sinr: 22,
      upSpeed: 75, downSpeed: 320, improvement: 2.1,
      grid: '东城网格B区', maintainer: '北京移动运维部', lastTest: '2024-01-14 10:15'
    },
    {
      id: 3, name: '国家体育场', lng: 116.397428, lat: 39.94423, type: 'station',
      placeType: '场馆', area: '朝阳区', coverage: 92, rsrp: -98, sinr: 18,
      upSpeed: 65, downSpeed: 280, improvement: 1.2,
      grid: '朝阳网格C区', maintainer: '北京电信运维部', lastTest: '2024-01-13 16:45'
    },
    {
      id: 4, name: '北京大学', lng: 116.317428, lat: 39.98923, type: 'station',
      placeType: '高校', area: '海淀区', coverage: 88, rsrp: -105, sinr: 15,
      upSpeed: 45, downSpeed: 220, improvement: -0.5,
      grid: '海淀网格A区', maintainer: '北京联通运维部', lastTest: '2024-01-12 09:30'
    },
    {
      id: 5, name: '首都国际机场', lng: 116.587428, lat: 40.07923, type: 'station',
      placeType: '交通枢纽', area: '顺义区', coverage: 99, rsrp: -78, sinr: 28,
      upSpeed: 120, downSpeed: 450, improvement: 4.2,
      grid: '顺义网格A区', maintainer: '北京移动运维部', lastTest: '2024-01-16 08:00'
    },
    {
      id: 6, name: '北京友谊医院', lng: 116.357428, lat: 39.93923, type: 'station',
      placeType: '医院', area: '西城区', coverage: 91, rsrp: -100, sinr: 19,
      upSpeed: 55, downSpeed: 260, improvement: 1.8,
      grid: '西城网格B区', maintainer: '北京电信运维部', lastTest: '2024-01-11 15:20'
    },
    {
      id: 7, name: '北京南站', lng: 116.387428, lat: 39.86423, type: 'station',
      placeType: '交通枢纽', area: '丰台区', coverage: 94, rsrp: -94, sinr: 21,
      upSpeed: 70, downSpeed: 300, improvement: 2.5,
      grid: '丰台网格A区', maintainer: '北京联通运维部', lastTest: '2024-01-14 11:30'
    },
    {
      id: 8, name: '清华大学', lng: 116.327428, lat: 39.99923, type: 'station',
      placeType: '高校', area: '海淀区', coverage: 89, rsrp: -102, sinr: 16,
      upSpeed: 50, downSpeed: 240, improvement: 0.8,
      grid: '海淀网格B区', maintainer: '北京电信运维部', lastTest: '2024-01-12 10:00'
    }
  ];
  updateMarkers();
};

const updateMarkers = () => {
  if (!cesiumMapViewer) {
    console.warn('Cesium viewer not initialized, skipping updateMarkers');
    return;
  }

  cesiumMapViewer.entities.removeAll();

  devices.value.forEach(device => {
    addMarker(device);
  });
};

const buildMarkerImage = (hex) => {
  // Build a bold, high-contrast pin marker as an SVG data URI.
  // 三层结构：深色外圈（与卫星图分离）+ 亮色主体 + 白色高光
  const svg = [
    '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">',
    // 外层暗影环 — 在任何底图上形成对比度
    '<circle cx="32" cy="32" r="30" fill="none" stroke="rgba(0,0,0,0.55)" stroke-width="4"/>',
    // 浅色扩散光晕
    '<circle cx="32" cy="32" r="27" fill="none" stroke="' + hex + '" stroke-width="3" opacity="0.35"/>',
    // 主体圆
    '<circle cx="32" cy="32" r="21" fill="' + hex + '" stroke="#fff" stroke-width="3.5"/>',
    // 内层渐变效果 — 白色半透明覆盖
    '<circle cx="32" cy="32" r="14" fill="rgba(255,255,255,0.25)"/>',
    // 中心白点
    '<circle cx="32" cy="32" r="5" fill="#fff"/>',
    '</svg>'
  ].join('');
  return 'data:image/svg+xml;base64,' + btoa(svg);
};

const addMarker = (device) => {
  if (!cesiumMapViewer) {
    console.warn('Cesium viewer not initialized, skipping addMarker');
    return;
  }

  const color = getCoverageCesiumColor(device.coverage);
  const hexColor = color.toCssColorString();
  const imageUrl = buildMarkerImage(hexColor);

  const entity = cesiumMapViewer.entities.add({
    deviceId: device.id,
    position: Cesium.Cartesian3.fromDegrees(device.lng, device.lat, 0),
    billboard: {
      image: imageUrl,
      width: 64,
      height: 64,
      verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
      horizontalOrigin: Cesium.HorizontalOrigin.CENTER,
      disableDepthTestDistance: Number.POSITIVE_INFINITY,
      scaleByDistance: new Cesium.NearFarScalar(800, 1.2, 15000, 0.5),
      pixelOffset: new Cesium.Cartesian2(0, -8)
    },
    label: {
      text: device.name,
      font: 'bold 16px "Source Han Sans SC", "Noto Sans SC", sans-serif',
      fillColor: Cesium.Color.WHITE,
      outlineColor: Cesium.Color.fromCssColorString('#0a0f1a'),
      outlineWidth: 6,
      style: Cesium.LabelStyle.FILL_AND_OUTLINE,
      verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
      pixelOffset: new Cesium.Cartesian2(0, -44),
      disableDepthTestDistance: Number.POSITIVE_INFINITY,
      show: true,
      scale: 1.2
    },
    description: `
      <div style="padding: 12px; min-width: 280px;">
        <h3 style="margin: 0 0 10px 0; color: #333;">${device.name}</h3>
        <p style="margin: 5px 0; color: #666;"><strong>类型:</strong> ${device.placeType}</p>
        <p style="margin: 5px 0; color: #666;"><strong>区域:</strong> ${device.area}</p>
        <p style="margin: 5px 0; color: #666;"><strong>覆盖率:</strong> ${device.coverage}%</p>
        <p style="margin: 5px 0; color: #666;"><strong>RSRP:</strong> ${device.rsrp} dBm</p>
        <p style="margin: 5px 0; color: #666;"><strong>SINR:</strong> ${device.sinr} dB</p>
      </div>
    `
  });

  markers.value.push(entity);
};

const getCoverageCesiumColor = (coverage) => {
  if (coverage >= 90) return Cesium.Color.fromCssColorString('#00ff88');
  if (coverage >= 80) return Cesium.Color.fromCssColorString('#ffaa00');
  return Cesium.Color.fromCssColorString('#ff4444');
};

const getDeviceColor = (coverage) => {
  if (coverage >= 90) return 'linear-gradient(135deg, #00ff88, #00cc6a)';
  if (coverage >= 80) return 'linear-gradient(135deg, #ffaa00, #ff8800)';
  return 'linear-gradient(135deg, #ff4444, #cc0000)';
};

const getCoverageGradient = (coverage) => {
  if (coverage >= 95) return 'linear-gradient(135deg, #00ff88, #00cc6a)';
  if (coverage >= 90) return 'linear-gradient(135deg, #00d4ff, #0099cc)';
  if (coverage >= 80) return 'linear-gradient(135deg, #ffaa00, #ff8800)';
  return 'linear-gradient(135deg, #ff4444, #cc0000)';
};

const getCoverageColor = (coverage) => {
  if (coverage >= 95) return '#00ff88';
  if (coverage >= 90) return '#00d4ff';
  if (coverage >= 80) return '#ffaa00';
  return '#ff4444';
};

const getRsrpClass = (rsrp) => {
  if (rsrp >= -85) return 'text-success';
  if (rsrp >= -95) return 'text-warning';
  return 'text-danger';
};

const getAntennaColor = (type) => {
  switch (type) {
    case '全向天线': return 'linear-gradient(135deg, #00d4ff, #0099cc)';
    case '定向天线': return 'linear-gradient(135deg, #00ff88, #00cc6a)';
    case '智能天线': return 'linear-gradient(135deg, #aa66ff, #8844cc)';
    default: return 'linear-gradient(135deg, #666, #444)';
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

const showDeviceInfoWindow = (device, position) => {
  if (!cesiumMapViewer) return;
  const entity = cesiumMapViewer.entities.values.find(e => e.deviceId === device.id);
  if (entity) {
    cesiumMapViewer.selectedEntity = entity;
  }
  // 飞至基站上空并显示信息面板
  cesiumMapViewer.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(device.lng, device.lat, 600),
    orientation: {
      heading: Cesium.Math.toRadians(0),
      pitch: Cesium.Math.toRadians(-60),
      roll: 0
    },
    duration: 1.2
  });
  selectedDevice.value = device;
  detailExpanded.value = false;
  showInfoPanel.value = true;
};

window._designEnterStation = (deviceId) => {
  const device = devices.value.find(d => d.id === deviceId);
  if (device) enterStation(device);
};

window._designLocate = (deviceId) => {
  const device = devices.value.find(d => d.id === deviceId);
  if (device) locateDevice(device);
};

const removeTempMarker = () => {
  if (tempEntity && cesiumMapViewer) {
    try {
      cesiumMapViewer.entities.remove(tempEntity);
    } catch (e) {
      console.warn('Failed to remove temp marker:', e);
    }
    tempEntity = null;
  }
};

const updateTempMarker = (lng, lat) => {
  removeTempMarker();
  if (!cesiumMapViewer) {
    console.warn('Cesium viewer not initialized, skipping updateTempMarker');
    return;
  }

  try {
    const pos = Cesium.Cartesian3.fromDegrees(lng, lat, 0);
    const cyanHex = '#00d4ff';
    const imageUrl = buildMarkerImage(cyanHex);

    tempEntity = cesiumMapViewer.entities.add({
      position: pos,
      billboard: {
        image: imageUrl,
        width: 64,
        height: 64,
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        horizontalOrigin: Cesium.HorizontalOrigin.CENTER,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
        scaleByDistance: new Cesium.NearFarScalar(800, 1.2, 15000, 0.5),
        pixelOffset: new Cesium.Cartesian2(0, -8)
      },
      label: {
        text: '待添加设备',
        font: 'bold 16px "Source Han Sans SC", "Noto Sans SC", sans-serif',
        fillColor: Cesium.Color.fromCssColorString('#00d4ff'),
        outlineColor: Cesium.Color.fromCssColorString('#0a0f1a'),
        outlineWidth: 6,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        pixelOffset: new Cesium.Cartesian2(0, -44),
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
        show: true,
        scale: 1.2
      }
    });
  } catch (e) {
    console.warn('Failed to add temp marker:', e);
  }
};

const toggleAddMode = throttle(() => {
  addMode.value = !addMode.value;

  if (addMode.value && cesiumMapViewer) {
    const center = cesiumMapViewer.camera.position;
    const cartographic = Cesium.Cartographic.fromCartesian(center);
    const lng = Cesium.Math.toDegrees(cartographic.longitude);
    const lat = Cesium.Math.toDegrees(cartographic.latitude);

    pendingDevice.value = {
      name: '',
      lng: lng,
      lat: lat
    };
    updateTempMarker(lng, lat);
  } else {
    removeTempMarker();
  }
}, 350);

const cancelAddDevice = debounce(() => {
  if (addMode.value) {
    removeTempMarker();
    pendingDevice.value = {
      name: '',
      lng: 116.397428,
      lat: 39.90923
    };
    addMode.value = false;
  }
}, 300);

const _confirmAddDevice = async () => {
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
const confirmAddDevice = debounce(_confirmAddDevice, 500);

const _locateDevice = (device) => {
  if (!cesiumMapViewer) {
    console.warn('Cesium viewer not initialized, skipping locateDevice');
    return;
  }

  cesiumMapViewer.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(device.lng, device.lat, 600),
    orientation: {
      heading: Cesium.Math.toRadians(0),
      pitch: Cesium.Math.toRadians(-60),
      roll: 0
    },
    duration: 1.2
  });

  const entity = cesiumMapViewer.entities.values.find(e => e.deviceId === device.id);
  if (entity) {
    cesiumMapViewer.selectedEntity = entity;
  }

  selectedDevice.value = device;
  detailExpanded.value = false;
  showInfoPanel.value = true;
};
const locateDevice = throttle(_locateDevice, 400);

const _enterStation = (device) => {
  selectedStation.value = device;
  loadNearbyStations(device);
  mapMode.value = 'STATION';
  nextTick(() => {
    initCesium();
    loadStationAntennas();
  });
};
const enterStation = debounce(_enterStation, 400);

const loadNearbyStations = (currentStation) => {
  nearbyStations.value = [
    { id: 1, name: '测试基站A', lng: 116.397428, lat: 39.90923, height: 100 },
    { id: 2, name: '测试基站B', lng: 116.407428, lat: 39.91923, height: 80 },
    { id: 3, name: '测试基站C', lng: 116.387428, lat: 39.89923, height: 120 }
  ];
};

const handleAddBaseStationClick = debounce(() => {
  stationForm.value = {
    id: null,
    name: '',
    lng: selectedStation.value?.lng || 116.397428,
    lat: selectedStation.value?.lat || 39.90923,
    height: 100
  };
  showStationDialog.value = true;
}, 300);

const editStation = (station) => {
  stationForm.value = { ...station };
  showStationDialog.value = true;
};

const _confirmAddBaseStation = () => {
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
const confirmAddBaseStation = debounce(_confirmAddBaseStation, 500);

const _switchStation = (station) => {
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
const switchStation = debounce(_switchStation, 400);

const deleteBaseStation = debounce((station) => {
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
        _switchStation(nearbyStations.value[0]);
      } else {
        backToMap();
      }
    }

    ElMessage.success('删除成功');
  }).catch(() => {
    ElMessage.info('已取消删除');
  });
}, 400);

const backToMap = debounce(() => {
  selectedStation.value = null;
  mapMode.value = '3D';
  if (cesiumViewer.value) {
    cesiumViewer.value.destroy();
    cesiumViewer.value = null;
  }
}, 400);

const deleteDevice = debounce((device) => {
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
}, 400);

const zoomIn = throttle(() => {
  if (!cesiumMapViewer) {
    console.warn('Cesium viewer not initialized, skipping zoomIn');
    return;
  }
  const currentHeight = cesiumMapViewer.camera.positionCartographic.height;
  cesiumMapViewer.camera.moveForward(currentHeight * 0.3);
}, 200);

const zoomOut = throttle(() => {
  if (!cesiumMapViewer) {
    console.warn('Cesium viewer not initialized, skipping zoomOut');
    return;
  }
  const currentHeight = cesiumMapViewer.camera.positionCartographic.height;
  cesiumMapViewer.camera.moveBackward(currentHeight * 0.3);
}, 200);

const resetView = throttle(() => {
  if (!cesiumMapViewer) {
    console.warn('Cesium viewer not initialized, skipping resetView');
    return;
  }
  cesiumMapViewer.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(116.397428, 39.90923, 15000),
    orientation: {
      heading: Cesium.Math.toRadians(0),
      pitch: Cesium.Math.toRadians(-45),
      roll: 0
    },
    duration: 1
  });
}, 500);

const toggleMapMode = debounce((mode) => {
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
      if (!cesiumMapViewer) {
        initMap();
      } else {
        window.dispatchEvent(new Event('resize'));
      }
    });
  }
}, 400);

const initCesium = () => {
  const container = document.getElementById('cesiumContainer');
  if (!container) {
    console.error('Cesium container not found');
    return;
  }

  if (!selectedStation.value) {
    ElMessage.error('请先选择基站');
    return;
  }

  const lng = selectedStation.value.lng || 116.397428;
  const lat = selectedStation.value.lat || 39.90923;

  try {
    // 禁用 Cesium Ion 默认 token
    Cesium.Ion.defaultAccessToken = undefined;

    cesiumViewer.value = new Cesium.Viewer('cesiumContainer', {
      baseLayer: false,
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

    cesiumViewer.value.scene.backgroundColor = Cesium.Color.fromCssColorString('#0a0f1a');
    cesiumViewer.value.scene.globe.baseColor = Cesium.Color.fromCssColorString('#0d1b2a');
    cesiumViewer.value.scene.globe.showGroundAtmosphere = false;
    cesiumViewer.value.scene.globe.depthTestAgainstTerrain = false;

    try {
      const tileProvider = new Cesium.UrlTemplateImageryProvider({
        url: 'https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}.png',
        subdomains: ['a', 'b', 'c', 'd'],
        maximumLevel: 18,
        credit: ''
      });
      cesiumViewer.value.imageryLayers.addImageryProvider(tileProvider);
    } catch (e) {
      console.warn('Tile provider failed, using base color only');
    }

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
    setupDragHandler();

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

  // 地面平台
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

  // 基站塔
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

  // 塔顶平台
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

  // 地面网格
  addGroundGrid(lng, lat);

  // 通信厂区模型
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
    const hColor = i === 0 ? Cesium.Color.fromCssColorString('#00d4ff').withAlpha(0.8) : Cesium.Color.WHITE.withAlpha(0.2);

    cesiumViewer.value.entities.add({
      polyline: {
        positions: [hStart, hEnd],
        width: 2,
        material: hColor
      }
    });

    const vStart = Cesium.Cartesian3.fromDegrees(lng + i * 0.00005, lat - gridSize * 0.00005, 0.5);
    const vEnd = Cesium.Cartesian3.fromDegrees(lng + i * 0.00005, lat + gridSize * 0.00005, 0.5);
    const vColor = i === 0 ? Cesium.Color.fromCssColorString('#00d4ff').withAlpha(0.8) : Cesium.Color.WHITE.withAlpha(0.2);

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
    case '全向天线': return Cesium.Color.fromCssColorString('#00d4ff').withAlpha(0.9);
    case '定向天线': return Cesium.Color.fromCssColorString('#00ff88').withAlpha(0.9);
    case '智能天线': return Cesium.Color.fromCssColorString('#aa66ff').withAlpha(0.9);
    default: return Cesium.Color.GRAY.withAlpha(0.9);
  }
};

const setupDragHandler = () => {
  if (!cesiumViewer.value) return;

  dragHandler = new Cesium.ScreenSpaceEventHandler(cesiumViewer.value.scene.canvas);

  dragHandler.setInputAction((event) => {
    const picked = cesiumViewer.value.scene.pick(event.position);
    if (Cesium.defined(picked) && picked.id && picked.id.antennaId) {
      draggingEntity = picked.id;
      cesiumViewer.value.scene.screenSpaceCameraController.enableInputs = false;
    }
  }, Cesium.ScreenSpaceEventType.LEFT_DOWN);

  dragHandler.setInputAction((event) => {
    if (!draggingEntity) return;
    const ray = cesiumViewer.value.camera.getPickRay(event.endPosition);
    const globe = cesiumViewer.value.scene.globe;
    const intersection = globe.pick(ray, cesiumViewer.value.scene);
    if (intersection) {
      const cartographic = Cesium.Cartographic.fromCartesian(intersection);
      const newLng = Cesium.Math.toDegrees(cartographic.longitude);
      const newLat = Cesium.Math.toDegrees(cartographic.latitude);
      const height = draggingEntity.position.getValue().height || 10;

      draggingEntity.position = Cesium.Cartesian3.fromDegrees(newLng, newLat, height);
    }
  }, Cesium.ScreenSpaceEventType.MOUSE_MOVE);

  dragHandler.setInputAction(() => {
    if (!draggingEntity) return;

    const pos = draggingEntity.position.getValue(Cesium.JulianDate.now());
    const cartographic = Cesium.Cartographic.fromCartesian(pos);
    const newLng = Cesium.Math.toDegrees(cartographic.longitude);
    const newLat = Cesium.Math.toDegrees(cartographic.latitude);

    const stationLng = selectedStation.value.lng || 116.397428;
    const stationLat = selectedStation.value.lat || 39.90923;

    const newX = (newLng - stationLng) / 0.0001;
    const newY = (newLat - stationLat) / 0.0001;

    const antennaId = draggingEntity.antennaId;
    const antennaIndex = stationAntennas.value.findIndex(a => a.id === antennaId);
    if (antennaIndex >= 0) {
      stationAntennas.value[antennaIndex].x = Math.round(newX * 10) / 10;
      stationAntennas.value[antennaIndex].y = Math.round(newY * 10) / 10;

      if (showCoverage.value) {
        refreshCoverageHeatmap();
      }
    }

    draggingEntity = null;
    cesiumViewer.value.scene.screenSpaceCameraController.enableInputs = true;
  }, Cesium.ScreenSpaceEventType.LEFT_UP);
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

const handleAddAntennaClick = debounce(() => {
  antennaForm.value = {
    name: '',
    type: '全向天线',
    x: 0,
    y: 0,
    z: 10,
    scale: 0.5,
    modelFile: 'old_antenna.glb',
    power: 43,
    azimuth: 0,
    tilt: 6,
    gain: 15
  };
  showAntennaDialog.value = true;
}, 300);

const editAntenna = debounce((antenna) => {
  antennaForm.value = { ...antenna };
  showAntennaDialog.value = true;
}, 300);

const _confirmAddAntenna = () => {
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

  if (showCoverage.value) {
    refreshCoverageHeatmap();
  }
};
const confirmAddAntenna = debounce(_confirmAddAntenna, 500);

const locateAntenna = throttle((antenna) => {
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
}, 400);

const deleteAntenna = debounce((antenna) => {
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

    if (showCoverage.value) {
      refreshCoverageHeatmap();
    }
  }).catch(() => {
    ElMessage.info('已取消删除');
  });
}, 400);

const setCesiumView = throttle((viewType) => {
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
}, 350);

const toggleLabels = () => {
  if (!cesiumViewer.value) return;

  const entities = cesiumViewer.value.entities.values;
  for (let i = 0; i < entities.length; i++) {
    const entity = entities[i];
    if (entity.antennaId && entity.label) {
      entity.label.show = showLabels.value;
    }
  }
};

const toggleAutoRotate = () => {
  if (!cesiumViewer.value) return;

  cesiumViewer.value.scene.camera.lookAtTransform(Cesium.Matrix4.IDENTITY);
  cesiumViewer.value.scene.camera.enableAutoRotation = autoRotate.value;
};

// ========== Signal Propagation Model ==========

// 窗口大小变化处理
const handleResize = () => {
  if (cesiumMapViewer) {
    cesiumMapViewer.resize();
  }
};

const toRad = (deg) => deg * Math.PI / 180;

const calcDistance3D = (lng1, lat1, h1, lng2, lat2, h2) => {
  const R = 6371000;
  const dLat = toRad(lat2 - lat1);
  const dLng = toRad(lng2 - lng1);
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2;
  const dHoriz = R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  const dVert = h2 - h1;
  return Math.sqrt(dHoriz * dHoriz + dVert * dVert);
};

const calcAzimuth = (lng1, lat1, lng2, lat2) => {
  const dLng = toRad(lng2 - lng1);
  const y = Math.sin(dLng) * Math.cos(toRad(lat2));
  const x = Math.cos(toRad(lat1)) * Math.sin(toRad(lat2)) - Math.sin(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.cos(dLng);
  let brng = Math.atan2(y, x) * 180 / Math.PI;
  return (brng + 360) % 360;
};

const calcAntennaGain = (antenna, azimuthToTarget) => {
  if (antenna.type === '全向天线') {
    return antenna.gain || 15;
  }

  const halfBeamwidth = 65 / 2;
  const frontToBack = 25;
  let angleDiff = Math.abs(azimuthToTarget - (antenna.azimuth || 0));
  if (angleDiff > 180) angleDiff = 360 - angleDiff;

  if (angleDiff <= halfBeamwidth) {
    return antenna.gain || 15;
  } else if (angleDiff <= 90) {
    const loss = (angleDiff - halfBeamwidth) / (90 - halfBeamwidth) * frontToBack;
    return (antenna.gain || 15) - loss;
  } else {
    return (antenna.gain || 15) - frontToBack;
  }
};

const calcTiltLoss = (antenna, distance, heightDiff) => {
  if (distance < 1) return 0;
  const verticalAngle = Math.atan2(heightDiff, distance) * 180 / Math.PI;
  const tilt = antenna.tilt || 6;
  const angleDiff = Math.abs(verticalAngle + tilt);
  if (angleDiff <= 10) return 0;
  return Math.min(angleDiff * 0.5, 10);
};

const calculateRSRP = (antenna, stationLng, stationLat, pointLng, pointLat) => {
  const antLng = stationLng + (antenna.x || 0) * 0.0001;
  const antLat = stationLat + (antenna.y || 0) * 0.0001;
  const antHeight = antenna.z || 10;

  const distance = calcDistance3D(antLng, antLat, antHeight, pointLng, pointLat, 0);
  if (distance < 1) return -40;

  const azimuth = calcAzimuth(antLng, antLat, pointLng, pointLat);
  const gain = calcAntennaGain(antenna, azimuth);
  const tiltLoss = calcTiltLoss(antenna, distance, -antHeight);

  const freq = 1800;
  const pl0 = 46.3 + 33.9 * Math.log10(freq) - 13.82 * Math.log10(Math.max(antHeight, 1));
  const pathLoss = pl0 + (44.9 - 6.55 * Math.log10(Math.max(antHeight, 1))) * Math.log10(Math.max(distance, 1));

  const txPower = antenna.power || 43;
  return txPower + gain - pathLoss - tiltLoss;
};

const getRSRPColor = (rsrp) => {
  if (rsrp >= -80) return Cesium.Color.fromCssColorString('#00ff88').withAlpha(0.5);
  if (rsrp >= -90) return Cesium.Color.fromCssColorString('#ffaa00').withAlpha(0.45);
  if (rsrp >= -100) return Cesium.Color.fromCssColorString('#ff4444').withAlpha(0.4);
  return Cesium.Color.fromCssColorString('#880000').withAlpha(0.35);
};

// ========== Coverage Heatmap ==========

const clearCoverageHeatmap = () => {
  if (!cesiumViewer.value) return;
  coverageEntities.value.forEach(entity => {
    cesiumViewer.value.entities.remove(entity);
  });
  coverageEntities.value = [];
  clearSignalLabels();
};

const clearSignalLabels = () => {
  if (!cesiumViewer.value) return;
  signalLabelEntities.value.forEach(entity => {
    cesiumViewer.value.entities.remove(entity);
  });
  signalLabelEntities.value = [];
};

const renderCoverageHeatmap = () => {
  if (!cesiumViewer.value || !selectedStation.value) return;
  clearCoverageHeatmap();

  const lng = selectedStation.value.lng || 116.397428;
  const lat = selectedStation.value.lat || 39.90923;
  const antennas = stationAntennas.value;
  if (antennas.length === 0) {
    ElMessage.warning('请先添加天线设备');
    showCoverage.value = false;
    return;
  }

  const gridCount = 40;
  const range = 0.0025;
  const step = (range * 2) / gridCount;

  for (let i = 0; i <= gridCount; i++) {
    for (let j = 0; j <= gridCount; j++) {
      const pLng = lng - range + i * step;
      const pLat = lat - range + j * step;

      let maxRsrp = -150;
      for (const ant of antennas) {
        const rsrp = calculateRSRP(ant, lng, lat, pLng, pLat);
        if (rsrp > maxRsrp) maxRsrp = rsrp;
      }

      const halfStep = step / 2;
      const entity = cesiumViewer.value.entities.add({
        polygon: {
          hierarchy: Cesium.Cartesian3.fromDegreesArray([
            pLng - halfStep, pLat - halfStep,
            pLng + halfStep, pLat - halfStep,
            pLng + halfStep, pLat + halfStep,
            pLng - halfStep, pLat + halfStep
          ]),
          height: 1.0,
          heightReference: Cesium.HeightReference.RELATIVE_TO_GROUND,
          material: getRSRPColor(maxRsrp)
        }
      });
      coverageEntities.value.push(entity);
    }
  }

  if (showSignalValues.value) {
    renderSignalLabels(lng, lat, antennas, gridCount, range, step);
  }
};

const renderSignalLabels = (lng, lat, antennas, gridCount, range, step) => {
  const labelStep = 4;
  for (let i = 0; i <= gridCount; i += labelStep) {
    for (let j = 0; j <= gridCount; j += labelStep) {
      const pLng = lng - range + i * step;
      const pLat = lat - range + j * step;

      let maxRsrp = -150;
      for (const ant of antennas) {
        const rsrp = calculateRSRP(ant, lng, lat, pLng, pLat);
        if (rsrp > maxRsrp) maxRsrp = rsrp;
      }

      const labelEntity = cesiumViewer.value.entities.add({
        position: Cesium.Cartesian3.fromDegrees(pLng, pLat, 2.0),
        label: {
          text: `${Math.round(maxRsrp)}`,
          font: '11px monospace',
          fillColor: Cesium.Color.WHITE,
          outlineColor: Cesium.Color.BLACK,
          outlineWidth: 1,
          style: Cesium.LabelStyle.FILL_AND_OUTLINE,
          verticalOrigin: Cesium.VerticalOrigin.CENTER,
          horizontalOrigin: Cesium.HorizontalOrigin.CENTER,
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
          scale: 0.9
        }
      });
      signalLabelEntities.value.push(labelEntity);
    }
  }
};

const refreshCoverageHeatmap = () => {
  if (showCoverage.value) {
    renderCoverageHeatmap();
  }
};

const toggleCoverage = (val) => {
  if (val) {
    renderCoverageHeatmap();
  } else {
    clearCoverageHeatmap();
    clearSignalLabels();
  }
};

const toggleSignalValues = (val) => {
  if (val && showCoverage.value) {
    const lng = selectedStation.value.lng || 116.397428;
    const lat = selectedStation.value.lat || 39.90923;
    const gridCount = 40;
    const range = 0.0025;
    const step = (range * 2) / gridCount;
    renderSignalLabels(lng, lat, stationAntennas.value, gridCount, range, step);
  } else {
    clearSignalLabels();
  }
};

onMounted(() => {
  // 使用 nextTick 确保 DOM 完全渲染后再初始化地图
  nextTick(() => {
    setTimeout(() => {
      initMap();
    }, 100);
  });

  // 监听窗口大小变化，重新调整地图大小
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  // 移除窗口大小变化监听
  window.removeEventListener('resize', handleResize);

  if (cesiumMapViewer) {
    cesiumMapViewer.destroy();
    cesiumMapViewer = null;
  }
  if (dragHandler) {
    dragHandler.destroy();
    dragHandler = null;
  }
  if (cesiumViewer.value) {
    clearCoverageHeatmap();
    clearSignalLabels();
    cesiumViewer.value.destroy();
  }
  if (clickHandler) {
    clickHandler.destroy();
    clickHandler = null;
  }
  delete window._designEnterStation;
  delete window._designLocate;
});
</script>

<style scoped>
/* ========== CSS Variables ========== */
:root {
  --bg-primary: #0a0f1a;
  --bg-secondary: #0d1b2a;
  --bg-tertiary: #1a2a4a;
  --bg-glass: rgba(10, 15, 26, 0.85);
  --bg-glass-light: rgba(26, 42, 74, 0.6);

  --color-primary: #00d4ff;
  --color-primary-dark: #0099cc;
  --color-primary-glow: rgba(0, 212, 255, 0.3);
  --color-success: #00ff88;
  --color-warning: #ffaa00;
  --color-danger: #ff4444;
  --color-info: #666;

  --text-primary: #ffffff;
  --text-secondary: #a0aec0;
  --text-muted: #4a5568;

  --border-color: rgba(255, 255, 255, 0.08);
  --border-glow: rgba(0, 212, 255, 0.2);

  --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.3);
  --shadow-md: 0 4px 16px rgba(0, 0, 0, 0.4);
  --shadow-lg: 0 8px 32px rgba(0, 0, 0, 0.5);
  --shadow-glow: 0 0 20px rgba(0, 212, 255, 0.15);

  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;

  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
  --font-sans: 'Source Han Sans SC', 'Noto Sans SC', -apple-system, sans-serif;
}

/* ========== Global Styles ========== */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

.design-page {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: linear-gradient(135deg, var(--bg-primary) 0%, var(--bg-secondary) 50%, var(--bg-primary) 100%);
  font-family: var(--font-sans);
  color: var(--text-primary);
}

/* ========== Background Particles ========== */
.bg-particles {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  z-index: 0;
  overflow: hidden;
}

.particle {
  position: absolute;
  width: 2px;
  height: 2px;
  background: var(--color-primary);
  border-radius: 50%;
  opacity: 0;
  animation: particleFloat linear infinite;
}

@keyframes particleFloat {
  0% {
    opacity: 0;
    transform: translateY(0) translateX(0);
  }
  10% {
    opacity: 0.6;
  }
  90% {
    opacity: 0.6;
  }
  100% {
    opacity: 0;
    transform: translateY(-100vh) translateX(50px);
  }
}

/* ========== Toolbar ========== */
.toolbar {
  position: relative;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  background: var(--bg-glass);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--border-color);
  box-shadow: var(--shadow-md);
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 20px;
}

.logo-section {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-glow);
}

.logo-icon svg {
  width: 20px;
  height: 20px;
  color: white;
}

.logo-text {
  display: flex;
  flex-direction: column;
}

.logo-title {
  font-family: var(--font-mono);
  font-size: 14px;
  font-weight: 700;
  color: var(--color-primary);
  letter-spacing: 1px;
}

.logo-subtitle {
  font-size: 11px;
  color: var(--text-secondary);
}

.mode-switch {
  display: flex;
  gap: 4px;
  background: rgba(255, 255, 255, 0.05);
  padding: 4px;
  border-radius: var(--radius-md);
}

.mode-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.mode-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-primary);
}

.mode-btn.active {
  background: var(--color-primary);
  color: white;
  box-shadow: var(--shadow-glow);
}

.mode-btn svg {
  width: 16px;
  height: 16px;
}

.toolbar-center {
  display: flex;
  align-items: center;
}

.status-indicators {
  display: flex;
  gap: 16px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 20px;
  border: 1px solid var(--border-color);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;
}

.status-dot.active {
  background: var(--color-success);
  box-shadow: 0 0 8px var(--color-success);
}

.status-dot.warning {
  background: var(--color-warning);
  box-shadow: 0 0 8px var(--color-warning);
}

.status-dot.info {
  background: var(--color-primary);
  box-shadow: 0 0 8px var(--color-primary);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.status-text {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-secondary);
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tool-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.3s ease;
}

.tool-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-primary);
  border-color: var(--color-primary);
  box-shadow: var(--shadow-glow);
}

.tool-btn.active {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
  box-shadow: var(--shadow-glow);
}

.tool-btn svg {
  width: 18px;
  height: 18px;
}

.toolbar-divider {
  width: 1px;
  height: 24px;
  background: var(--border-color);
  margin: 0 4px;
}

/* ========== Main Content ========== */
.main-content {
  flex: 1;
  display: flex;
  position: relative;
  z-index: 1;
  overflow: hidden;
}

/* ========== Sidebar ========== */
.sidebar {
  position: relative;
  width: 380px;
  display: flex;
  flex-direction: column;
  background: var(--bg-glass);
  backdrop-filter: blur(20px);
  border-right: 1px solid var(--border-color);
  z-index: 10;
  transition: width 0.3s ease;
}

.sidebar.collapsed {
  width: 48px;
}

.sidebar-toggle {
  position: absolute;
  top: 50%;
  right: -14px;
  transform: translateY(-50%);
  width: 28px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-glass);
  border: 1px solid var(--border-color);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  color: var(--text-secondary);
  cursor: pointer;
  z-index: 20;
  transition: all 0.3s ease;
}

.sidebar-toggle:hover {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}

.sidebar-toggle svg {
  width: 16px;
  height: 16px;
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

/* Custom Scrollbar */
.sidebar-content::-webkit-scrollbar {
  width: 6px;
}

.sidebar-content::-webkit-scrollbar-track {
  background: transparent;
}

.sidebar-content::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
}

.sidebar-content::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.2);
}

/* ========== Sidebar Sections ========== */
.sidebar-section {
  margin-bottom: 20px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.section-header h3 {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.section-header h3 svg {
  width: 16px;
  height: 16px;
  color: var(--color-primary);
}

.device-count {
  font-family: var(--font-mono);
  font-size: 12px;
  padding: 4px 10px;
  background: var(--color-primary);
  color: white;
  border-radius: 12px;
}

/* ========== Search Box ========== */
.search-box {
  position: relative;
  margin-bottom: 16px;
}

.search-box svg {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  width: 16px;
  height: 16px;
  color: var(--text-muted);
}

.search-box input {
  width: 100%;
  padding: 10px 12px 10px 36px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
  transition: all 0.3s ease;
}

.search-box input::placeholder {
  color: var(--text-muted);
}

.search-box input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-glow);
}

/* ========== Device Cards ========== */
.device-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: calc(100vh - 300px);
  overflow-y: auto;
}

.device-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 14px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.device-card:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: var(--color-primary);
  box-shadow: var(--shadow-glow);
  transform: translateX(4px);
}

.device-card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.device-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  flex-shrink: 0;
}

.device-icon svg {
  width: 20px;
  height: 20px;
  color: white;
}

.device-info {
  flex: 1;
  min-width: 0;
}

.device-name {
  display: block;
  font-weight: 600;
  font-size: 14px;
  color: var(--text-primary);
  margin-bottom: 2px;
}

.device-type {
  font-size: 12px;
  color: var(--text-secondary);
}

.device-coverage {
  font-family: var(--font-mono);
  font-size: 18px;
  font-weight: 700;
}

.device-card-body {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.device-meta {
  display: flex;
  gap: 12px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--text-secondary);
}

.meta-item svg {
  width: 12px;
  height: 12px;
}

.device-actions {
  display: flex;
  gap: 6px;
}

.action-btn {
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.3s ease;
}

.action-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-primary);
}

.action-btn.locate:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.action-btn.enter:hover {
  border-color: var(--color-success);
  color: var(--color-success);
}

.action-btn.edit:hover {
  border-color: var(--color-warning);
  color: var(--color-warning);
}

.action-btn.delete:hover {
  border-color: var(--color-danger);
  color: var(--color-danger);
  background: rgba(255, 68, 68, 0.1);
}

.action-btn svg {
  width: 14px;
  height: 14px;
}

/* ========== Empty State ========== */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
}

.empty-state svg {
  width: 48px;
  height: 48px;
  color: var(--text-muted);
  margin-bottom: 16px;
}

.empty-state p {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.empty-state span {
  font-size: 12px;
  color: var(--text-muted);
}

/* ========== Tab Switcher ========== */
.tab-switcher {
  display: flex;
  gap: 4px;
  background: rgba(255, 255, 255, 0.05);
  padding: 4px;
  border-radius: var(--radius-md);
  margin-bottom: 16px;
}

.tab-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.tab-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-primary);
}

.tab-btn.active {
  background: var(--color-primary);
  color: white;
}

.tab-btn svg {
  width: 14px;
  height: 14px;
}

/* ========== Station Cards ========== */
.station-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: calc(100vh - 350px);
  overflow-y: auto;
  margin-bottom: 16px;
}

.station-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 14px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.station-card:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: var(--color-primary);
}

.station-card.active {
  background: rgba(0, 212, 255, 0.1);
  border-color: var(--color-primary);
  box-shadow: var(--shadow-glow);
}

.station-card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.station-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  border-radius: var(--radius-sm);
}

.station-icon svg {
  width: 20px;
  height: 20px;
  color: white;
}

.station-info {
  flex: 1;
  min-width: 0;
}

.station-name {
  display: block;
  font-weight: 600;
  font-size: 14px;
  color: var(--text-primary);
  margin-bottom: 2px;
}

.station-coord {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-secondary);
}

.station-actions {
  display: flex;
  gap: 6px;
}

/* ========== Antenna Cards ========== */
.antenna-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: calc(100vh - 350px);
  overflow-y: auto;
  margin-bottom: 16px;
}

.antenna-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 14px;
  transition: all 0.3s ease;
}

.antenna-card:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: var(--color-primary);
}

.antenna-card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.antenna-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  flex-shrink: 0;
}

.antenna-icon svg {
  width: 20px;
  height: 20px;
  color: white;
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
  font-weight: 600;
  font-size: 14px;
  color: var(--text-primary);
}

.antenna-badge {
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}

.antenna-badge.omni {
  background: rgba(0, 212, 255, 0.2);
  color: var(--color-primary);
}

.antenna-badge.directional {
  background: rgba(0, 255, 136, 0.2);
  color: var(--color-success);
}

.antenna-badge.smart {
  background: rgba(170, 102, 255, 0.2);
  color: #aa66ff;
}

.antenna-coord {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-secondary);
}

.antenna-actions {
  display: flex;
  gap: 6px;
}

/* ========== Add Button ========== */
.add-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px;
  border: 2px dashed var(--border-color);
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.add-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: rgba(0, 212, 255, 0.05);
}

.add-btn.primary {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: rgba(0, 212, 255, 0.1);
}

.add-btn.primary:hover {
  background: rgba(0, 212, 255, 0.2);
}

.add-btn svg {
  width: 18px;
  height: 18px;
}

/* ========== View Section ========== */
.view-section {
  margin-bottom: 20px;
}

.view-section h4 {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 12px;
}

.preset-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.preset-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.03);
  color: var(--text-secondary);
  font-size: 11px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.preset-btn:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.preset-btn svg {
  width: 20px;
  height: 20px;
}

/* ========== Toggle Switch ========== */
.setting-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-color);
}

.setting-item:last-child {
  border-bottom: none;
}

.toggle-switch {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;
  flex-shrink: 0;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(255, 255, 255, 0.1);
  transition: 0.3s;
  border-radius: 12px;
}

.toggle-slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: 0.3s;
  border-radius: 50%;
}

input:checked + .toggle-slider {
  background-color: var(--color-primary);
  box-shadow: var(--shadow-glow);
}

input:checked + .toggle-slider:before {
  transform: translateX(20px);
}

.setting-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.setting-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.setting-desc {
  font-size: 11px;
  color: var(--text-muted);
}

/* ========== Legend ========== */
.legend-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: var(--text-secondary);
}

.legend-color {
  width: 20px;
  height: 12px;
  border-radius: 3px;
  flex-shrink: 0;
}

/* ========== Tips ========== */
.tips-section {
  margin-top: auto;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
}

.tips-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tip-item {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: var(--text-secondary);
}

.tip-item kbd {
  display: inline-block;
  padding: 3px 8px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-primary);
  min-width: 70px;
  text-align: center;
}

/* ========== Map Wrapper ========== */
.map-wrapper {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.map-container {
  width: 100%;
  height: 100%;
}

.station-container {
  width: 100%;
  height: 100%;
}

.cesium-container {
  width: 100%;
  height: 100%;
}

/* ========== Add Mode Overlay ========== */
.add-mode-overlay {
  position: absolute;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 20;
}

.add-mode-hint {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 20px;
  background: var(--bg-glass);
  backdrop-filter: blur(20px);
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-glow);
  animation: pulse 2s ease-in-out infinite;
}

.add-mode-hint svg {
  width: 20px;
  height: 20px;
  color: var(--color-primary);
}

.add-mode-hint span {
  font-size: 13px;
  color: var(--text-primary);
}

/* ========== Map Coordinates ========== */
.map-coordinates {
  position: absolute;
  bottom: 20px;
  left: 20px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  background: var(--bg-glass);
  backdrop-filter: blur(20px);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  z-index: 10;
}

.coord-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.coord-label {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-muted);
  text-transform: uppercase;
}

.coord-value {
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 600;
  color: var(--color-primary);
}

.coord-divider {
  width: 1px;
  height: 16px;
  background: var(--border-color);
}

/* ========== Coordinate Display (Station Mode) ========== */
.coordinate-display {
  position: absolute;
  bottom: 20px;
  left: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 18px;
  background: var(--bg-glass);
  backdrop-filter: blur(20px);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  z-index: 10;
}

/* ========== Add Panel Overlay ========== */
.add-panel-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.add-panel {
  width: 400px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  animation: slideUp 0.3s ease;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.add-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
}

.add-panel-header h3 {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.add-panel-header h3 svg {
  width: 20px;
  height: 20px;
  color: var(--color-primary);
}

.close-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.3s ease;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-primary);
}

.close-btn svg {
  width: 18px;
  height: 18px;
}

.add-panel-body {
  padding: 24px;
}

.add-panel-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--border-color);
}

/* ========== Dialog Overlay ========== */
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease;
}

.dialog {
  width: 450px;
  max-height: 90vh;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  animation: slideUp 0.3s ease;
  display: flex;
  flex-direction: column;
}

.dialog-lg {
  width: 550px;
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
}

.dialog-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.dialog-body {
  padding: 24px;
  overflow-y: auto;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--border-color);
}

/* ========== Form Styles ========== */
.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.required {
  color: var(--color-danger);
}

.form-input {
  width: 100%;
  padding: 10px 14px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
  transition: all 0.3s ease;
}

.form-input::placeholder {
  color: var(--text-muted);
}

.form-input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-glow);
}

.form-input.disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.form-select {
  width: 100%;
  padding: 10px 14px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
  cursor: pointer;
  transition: all 0.3s ease;
}

.form-select:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-glow);
}

.form-select option {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.form-row {
  display: flex;
  gap: 12px;
}

.form-row .form-group {
  flex: 1;
}

.form-hint {
  display: block;
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 4px;
}

.form-divider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 20px 0;
  font-size: 12px;
  color: var(--text-muted);
}

.form-divider::before,
.form-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border-color);
}

/* ========== File Upload ========== */
.file-upload {
  display: flex;
  align-items: center;
  gap: 12px;
}

.upload-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: rgba(0, 212, 255, 0.1);
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-sm);
  color: var(--color-primary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.upload-btn:hover {
  background: rgba(0, 212, 255, 0.2);
}

.upload-btn svg {
  width: 16px;
  height: 16px;
}

.file-name {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-secondary);
}

/* ========== Buttons ========== */
.btn {
  padding: 10px 20px;
  border: none;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-primary {
  background: var(--color-primary);
  color: white;
}

.btn-primary:hover {
  background: var(--color-primary-dark);
  box-shadow: var(--shadow-glow);
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.15);
  color: var(--text-primary);
}
</style>
