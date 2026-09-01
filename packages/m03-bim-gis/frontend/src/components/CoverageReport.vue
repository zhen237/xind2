<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="$emit('update:visible', $event)"
    title="信号覆盖报告"
    width="680px"
    class="coverage-report-dialog"
  >
    <div class="report-content" ref="reportRef">
      <h2 style="text-align: center; margin-bottom: 24px;">信号覆盖评估报告</h2>

      <div class="report-section">
        <h3>一、仿真参数</h3>
        <table class="report-table">
          <tr>
            <td>传播模型</td><td>{{ modelLabel(params.model) }}</td>
            <td>频率</td><td>{{ params.frequency }} MHz</td>
          </tr>
          <tr>
            <td>发射功率</td><td>{{ params.txPower }} dBm</td>
            <td>天线增益</td><td>{{ params.antennaGain }} dBi</td>
          </tr>
          <tr>
            <td>天线高度</td><td>{{ params.antennaHeight }} m</td>
            <td>接收高度</td><td>{{ params.rxHeight }} m</td>
          </tr>
          <tr>
            <td>覆盖半径</td><td>{{ params.radius }} km</td>
            <td>栅格大小</td><td>{{ params.gridSize }} m</td>
          </tr>
        </table>
      </div>

      <div class="report-section" v-if="result">
        <h3>二、覆盖统计结果</h3>
        <table class="report-table report-table-bordered">
          <thead>
            <tr>
              <th>覆盖等级</th>
              <th>RSRP 范围 (dBm)</th>
              <th>面积 (km²)</th>
              <th>占比</th>
              <th>颜色</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>优秀</td><td>≥ -85</td>
              <td>{{ result.goodArea }}</td><td>{{ result.goodPercent }}%</td>
              <td><span class="color-block" style="background: #00B050"></span></td>
            </tr>
            <tr>
              <td>良好</td><td>-85 ~ -95</td>
              <td>{{ result.fairArea }}</td><td>{{ result.fairPercent }}%</td>
              <td><span class="color-block" style="background: #92D050"></span></td>
            </tr>
            <tr>
              <td>一般</td><td>-95 ~ -105</td>
              <td>{{ result.weakArea }}</td><td>{{ result.weakPercent }}%</td>
              <td><span class="color-block" style="background: #FFC000"></span></td>
            </tr>
            <tr>
              <td>较弱</td><td>-105 ~ -115</td>
              <td>{{ result.blindArea }}</td><td>{{ result.blindPercent }}%</td>
              <td><span class="color-block" style="background: #FF6600"></span></td>
            </tr>
            <tr>
              <td>盲区</td><td>< -115</td>
              <td>-</td><td>-</td>
              <td><span class="color-block" style="background: #FF0000"></span></td>
            </tr>
            <tr class="total-row">
              <td colspan="2">总计</td>
              <td>{{ result.totalArea }}</td>
              <td>100%</td>
              <td></td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="report-section">
        <h3>三、天线设备列表</h3>
        <table class="report-table report-table-bordered">
          <thead>
            <tr>
              <th>序号</th>
              <th>设备名称</th>
              <th>方位角 (°)</th>
              <th>下倾角 (°)</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(antenna, idx) in antennas" :key="antenna.id">
              <td>{{ idx + 1 }}</td>
              <td>{{ antenna.deviceName }}</td>
              <td>{{ antenna.azimuth || 0 }}°</td>
              <td>{{ antenna.downtilt || 0 }}°</td>
            </tr>
            <tr v-if="antennas.length === 0">
              <td colspan="4" style="text-align: center;">无天线设备</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="report-section">
        <h3>四、评估结论</h3>
        <div class="conclusion" v-if="result">
          <p>本次仿真共覆盖面积 <strong>{{ result.totalArea }} km²</strong>，其中：</p>
          <ul>
            <li>良好覆盖区域（RSRP ≥ -95 dBm）占比 <strong>{{ result.goodPercent }}%</strong>；</li>
            <li>一般覆盖区域（-95 ~ -105 dBm）占比 <strong>{{ result.fairPercent }}%</strong>；</li>
            <li>弱覆盖区域（-105 ~ -115 dBm）占比 <strong>{{ result.weakPercent }}%</strong>；</li>
            <li>盲区（RSRP < -115 dBm）占比 <strong>{{ result.blindPercent }}%</strong>。</li>
          </ul>
          <p v-if="parseFloat(result.goodPercent) > 80">
            总体覆盖效果<strong style="color: #67C23A">良好</strong>，满足通信覆盖要求。
          </p>
          <p v-else-if="parseFloat(result.goodPercent) > 60">
            总体覆盖效果<strong style="color: #E6A23C">一般</strong>，建议优化天线参数或增加基站。
          </p>
          <p v-else>
            总体覆盖效果<strong style="color: #F56C6C">较差</strong>，需要调整天线方位角/下倾角或增加基站密度。
          </p>
        </div>
      </div>

      <div class="report-footer">
        <span>报告生成时间: {{ new Date().toLocaleString('zh-CN') }}</span>
      </div>
    </div>

    <template #footer>
      <el-button @click="$emit('update:visible', false)">关闭</el-button>
      <el-button type="primary" :icon="Printer" @click="printReport">打印/导出PDF</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { Printer } from '@element-plus/icons-vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  result: { type: Object, default: null },
  params: { type: Object, default: () => ({}) },
  antennas: { type: Array, default: () => [] }
})

defineEmits(['update:visible'])

function modelLabel(model) {
  const labels = {
    cost231: 'Cost-231 Hata',
    okumura: 'Okumura-Hata',
    freespace: '自由空间'
  }
  return labels[model] || model
}

function printReport() {
  const printContent = document.querySelector('.report-content')
  if (!printContent) return

  const win = window.open('', '_blank')
  win.document.write(`
    <html>
    <head>
      <title>信号覆盖评估报告</title>
      <style>
        body { font-family: 'Microsoft YaHei', sans-serif; padding: 20px; }
        table { border-collapse: collapse; width: 100%; margin: 8px 0; }
        td, th { border: 1px solid #ddd; padding: 6px 10px; font-size: 13px; }
        th { background: #f5f7fa; }
        h3 { margin: 16px 0 8px; }
        .color-block { display: inline-block; width: 20px; height: 12px; border-radius: 2px; }
        .total-row { font-weight: bold; background: #f5f7fa; }
        .report-footer { margin-top: 20px; text-align: right; color: #999; font-size: 12px; }
      </style>
    </head>
    <body>${printContent.innerHTML}</body>
    </html>
  `)
  win.document.close()
  win.print()
}
</script>

<style scoped>
.report-content {
  max-height: 600px;
  overflow-y: auto;
  padding: 0 8px;
}

.report-section {
  margin-bottom: 20px;
}

.report-section h3 {
  font-size: 15px;
  color: #303133;
  border-left: 3px solid #409EFF;
  padding-left: 8px;
  margin-bottom: 8px;
}

.report-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.report-table td {
  padding: 6px 10px;
  border: 1px solid #ebeef5;
}

.report-table-bordered th {
  background: #f5f7fa;
  padding: 6px 10px;
  border: 1px solid #ebeef5;
  text-align: center;
}

.report-table-bordered td {
  text-align: center;
}

.total-row {
  font-weight: bold;
  background: #f5f7fa;
}

.color-block {
  display: inline-block;
  width: 20px;
  height: 12px;
  border-radius: 2px;
}

.conclusion ul {
  padding-left: 20px;
  margin: 8px 0;
}

.conclusion li {
  margin-bottom: 4px;
  font-size: 13px;
}

.report-footer {
  margin-top: 20px;
  text-align: right;
  color: #c0c4cc;
  font-size: 12px;
  border-top: 1px dashed #ebeef5;
  padding-top: 8px;
}
</style>
