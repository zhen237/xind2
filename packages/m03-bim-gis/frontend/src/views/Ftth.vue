<template>
  <div class="ftth-page">
    <div class="page-header">
      <div class="header-row">
        <h2>FTTH 光交箱与光路交付物</h2>
        <el-select
          v-model="currentTag"
          size="small"
          class="dataset-select"
          placeholder="选择真实数据集"
          @change="onDatasetChange"
        >
          <el-option
            v-for="d in datasets"
            :key="d.tag"
            :label="d.label"
            :value="d.tag"
          />
        </el-select>
        <el-button
          size="small"
          type="primary"
          :loading="refreshing"
          @click="refreshFromBackend"
        >
          从后端刷新
        </el-button>
        <span
          class="source-badge"
          :class="{ static: dataSource === 'static' }"
        >
          {{ dataSource === 'backend' ? '后端实时' : '静态缓存' }}
        </span>
      </div>
      <p
        v-if="data"
        class="subtitle"
      >
        数据源: {{ data.source }} ｜ 生成时间: {{ data.generated_at }}
        <span class="ds-tag">（{{ currentTag || '根目录默认' }}）</span>
        <span
          v-if="lastSynced"
          class="ds-tag"
        >｜ 最近同步: {{ lastSynced }}</span>
      </p>
    </div>

    <!-- 统计卡片 -->
    <el-row
      v-if="data"
      :gutter="16"
      class="stat-row"
    >
      <el-col
        v-for="c in statCards"
        :key="c.label"
        :span="4"
      >
        <el-card
          shadow="hover"
          class="stat-card"
        >
          <div class="stat-value">
            {{ c.value }}
          </div>
          <div class="stat-label">
            {{ c.label }}
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 数据自检 (行业标准校验规则, S3 复用) -->
    <el-card
      v-if="validation"
      shadow="never"
      class="block-card"
    >
      <template #header>
        <span>数据自检 · 行业标准校验规则（S3 设计审查规则复用）</span>
      </template>
      <div class="check-summary">
        <el-progress
          type="dashboard"
          :percentage="validation.summary.passed_rate"
          :color="validation.summary.failed > 0 ? '#e6a23c' : '#67c23a'"
          :width="120"
        />
        <div class="check-meta">
          <div class="check-line">
            <b>通过率 {{ validation.summary.passed_rate }}%</b>
            ｜ 通过 <b>{{ validation.summary.passed }}</b> / 共 {{ validation.summary.total }}
            ｜ 失败 <b class="fail">{{ validation.summary.failed }}</b>
            ｜ 警告 <b class="warn">{{ validation.summary.warned }}</b>
            ｜ 跳过 {{ validation.summary.skipped }}
          </div>
          <div class="check-groups">
            <span
              v-for="(g, name) in validation.groups"
              :key="name"
              class="group-chip"
              :class="{ bad: g.fail > 0, warn: g.warn > 0 && g.fail === 0 }"
            >{{ name }}：{{ g.pass }}✓ / {{ g.fail }}✗ / {{ g.warn }}⚠</span>
          </div>
        </div>
      </div>
      <el-collapse
        v-if="issues.length"
        class="check-issues"
      >
        <el-collapse-item
          v-for="r in issues"
          :key="r.id"
          :name="r.id"
        >
          <template #title>
            <span class="issue-title">
              <el-tag
                size="small"
                :type="r.status === 'fail' ? 'danger' : 'warning'"
              >
                {{ r.status === 'fail' ? '失败' : '警告' }}
              </el-tag>
              <span
                v-if="getRuleInterp(r.id)"
                class="issue-human"
              >{{ getRuleInterp(r.id).title }}</span>
              <span class="issue-id">{{ r.id }} {{ r.name }}</span>
            </span>
          </template>
          <div
            v-if="getRuleInterp(r.id)"
            class="issue-meaning"
          >
            <b>含义：</b>{{ getRuleInterp(r.id).meaning }}
          </div>
          <div
            v-if="getRuleInterp(r.id)"
            class="issue-fix"
          >
            <b>修复：</b>{{ getRuleInterp(r.id).fix }}
          </div>
          <div class="issue-detail">
            <b>详情：</b>{{ r.detail }}
          </div>
          <div
            v-if="r.suggestion"
            class="issue-suggestion"
          >
            <b>建议：</b>{{ r.suggestion }}
          </div>
          <div
            v-if="r.samples && r.samples.length"
            class="issue-samples"
          >
            <div
              v-for="(s, i) in r.samples"
              :key="i"
              class="sample"
            >
              {{ s }}
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>
      <div
        v-else
        class="all-pass"
      >
        全部规则通过 ✓
      </div>
    </el-card>

    <el-row :gutter="16">
      <!-- 箱体清单 -->
      <el-col :span="14">
        <el-card
          shadow="never"
          class="block-card"
        >
          <template #header>
            <span>箱体清单</span>
          </template>
          <div class="filter-bar">
            <el-radio-group v-model="typeFilter">
              <el-radio-button label="all">
                全部
              </el-radio-button>
              <el-radio-button label="BPE">
                BPE
              </el-radio-button>
              <el-radio-button label="PBO">
                PBO
              </el-radio-button>
            </el-radio-group>
            <el-input
              v-model="searchText"
              placeholder="搜索箱体编码"
              clearable
              size="small"
              class="search"
            />
          </div>
          <el-table
            :data="filteredBoites"
            height="430"
            size="small"
            stripe
          >
            <el-table-column
              prop="code"
              label="编码"
              width="180"
            />
            <el-table-column
              prop="type"
              label="类型"
              width="80"
            />
            <el-table-column
              prop="capacite_fo"
              label="容量FO"
              width="90"
            />
            <el-table-column
              prop="fonction"
              label="功能"
              width="100"
            />
            <el-table-column
              prop="pm"
              label="归属PM"
              width="140"
            />
            <el-table-column
              prop="logements"
              label="户数"
              width="80"
            />
            <el-table-column
              prop="ptec"
              label="PTEC"
              width="120"
            />
          </el-table>
        </el-card>
      </el-col>

      <!-- 图表 -->
      <el-col :span="10">
        <el-card
          shadow="never"
          class="block-card"
        >
          <template #header>
            <span>按 PM 分布</span>
          </template>
          <div
            ref="barEl"
            class="chart"
          />
        </el-card>
        <el-card
          shadow="never"
          class="block-card"
        >
          <template #header>
            <span>类型占比</span>
          </template>
          <div
            ref="pieEl"
            class="chart"
          />
        </el-card>
      </el-col>
    </el-row>

    <!-- 3D 地球 + 智能规划 -->
    <el-card
      shadow="never"
      class="block-card"
    >
      <template #header>
        <span>3D 可视化</span>
      </template>
      <el-tabs>
        <el-tab-pane label="3D 地球总览（真实竣工）">
          <FtthMap
            :boites="data ? data.boites : []"
            :cables="data ? data.cables : []"
            :sites="data ? data.sites : []"
          />
        </el-tab-pane>
        <el-tab-pane
          label="智能规划（AI 辅助设计）"
          lazy
        >
          <FtthPlanner />
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 交付物数据预览（F3: xlsx 在线预览, 网页表格替代下载） -->
    <FtthTables
      v-if="data"
      :boites="data.boites"
      :cables="data.cables"
    />

    <!-- 交付物说明 -->
    <el-card
      shadow="never"
      class="block-card"
    >
      <template #header>
        <span>官方交付物（在 QGIS 插件「FTTH 官方交付物」按钮一键导出 xlsx）</span>
      </template>
      <el-row :gutter="16">
        <el-col
          v-for="d in deliverables"
          :key="d.title"
          :span="6"
        >
          <div class="deliver-item">
            <div class="deliver-title">
              {{ d.title }}
            </div>
            <div class="deliver-desc">
              {{ d.desc }}
            </div>
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import FtthMap from '@/components/FtthMap.vue'
import FtthPlanner from '@/components/FtthPlanner.vue'
import FtthTables from '@/components/FtthTables.vue'
import { useFtthDataset } from '@/composables/useFtthDataset.js'
import { ftthAPI } from '@/utils/request.js'

const { currentTag, datasets, loadIndex, path } = useFtthDataset()

const data = ref(null)
const validation = ref(null)
const typeFilter = ref('all')
const searchText = ref('')
const barEl = ref(null)
const pieEl = ref(null)
// 数据来源标记：backend=后端实时（QGIS 同步结果），static=public/datasets 静态回退
const dataSource = ref('static')
const refreshing = ref(false)
const lastSynced = ref('')

// 规则人话解读表（按 FTTH 竣工标准常见规则维护，key=规则 id）
const RULE_INTERPRETATION = {
  '4.1a': {
    title: 'IMB 字段缺失',
    meaning: '楼栋（IMB）图层缺少规范字段 CODE_VOIE（街道编码），多为 Shapefile 10 字符截断或字段别名映射不一致导致。',
    fix: '在 QGIS 源数据中补全 CODE_VOIE 字段；若字段名被截断，请检查字段别名映射。',
  },
  '4.2a': {
    title: 'BOITE 字段缺失',
    meaning: '光交箱（BOITE）图层存在规范字段为空或字段名缺失的情况。',
    fix: '回填空值字段；若字段名缺失，检查 Shapefile 字段截断与别名映射。',
  },
  '4.3a': {
    title: '光缆光纤数为空',
    meaning: '光缆（CABLE）图层中部分记录的光纤使用数/可用数字段为空。',
    fix: '在 QGIS 中回填 NB_FIBRE_UTIL、NB_FIBRE_DISP 字段值。',
  },
  '4.4a': {
    title: 'PTECH 字段缺失',
    meaning: '技术点（PTECH）图层存在规范字段为空或字段名缺失的情况。',
    fix: '回填空值字段；若字段名缺失，检查字段别名映射。',
  },
  '4.6a': {
    title: 'ZPM 字段缺失',
    meaning: '配线点（ZPM）图层缺少规范字段 REF_PM，多为字段截断或别名映射导致。',
    fix: '补全 REF_PM 字段，或检查字段别名映射。',
  },
  '5.4': {
    title: '缆端点引用异常',
    meaning: '有光缆端点指向了不存在的箱体/站点（幽灵引用），或节点未被任何配线缆连接。',
    fix: '核对并修正缆端点 CODE，或补连配线缆。',
  },
  '6.2': {
    title: 'ZPM 可能重叠',
    meaning: '两个 ZPM 多边形的包围盒重叠，可能是真实相交，也可能只是相切。',
    fix: '用精确几何工具（如 shapely）判定；若为真实相交则调整 ZPM 边界。',
  },
  '6.3': {
    title: 'SITE 必须落入 ZPM',
    meaning: '站点（SITE/PM）坐标未落在其归属的 ZPM 多边形内。',
    fix: '核对 SITE 坐标或 ZPM 边界，确保归属关系正确。',
  },
  '6.5': {
    title: '配线缆端点越界',
    meaning: '配线缆（DISTRIBUTION）端点超出了归属 ZPM 多边形范围。',
    fix: '核对缆端点坐标，确保落在对应 ZPM 多边形内。',
  },
  '6.6': {
    title: '缆端点与节点不重合',
    meaning: '光缆端点坐标与引用的箱体/站点坐标不一致，或存在 ORIGINE=EXTREMITE 的自环。',
    fix: '修正端点坐标使其与对应节点重合；删除自环缆。',
  },
}

function getRuleInterp(ruleId) {
  return RULE_INTERPRETATION[ruleId] || null
}

// 数据自检：仅展示失败/警告项，失败置顶
const issues = computed(() => {
  if (!validation.value) return []
  const severity = { fail: 0, warn: 1 }
  return validation.value.rules
    .filter((r) => r.status === 'fail' || r.status === 'warn')
    .sort((a, b) => severity[a.status] - severity[b.status] || a.id.localeCompare(b.id))
})

const statCards = computed(() => {
  if (!data.value) return []
  const s = data.value.summary
  const boites = data.value.boites
  const bpe = boites.filter((b) => b.type === 'BPE').length
  const pbo = boites.filter((b) => b.type === 'PBO').length
  const log = boites.reduce((a, b) => a + (b.logements || 0), 0)
  return [
    { label: '箱体', value: s.BOITE },
    { label: '住户', value: log },
    { label: 'BPE', value: bpe },
    { label: 'PBO', value: pbo },
    { label: 'IMB', value: s.IMB },
    { label: '缆段', value: s.CABLE },
  ]
})

const filteredBoites = computed(() => {
  if (!data.value) return []
  let list = data.value.boites
  if (typeFilter.value !== 'all') list = list.filter((b) => b.type === typeFilter.value)
  if (searchText.value) {
    list = list.filter((b) => b.code.includes(searchText.value))
  }
  return list
})

const deliverables = [
  { title: '光交箱汇总', desc: 'Sommaire + 每箱体明细 sheet（容量/功能/PTEC/经过缆段）' },
  { title: '光路由表', desc: 'Routes Optiques：PM→箱体逐段光缆与长度' },
  { title: '机柜熔接盘图', desc: 'Plan de Baie：24 芯位熔接盘占用矩阵' },
  { title: '系统图', desc: 'Synoptique：各 PM 光路系统图' },
]

async function loadData(fromBackend = true) {
  const tag = currentTag.value
  if (fromBackend && tag) {
    try {
      const res = await ftthAPI.getDataset(tag)
      if (res.code === 200 && res.data && res.data.data) {
        data.value = res.data.data
        validation.value = res.data.validation || null
        dataSource.value = 'backend'
        lastSynced.value = new Date().toLocaleString('zh-CN')
        await nextTick()
        renderCharts()
        return
      }
    } catch (e) {
      // 后端不可达（未启动 / 跨域被拦）→ 回退静态文件
      console.warn('FTTH 后端拉取失败，回退静态文件', e)
    }
  }
  // 回退：直接读 public/datasets/{tag}/ 静态 JSON
  try {
    const [dRes, vRes] = await Promise.all([
      fetch(path('ftth-data.json')),
      fetch(path('ftth-validation.json')),
    ])
    if (!dRes.ok) throw new Error('HTTP ' + dRes.status)
    data.value = await dRes.json()
    if (vRes.ok) validation.value = await vRes.json()
    dataSource.value = 'static'
    await nextTick()
    renderCharts()
  } catch (e) {
    console.error('FTTH 数据加载失败', e)
  }
}

// 切换数据集下拉
async function onDatasetChange(tag) {
  currentTag.value = tag
  await loadData(true)
}

// 手动「从后端刷新」：强制走后端，失败时提示并保留当前视图
async function refreshFromBackend() {
  if (!currentTag.value) {
    ElMessage.warning('请先选择数据集')
    return
  }
  refreshing.value = true
  try {
    const res = await ftthAPI.getDataset(currentTag.value)
    if (res.code === 200 && res.data && res.data.data) {
      data.value = res.data.data
      validation.value = res.data.validation || null
      dataSource.value = 'backend'
      lastSynced.value = new Date().toLocaleString('zh-CN')
      ElMessage.success('已从后端刷新最新成果')
      await nextTick()
      renderCharts()
    } else {
      ElMessage.error('后端无该数据集（' + (res.message || '未知错误') + '）')
    }
  } catch (e) {
    ElMessage.error('后端刷新失败：' + (e.message || e))
  } finally {
    refreshing.value = false
  }
}

function renderCharts() {
  if (!data.value) return
  const pmGroups = {}
  for (const b of data.value.boites) {
    pmGroups[b.pm] = pmGroups[b.pm] || { BPE: 0, PBO: 0 }
    pmGroups[b.pm][b.type] = (pmGroups[b.pm][b.type] || 0) + 1
  }
  const pms = Object.keys(pmGroups)
  const needRotate = pms.length > 4
  if (barEl.value) {
    const bar = echarts.init(barEl.value)
    bar.setOption({
      tooltip: {},
      legend: { data: ['BPE', 'PBO'] },
      grid: { left: '3%', right: '4%', bottom: needRotate ? 60 : 30, containLabel: true },
      xAxis: {
        type: 'category',
        data: pms,
        axisLabel: { rotate: needRotate ? 30 : 0, interval: 0 },
      },
      yAxis: { type: 'value' },
      series: [
        { name: 'BPE', type: 'bar', data: pms.map((p) => pmGroups[p].BPE || 0) },
        { name: 'PBO', type: 'bar', data: pms.map((p) => pmGroups[p].PBO || 0) },
      ],
    })
  }
  const bpe = data.value.boites.filter((b) => b.type === 'BPE').length
  const pbo = data.value.boites.filter((b) => b.type === 'PBO').length
  if (pieEl.value) {
    const pie = echarts.init(pieEl.value)
    pie.setOption({
      tooltip: {},
      legend: { data: ['BPE', 'PBO'] },
      series: [
        {
          type: 'pie',
          radius: '60%',
          data: [
            { name: 'BPE', value: bpe },
            { name: 'PBO', value: pbo },
          ],
        },
      ],
    })
  }
}

onMounted(async () => {
  await loadIndex()
  await loadData()
})
</script>

<style scoped>
/* ── FTTH 页面浅色主题（覆盖全局 dark theme）──────── */
.ftth-page {
  padding: 16px;
  background: #f5f7fa;
  color: #1a1a2e;
  min-height: 100vh;
}
.ftth-page h2 { margin: 0 0 4px; color: #1a1a2e; }
.ftth-page .subtitle { color: #606266; font-size: 12px; margin: 0 0 12px; }

/* El-Card 浅色 */
.ftth-page :deep(.el-card) {
  background-color: #ffffff !important;
  border-color: #e4e7ed !important;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06) !important;
}
.ftth-page :deep(.el-card__header) {
  border-bottom-color: #e4e7ed !important;
  color: #303133;
}

/* El-Table 浅色 */
.ftth-page :deep(.el-table) {
  --el-table-bg-color: #fff;
  --el-table-tr-bg-color: #fff;
  --el-table-header-bg-color: #f5f7fa;
  --el-table-row-hover-bg-color: #ecf5ff;
  --el-table-border-color: #ebeef5;
  --el-table-text-color: #303133;
  --el-table-header-text-color: #1a1a2e;
  color: #303133;
}
.ftth-page :deep(.el-table th) {
  background-color: #f5f7fa !important;
  color: #1a1a2e !important;
}
.ftth-page :deep(.el-table td),
.ftth-page :deep(.el-table th) {
  border-bottom-color: #ebeef5;
}

/* El-Button */
.ftth-page :deep(.el-button) {
  --el-button-bg-color: #fff;
  --el-button-border-color: #dcdfe6;
  --el-button-text-color: #606266;
  --el-button-hover-bg-color: #ecf5ff;
  --el-button-hover-border-color: #409eff;
  --el-button-hover-text-color: #409eff;
}
.ftth-page :deep(.el-button--primary) {
  --el-button-bg-color: #409eff;
  --el-button-border-color: #409eff;
  --el-button-text-color: #fff;
  --el-button-hover-bg-color: #66b1ff;
  --el-button-hover-border-color: #66b1ff;
}

/* El-Input / Select */
.ftth-page :deep(.el-input__wrapper) {
  background-color: #fff !important;
  border-color: #dcdfe6 !important;
  box-shadow: none !important;
}
.ftth-page :deep(.el-input__inner) { color: #303133 !important; }
.ftth-page :deep(.el-input__inner::placeholder) { color: #c0c4cc !important; }
.ftth-page :deep(.el-select-dropdown) {
  background-color: #fff !important;
  border-color: #dcdfe6 !important;
}
.ftth-page :deep(.el-select-dropdown__item) { color: #606266 !important; }
.ftth-page :deep(.el-select-dropdown__item.hover),
.ftth-page :deep(.el-select-dropdown__item:hover) {
  background-color: #ecf5ff !important;
  color: #409eff !important;
}

/* El-Tabs */
.ftth-page :deep(.el-tabs__item) { color: #606266 !important; }
.ftth-page :deep(.el-tabs__item.is-active) { color: #409eff !important; }
.ftth-page :deep(.el-tabs__active-bar) { background-color: #409eff !important; }
.ftth-page :deep(.el-tabs__header) {
  border-bottom-color: #e4e7ed !important;
}

/* El-Tag */
.ftth-page :deep(.el-tag) {
  background-color: #ecf5ff !important;
  border-color: #b3d8ff !important;
  color: #409eff !important;
}
.ftth-page :deep(.el-tag--success) {
  background-color: #f0f9eb !important;
  border-color: #c2e7b0 !important;
  color: #67c23a !important;
}
.ftth-page :deep(.el-tag--warning) {
  background-color: #fdf6ec !important;
  border-color: #faecd8 !important;
  color: #e6a23c !important;
}
.ftth-page :deep(.el-tag--danger) {
  background-color: #fef0f0 !important;
  border-color: #fde2e2 !important;
  color: #f56c6c !important;
}

/* El-Radio */
.ftth-page :deep(.el-radio-button__inner) {
  background-color: #fff;
  border-color: #dcdfe6;
  color: #606266;
}
.ftth-page :deep(.el-radio-button__original:checked + .el-radio-button__inner) {
  background-color: #409eff;
  border-color: #409eff;
  color: #fff;
  box-shadow: -1px 0 0 0 #409eff;
}

/* 统计卡片文字 */
.stat-value { font-size: 24px; font-weight: 600; color: #1a1a2e; }
.stat-label { color: #909399; font-size: 12px; margin-top: 4px; }

/* 自检区域 */
.issue-suggestion {
  font-size: 13px; color: #409eff;
  background: #ecf5ff; border: 1px solid #d9ecff;
  border-radius: 4px; padding: 6px 10px; margin: 6px 0; line-height: 1.6;
}
.issue-detail { font-size: 13px; color: #606266; line-height: 1.6; }
.issue-samples {
  margin-top: 6px; max-height: 160px; overflow: auto;
  background: #fafafa; border-radius: 4px; padding: 6px 10px;
}
.issue-samples .sample { font-family: monospace; font-size: 12px; color: #909399; padding: 1px 0; }
.all-pass { color: #67c23a; font-weight: 600; }

.group-chip {
  font-size: 12px; padding: 3px 10px; border-radius: 12px;
  background: #f0f9eb; color: #67c23a; border: 1px solid #e1f3d8;
}
.group-chip.bad { background: #fef0f0; color: #f56c6c; border-color: #fde2e2; }
.group-chip.warn { background: #fdf6ec; color: #e6a23c; border-color: #faecd8; }

.check-line .fail { color: #f56c6c; }
.check-line .warn { color: #e6a23c; }

.deliver-item {
  border: 1px solid #ebeef5; border-radius: 6px; padding: 12px;
  background: #fff;
}
.deliver-title { font-weight: 600; margin-bottom: 6px; color: #303133; }
.deliver-desc { font-size: 12px; color: #909399; }

.ds-tag { color: #409eff; font-weight: 600; }
.source-badge { font-size: 11px; padding: 2px 8px; border-radius: 10px; }
.source-badge.static { background: #f4f4f5; color: #909399; }
.source-badge:not(.static) { background: #ecf5ff; color: #409eff; }

.page-header h2 { margin: 0 0 4px; }
.header-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.dataset-select { width: 280px; flex: none; }
.stat-row { margin-bottom: 16px; }
.stat-card { text-align: center; }
.block-card { margin-bottom: 16px; }
.chart { height: 240px; }
.filter-bar { display: flex; justify-content: space-between; margin-bottom: 12px; }
.search { width: 200px; }
.check-summary { display: flex; align-items: center; gap: 24px; margin-bottom: 12px; }
.check-meta { flex: 1; }
.check-line { font-size: 13px; margin-bottom: 10px; }
.check-groups { display: flex; flex-wrap: wrap; gap: 8px; }
.issue-title { display: inline-flex; align-items: center; gap: 8px; }
.issue-human { font-weight: 600; color: #303133; }
.issue-id { color: #909399; font-size: 12px; }
.issue-meaning { font-size: 13px; color: #606266; line-height: 1.6; margin: 6px 0; }
.issue-fix {
  font-size: 13px; color: #409eff;
  background: #ecf5ff; border: 1px solid #d9ecff;
  border-radius: 4px; padding: 6px 10px; margin: 6px 0; line-height: 1.6;
}
</style>
