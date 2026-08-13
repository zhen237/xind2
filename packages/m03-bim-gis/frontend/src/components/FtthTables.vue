<template>
  <el-card shadow="never" class="block-card">
    <template #header>
      <span>交付物数据预览（网页直接查看，无需下载 xlsx）</span>
    </template>
    <el-tabs>
      <!-- 光交箱汇总：全字段表格（对应 Plans_de_Boie Sommaire + 每箱明细） -->
      <el-tab-pane label="光交箱汇总">
        <div class="filter-bar">
          <el-radio-group v-model="typeFilter">
            <el-radio-button label="all">全部</el-radio-button>
            <el-radio-button label="BPE">BPE</el-radio-button>
            <el-radio-button label="PBO">PBO</el-radio-button>
          </el-radio-group>
          <el-input
            v-model="searchText"
            placeholder="搜索箱体编码"
            clearable
            size="small"
            class="search"
          />
        </div>
        <el-table :data="filteredBoites" height="420" size="small" stripe border>
          <el-table-column prop="code" label="编码" width="190" fixed />
          <el-table-column prop="type" label="类型" width="70" />
          <el-table-column prop="capacite_fo" label="容量FO" width="80" />
          <el-table-column prop="fonction" label="功能" width="100" />
          <el-table-column prop="pm" label="归属PM" width="140" />
          <el-table-column prop="ptec" label="PTEC" width="110" />
          <el-table-column prop="logements" label="户数" width="70" />
          <el-table-column prop="adresse" label="地址" min-width="160" show-overflow-tooltip />
          <el-table-column prop="x" label="经度" width="100" />
          <el-table-column prop="y" label="纬度" width="100" />
        </el-table>
      </el-tab-pane>

      <!-- 光路由表：缆段逐行（对应 Routes_Optiques） -->
      <el-tab-pane label="光路由表">
        <el-table :data="cables" height="420" size="small" stripe border>
          <el-table-column prop="code" label="缆编码" width="210" fixed />
          <el-table-column prop="type_cable" label="类型" width="130" />
          <el-table-column prop="capacite_fo" label="容量FO" width="80" />
          <el-table-column prop="longueur" label="长度(m)" width="90" />
          <el-table-column prop="pm" label="归属PM" width="140" />
          <el-table-column prop="origine" label="起点箱" width="190" />
          <el-table-column prop="extremite" label="终点箱" width="190" />
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </el-card>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  boites: { type: Array, default: () => [] },
  cables: { type: Array, default: () => [] },
})

const typeFilter = ref('all')
const searchText = ref('')

const filteredBoites = computed(() => {
  let list = props.boites
  if (typeFilter.value !== 'all') {
    list = list.filter((b) => b.type === typeFilter.value)
  }
  if (searchText.value) {
    list = list.filter((b) => (b.code || '').includes(searchText.value))
  }
  return list
})
</script>

<style scoped>
.filter-bar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
}
.search {
  width: 200px;
}
</style>
