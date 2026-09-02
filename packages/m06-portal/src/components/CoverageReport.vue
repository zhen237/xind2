<template>
  <el-dialog
    title="覆盖评估详细报告"
    :model-value="visible"
    width="80%"
    max-width="1200px"
    :close-on-click-modal="false"
    class="report-dialog"
    @update:model-value="$emit('update:visible', $event)"
  >
    <div class="report-content" ref="reportContent">
      <!-- 1. 场所基本信息 -->
      <el-card title="场所基本信息" class="report-section">
        <el-descriptions :column="3" border :data="basicInfo">
          <el-descriptions-item label="场所名称">{{ place.name }}</el-descriptions-item>
          <el-descriptions-item label="场所类型">
            <el-tag :type="getTypeTagType(place.type)">{{ place.type }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="行政区">{{ place.area }}</el-descriptions-item>
          <el-descriptions-item label="责任网格">{{ place.responsibleGrid }}</el-descriptions-item>
          <el-descriptions-item label="维护单位">{{ place.maintenanceUnit }}</el-descriptions-item>
          <el-descriptions-item label="最近测试时间">{{ place.lastTestTime }}</el-descriptions-item>
          <el-descriptions-item label="报告生成时间">{{ reportTime }}</el-descriptions-item>
          <el-descriptions-item label="测试方式">{{ place.testMethod || '路测+定点测试' }}</el-descriptions-item>
          <el-descriptions-item label="测试设备">{{ place.testDevice || '华为C5000' }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 2. 核心覆盖指标 -->
      <el-card title="核心覆盖指标" class="report-section">
        <div class="metrics-grid">
          <div 
            v-for="metric in coreMetrics" 
            :key="metric.key" 
            class="metric-card"
            :class="metric.level"
          >
            <div class="metric-icon" :class="metric.level">
              <component :is="metric.icon" />
            </div>
            <div class="metric-info">
              <div class="metric-label">{{ metric.label }}</div>
              <div class="metric-value">{{ metric.value }} {{ metric.unit }}</div>
              <div class="metric-status">
                <el-tag :type="getMetricTagType(metric.level)">{{ metric.levelText }}</el-tag>
                <span class="target-text">目标: {{ metric.target }}</span>
              </div>
            </div>
          </div>
        </div>
      </el-card>

      <!-- 3. 覆盖趋势图表 -->
      <el-card title="覆盖趋势（近3个月）" class="report-section">
        <div ref="trendChartRef" class="chart-container"></div>
      </el-card>

      <!-- 4. 周边基站列表 -->
      <el-card title="周边基站列表（500米内）" class="report-section">
        <el-table :data="nearbyStations" border stripe>
          <el-table-column prop="name" label="基站名称" />
          <el-table-column prop="distance" label="距离(米)">
            <template #default="scope">
              <el-tag type="info">{{ scope.row.distance }}m</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="operator" label="运营商">
            <template #default="scope">
              <el-tag :type="getOperatorTagType(scope.row.operator)">
                {{ scope.row.operator }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="band" label="频段" />
          <el-table-column prop="rsrp" label="最近RSRP(dBm)">
            <template #default="scope">
              <span :class="getRSRPClass(scope.row.rsrp)">{{ scope.row.rsrp }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="attribution" label="归属">
            <template #default="scope">
              <el-tag :type="scope.row.attribution === '自建' ? 'success' : 'warning'">
                {{ scope.row.attribution }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 5. 问题分析与优化建议 -->
      <el-card 
        title="问题分析与优化建议" 
        class="report-section"
        v-if="hasIssues"
      >
        <div class="analysis-section">
          <div class="issue-item">
            <h4 class="issue-title">🔴 问题描述</h4>
            <ul class="issue-list">
              <li v-for="(issue, index) in issues" :key="index">{{ issue }}</li>
            </ul>
          </div>
          <div class="issue-item">
            <h4 class="issue-title">⚡ 可能原因</h4>
            <ul class="issue-list">
              <li v-for="(reason, index) in reasons" :key="index">{{ reason }}</li>
            </ul>
          </div>
          <div class="issue-item">
            <h4 class="issue-title">✅ 优化建议</h4>
            <ul class="issue-list">
              <li v-for="(suggestion, index) in suggestions" :key="index">{{ suggestion }}</li>
            </ul>
          </div>
          <div class="issue-item">
            <h4 class="issue-title">📈 预期改善效果</h4>
            <p>{{ expectedEffect }}</p>
          </div>
        </div>
      </el-card>

      <el-card 
        title="评估结果" 
        class="report-section"
        v-else
      >
        <div class="success-message">
          <span class="success-icon">🎉</span>
          <p>当前覆盖良好，暂无优化建议</p>
          <p class="success-sub">所有核心指标均已达标，请继续保持</p>
        </div>
      </el-card>

      <!-- 6. 历史工单记录 -->
      <el-card title="历史工单记录（近6个月）" class="report-section">
        <el-table :data="workOrders" border stripe>
          <el-table-column prop="orderNo" label="工单号" />
          <el-table-column prop="createTime" label="发起时间" />
          <el-table-column prop="type" label="问题类型">
            <template #default="scope">
              <el-tag :type="getOrderTypeTagType(scope.row.type)">
                {{ scope.row.type }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="处理状态">
            <template #default="scope">
              <el-tag :type="getOrderStatusTagType(scope.row.status)">
                {{ scope.row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="result" label="处理结果" />
        </el-table>
      </el-card>

      <!-- 7. 测试详情与原始数据追溯 -->
      <el-card title="测试详情与原始数据追溯" class="report-section">
        <div class="test-detail">
          <div class="detail-row">
            <span class="detail-label">测试方式：</span>
            <span class="detail-value">{{ place.testMethod || '路测(DT) + 定点测试(CQT)' }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">测试设备：</span>
            <span class="detail-value">{{ place.testDevice || '华为C5000路测终端' }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">测试样本量：</span>
            <span class="detail-value">{{ place.sampleCount || '1,256 个采样点' }}</span>
          </div>
          <div class="detail-actions">
            <el-button type="primary" @click="downloadLog">
              <el-icon><Download /></el-icon>
              下载原始测试日志
            </el-button>
            <el-button @click="showWeakPoints">
              <el-icon><List /></el-icon>
              查看关键弱覆盖点列表
            </el-button>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 底部操作按钮 -->
    <template #footer>
      <el-button @click="handleClose">关闭</el-button>
      <el-button type="primary" @click="exportPDF">
        <el-icon><Printer /></el-icon>
        导出 PDF
      </el-button>
    </template>

    <!-- 弱覆盖点弹窗 -->
    <el-dialog title="关键弱覆盖点列表" :model-value="showWeakPointsDialog" width="500px" @update:model-value="showWeakPointsDialog = $event">
      <el-table :data="weakPoints" border>
        <el-table-column prop="location" label="位置" />
        <el-table-column prop="rsrp" label="RSRP(dBm)">
          <template #default="scope">
            <span class="poor">{{ scope.row.rsrp }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="sinr" label="SINR(dB)">
          <template #default="scope">
            <span class="poor">{{ scope.row.sinr }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="suggestion" label="优化建议" />
      </el-table>
    </el-dialog>
  </el-dialog>
</template>

<script setup>import { ref, computed, onMounted, watch, onUnmounted, nextTick } from 'vue';
import { ElMessage } from 'element-plus';
import { TrendCharts, Timer, Download, List, Printer, SuccessFilled, Warning, Remove, Phone, Odometer, Histogram } from '@element-plus/icons-vue';
import * as echarts from 'echarts';
const props = defineProps({
 visible: Boolean,
 place: {
 type: Object,
 default: () => ({})
 }
});
const emit = defineEmits(['update:visible']);
const reportContent = ref(null);
const trendChartRef = ref(null);
const showWeakPointsDialog = ref(false);
let trendChart = null;
// 报告生成时间
const reportTime = computed(() => {
 const now = new Date();
 return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')} ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
});
// 基本信息
const basicInfo = computed(() => props.place);
// 核心指标
const coreMetrics = computed(() => {
 const p = props.place;
 return [
 {
 key: 'coverage',
 label: '综合覆盖率',
 value: p.coverage || 0,
 unit: '%',
 target: '≥95%',
 level: getLevel(p.coverage, 95, 90),
 levelText: getLevelText(p.coverage, 95, 90),
 icon: Histogram
 },
 {
 key: 'rsrp',
 label: '平均RSRP',
 value: p.rsrp || 0,
 unit: 'dBm',
 target: '≥-100',
 level: getRSRPLevel(p.rsrp),
 levelText: getRSRPLevelText(p.rsrp),
 icon: Phone
 },
 {
 key: 'sinr',
 label: '平均SINR',
 value: p.sinr || 0,
 unit: 'dB',
 target: '≥20',
 level: getLevel(p.sinr, 20, 15),
 levelText: getLevelText(p.sinr, 20, 15),
 icon: TrendCharts
 },
 {
 key: 'downlink',
 label: '下行速率',
 value: p.downloadSpeed || 0,
 unit: 'Mbps',
 target: '≥300',
 level: getLevel(p.downloadSpeed, 300, 200),
 levelText: getLevelText(p.downloadSpeed, 300, 200),
 icon: Phone
 },
 {
 key: 'uplink',
 label: '上行速率',
 value: p.uploadSpeed || 0,
 unit: 'Mbps',
 target: '≥50',
 level: getLevel(p.uploadSpeed, 50, 30),
 levelText: getLevelText(p.uploadSpeed, 50, 30),
 icon: Phone
 },
 {
 key: 'latency',
 label: '时延',
 value: p.latency || 25,
 unit: 'ms',
 target: '<50',
 level: getLatencyLevel(p.latency),
 levelText: getLatencyLevelText(p.latency),
 icon: Timer
 }
 ];
});
// 判断是否有问题
const hasIssues = computed(() => {
 const p = props.place;
 return (p.coverage < 95 || (p.rsrp && p.rsrp < -100) || p.downloadSpeed < 300);
});
// 问题列表
const issues = computed(() => {
 const p = props.place;
 const list = [];
 if (p.coverage < 95)
 list.push(`综合覆盖率 ${p.coverage}%，未达到目标值 95%`);
 if (p.rsrp && p.rsrp < -100)
 list.push(`平均 RSRP ${p.rsrp} dBm，信号强度较弱`);
 if (p.downloadSpeed < 300)
 list.push(`下行速率 ${p.downloadSpeed} Mbps，未达到目标值 300 Mbps`);
 return list.length > 0 ? list : ['当前无明显问题'];
});
// 可能原因
const reasons = computed(() => {
 return [
 '周边基站距离较远，信号衰减明显',
 '建筑物遮挡导致信号穿透损耗较大',
 '部分频段存在干扰',
 '天线方向角/下倾角需要优化'
 ];
});
// 优化建议
const suggestions = computed(() => {
 return [
 '建议在场所周边新增微基站或分布式天线系统(DAS)',
 '调整周边基站天线参数，增强覆盖',
 '优化频段配置，减少干扰',
 '考虑建设室内分布系统'
 ];
});
// 预期效果
const expectedEffect = computed(() => {
 return '实施上述优化措施后，预计综合覆盖率可提升至 98% 以上，RSRP 改善 5-10 dBm，下行速率提升至 400 Mbps 以上。';
});
// 周边基站数据
const nearbyStations = computed(() => {
 return props.place.nearbyStations || [
 { name: '东单基站-A', distance: 150, operator: '联通', band: '1800MHz', rsrp: -85, attribution: '自建' },
 { name: '王府井基站-B', distance: 280, operator: '移动', band: '2100MHz', rsrp: -92, attribution: '自建' },
 { name: '建国门基站', distance: 420, operator: '电信', band: '800MHz', rsrp: -98, attribution: '共享' },
 { name: '朝阳门基站', distance: 480, operator: '联通', band: '1800MHz', rsrp: -102, attribution: '自建' }
 ];
});
// 工单数据
const workOrders = computed(() => {
 return props.place.workOrders || [
 { orderNo: 'WO-20240115-001', createTime: '2024-01-15 09:30', type: '覆盖优化', status: '已完成', result: '天线调整完成，覆盖改善' },
 { orderNo: 'WO-20240108-003', createTime: '2024-01-08 14:20', type: '故障处理', status: '已完成', result: '信号干扰排除' },
 { orderNo: 'WO-20240102-005', createTime: '2024-01-02 10:00', type: '站点勘察', status: '进行中', result: '待制定优化方案' }
 ];
});
// 弱覆盖点数据
const weakPoints = ref([
 { location: '门诊楼地下一层', rsrp: -115, sinr: 5, suggestion: '建议新增室内天线' },
 { location: '住院部B栋3层', rsrp: -108, sinr: 8, suggestion: '调整天线方向' },
 { location: '停车场B2层', rsrp: -120, sinr: 3, suggestion: '安装DAS系统' }
]);
// 辅助函数
const getLevel = (value, good, medium) => {
 if (value >= good)
 return 'good';
 if (value >= medium)
 return 'medium';
 return 'poor';
};
const getLevelText = (value, good, medium) => {
 if (value >= good)
 return '优秀';
 if (value >= medium)
 return '良好';
 return '差';
};
const getRSRPLevel = (rsrp) => {
 if (!rsrp)
 return 'poor';
 if (rsrp >= -95)
 return 'good';
 if (rsrp >= -105)
 return 'medium';
 return 'poor';
};
const getRSRPLevelText = (rsrp) => {
 if (!rsrp)
 return '未知';
 if (rsrp >= -95)
 return '优秀';
 if (rsrp >= -105)
 return '良好';
 return '差';
};
const getLatencyLevel = (latency) => {
 if (!latency)
 return 'good';
 if (latency < 30)
 return 'good';
 if (latency < 50)
 return 'medium';
 return 'poor';
};
const getLatencyLevelText = (latency) => {
 if (!latency)
 return '未知';
 if (latency < 30)
 return '优秀';
 if (latency < 50)
 return '良好';
 return '差';
};
const getTypeTagType = (type) => {
 const map = { '医院': 'danger', '交通枢纽': 'warning', '场馆': 'success', '高校': 'primary' };
 return map[type] || 'info';
};
const getMetricTagType = (level) => {
 const map = { 'good': 'success', 'medium': 'warning', 'poor': 'danger' };
 return map[level] || 'info';
};
const getOperatorTagType = (operator) => {
 const map = { '联通': 'primary', '移动': 'success', '电信': 'warning' };
 return map[operator] || 'info';
};
const getRSRPClass = (rsrp) => {
 if (rsrp >= -95)
 return 'good';
 if (rsrp >= -105)
 return 'medium';
 return 'poor';
};
const getOrderTypeTagType = (type) => {
 const map = { '覆盖优化': 'primary', '故障处理': 'danger', '站点勘察': 'warning', '设备更换': 'info' };
 return map[type] || 'info';
};
const getOrderStatusTagType = (status) => {
 const map = { '已完成': 'success', '进行中': 'warning', '待处理': 'info', '已关闭': 'danger' };
 return map[status] || 'info';
};
// 方法
const initTrendChart = () => {
 console.log('initTrendChart called');
 if (!trendChartRef.value) {
 console.log('trendChartRef.value is null');
 return;
 }
 console.log('trendChartRef.value found, height:', trendChartRef.value.clientHeight);
 if (trendChartRef.value.clientHeight === 0) {
 console.log('Container has zero height, retrying in 100ms');
 setTimeout(initTrendChart, 100);
 return;
 }
 if (trendChart) {
 trendChart.dispose();
 }
 trendChart = echarts.init(trendChartRef.value);
 const months = ['1月', '2月', '3月'];
 const trendData = props.place.trendData || {
 coverage: [92, 95, 98],
 rsrp: [-98, -95, -85],
 sinr: [18, 22, 25],
 downlink: [250, 280, 350]
 };
 console.log('trendData:', trendData);
 const option = {
 tooltip: {
 trigger: 'axis',
 axisPointer: { type: 'cross' }
 },
 legend: {
 data: ['综合覆盖率(%)', 'RSRP(dBm)', 'SINR(dB)', '下行速率(Mbps)']
 },
 grid: {
 left: '3%',
 right: '4%',
 bottom: '3%',
 containLabel: true
 },
 xAxis: {
 type: 'category',
 boundaryGap: false,
 data: months
 },
 yAxis: [
 {
 type: 'value',
 name: '覆盖率(%)/速率(Mbps)',
 position: 'left',
 axisLabel: { formatter: '{value}' }
 },
 {
 type: 'value',
 name: 'RSRP/SINR',
 position: 'right',
 axisLabel: { formatter: '{value}' }
 }
 ],
 series: [
 {
 name: '综合覆盖率(%)',
 type: 'line',
 smooth: true,
 data: trendData.coverage,
 lineStyle: { color: '#67c23a' },
 itemStyle: { color: '#67c23a' }
 },
 {
 name: 'RSRP(dBm)',
 type: 'line',
 smooth: true,
 yAxisIndex: 1,
 data: trendData.rsrp,
 lineStyle: { color: '#409eff' },
 itemStyle: { color: '#409eff' }
 },
 {
 name: 'SINR(dB)',
 type: 'line',
 smooth: true,
 yAxisIndex: 1,
 data: trendData.sinr,
 lineStyle: { color: '#e6a23c' },
 itemStyle: { color: '#e6a23c' }
 },
 {
 name: '下行速率(Mbps)',
 type: 'line',
 smooth: true,
 data: trendData.downlink,
 lineStyle: { color: '#f56c6c' },
 itemStyle: { color: '#f56c6c' }
 }
 ]
 };
 trendChart.setOption(option);
 trendChart.resize();
 console.log('chart initialized');
};
const handleResize = () => {
 if (trendChart) {
 trendChart.resize();
 }
};
const downloadLog = () => {
 ElMessage.info('功能开发中，敬请期待');
};
const showWeakPoints = () => {
 showWeakPointsDialog.value = true;
};
const exportPDF = () => {
 ElMessage.info('功能开发中，敬请期待');
};
const handleClose = () => {
 emit('update:visible', false);
};
// 生命周期
onMounted(() => {
 window.addEventListener('resize', handleResize);
});
onUnmounted(() => {
 window.removeEventListener('resize', handleResize);
 if (trendChart) {
 trendChart.dispose();
 }
});
watch(() => props.visible, (newVal) => {
 if (newVal) {
 nextTick(() => {
 setTimeout(() => {
 initTrendChart();
 }, 300);
 });
 }
});
</script>

<style scoped>
.report-dialog {
  max-height: 90vh;
}

.report-content {
  max-height: 70vh;
  overflow-y: auto;
  padding-right: 10px;
}

.report-section {
  margin-bottom: 20px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.metric-card {
  display: flex;
  align-items: center;
  padding: 16px;
  border-radius: 8px;
  background: #fafafa;
  transition: all 0.3s;
}

.metric-card.good {
  border-left: 4px solid #67c23a;
}

.metric-card.medium {
  border-left: 4px solid #e6a23c;
}

.metric-card.poor {
  border-left: 4px solid #f56c6c;
}

.metric-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 16px;
  font-size: 24px;
}

.metric-icon.good {
  background: rgba(103, 194, 58, 0.1);
  color: #67c23a;
}

.metric-icon.medium {
  background: rgba(230, 162, 60, 0.1);
  color: #e6a23c;
}

.metric-icon.poor {
  background: rgba(245, 108, 108, 0.1);
  color: #f56c6c;
}

.metric-info {
  flex: 1;
}

.metric-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 4px;
}

.metric-value {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}

.metric-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.target-text {
  font-size: 12px;
  color: #909399;
}

.chart-container {
  min-height: 350px;
  height: 350px;
  width: 100%;
  background: #fafafa;
  border-radius: 8px;
  padding: 10px;
  box-sizing: border-box;
}

.analysis-section {
  background: #fefefe;
  border-radius: 8px;
  padding: 16px;
}

.issue-item {
  margin-bottom: 16px;
}

.issue-item:last-child {
  margin-bottom: 0;
}

.issue-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}

.issue-list {
  margin: 0;
  padding-left: 20px;
}

.issue-list li {
  margin-bottom: 6px;
  color: #606266;
  font-size: 13px;
}

.expected-effect {
  font-size: 13px;
  color: #606266;
}

.success-message {
  text-align: center;
  padding: 30px;
}

.success-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.success-message p {
  font-size: 16px;
  color: #67c23a;
  margin: 8px 0;
}

.success-sub {
  font-size: 13px;
  color: #909399 !important;
}

.test-detail {
  padding: 16px;
  background: #fafafa;
  border-radius: 8px;
}

.detail-row {
  display: flex;
  margin-bottom: 12px;
}

.detail-row:last-child {
  margin-bottom: 16px;
}

.detail-label {
  width: 100px;
  font-weight: 500;
  color: #909399;
}

.detail-value {
  color: #303133;
}

.detail-actions {
  display: flex;
  gap: 12px;
}

.weak-points-table {
  width: 100%;
}

.poor {
  color: #f56c6c;
}

.medium {
  color: #e6a23c;
}

.good {
  color: #67c23a;
}

/* 滚动条样式 */
.report-content::-webkit-scrollbar {
  width: 6px;
}

.report-content::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.report-content::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.report-content::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
</style>