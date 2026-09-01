<template>
  <div class="workbench">
    <el-tabs v-model="activeTab" class="wb-tabs">
      <el-tab-pane label="安全规范审查" name="safety">
        <TaskList />
      </el-tab-pane>
      <el-tab-pane label="资源冲突检测" name="conflict">
        <RuleManage />
      </el-tab-pane>
      <el-tab-pane label="审查报告" name="report">
        <ReviewReport />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import TaskList from './TaskList.vue'
import RuleManage from './RuleManage.vue'
import ReviewReport from './ReviewReport.vue'

// 门户「智能审查」下三个二级菜单(review_safety/review_conflict/review_report)
// 在 m06-portal 的 iframeUrlMap 中均映射到 /#/work-order，本工作台以 tab 形式
// 同时承载「安全规范审查 / 资源冲突检测 / 审查报告」三块能力。
const activeTab = ref('safety')
</script>

<style scoped>
.workbench {
  padding: 18px 22px 22px;
}
.wb-tabs :deep(.el-tabs__header) {
  margin-bottom: 18px;
}
.wb-tabs :deep(.el-tabs__nav-wrap::after) {
  height: 1px;
  background: var(--brand-border);
}
.wb-tabs :deep(.el-tabs__item) {
  font-size: 15px;
  font-weight: 600;
  color: var(--brand-text-soft);
}
.wb-tabs :deep(.el-tabs__item.is-active) {
  color: #1677ff;
}
.wb-tabs :deep(.el-tabs__active-bar) {
  background: linear-gradient(90deg, #1677ff, #13c2c2);
}
</style>
