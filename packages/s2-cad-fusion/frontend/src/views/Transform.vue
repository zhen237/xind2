<template>
  <div class="page">
    <h2>坐标转换</h2>
    <el-card shadow="never">
      <el-form label-width="110px" style="max-width: 640px">
        <el-form-item label="X (经度/东)">
          <el-input-number v-model="x" :controls="false" style="width: 100%" />
        </el-form-item>
        <el-form-item label="Y (纬度/北)">
          <el-input-number v-model="y" :controls="false" style="width: 100%" />
        </el-form-item>
        <el-form-item label="Z (高程)">
          <el-input-number v-model="z" :controls="false" style="width: 100%" />
        </el-form-item>
        <el-form-item label="源坐标系">
          <el-select v-model="sourceEpsg" style="width: 100%">
            <el-option label="CGCS2000 高斯投影 (EPSG:4490)" value="EPSG:4490" />
            <el-option label="WGS84 (EPSG:4326)" value="EPSG:4326" />
            <el-option label="Web Mercator (EPSG:3857)" value="EPSG:3857" />
            <el-option label="北京54 (EPSG:4214)" value="EPSG:4214" />
            <el-option label="西安80 (EPSG:4610)" value="EPSG:4610" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标坐标系">
          <el-select v-model="targetEpsg" style="width: 100%">
            <el-option label="WGS84 (EPSG:4326)" value="EPSG:4326" />
            <el-option label="CGCS2000 (EPSG:4490)" value="EPSG:4490" />
            <el-option label="Web Mercator (EPSG:3857)" value="EPSG:3857" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="onTransform">转换</el-button>
          <el-button @click="reset">重置</el-button>
        </el-form-item>
      </el-form>

      <el-divider>转换结果</el-divider>
      <el-result v-if="result" icon="success" title="转换成功">
        <template #sub-title>
          <p style="font-size: 16px">
            ({{ result.x }}, {{ result.y }}, {{ result.z ?? '-' }})
          </p>
          <p style="color: #999">
            {{ sourceEpsg }} → {{ targetEpsg }}
            <el-tag v-if="result.transformationType" size="small" style="margin-left: 8px">
              {{ result.transformationType }}
            </el-tag>
          </p>
        </template>
      </el-result>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { transformCoordinate } from '../api'

const x = ref(0)
const y = ref(0)
const z = ref(0)
const sourceEpsg = ref('EPSG:4490')
const targetEpsg = ref('EPSG:4326')
const loading = ref(false)
const result = ref(null)

const onTransform = async () => {
  loading.value = true
  result.value = null
  try {
    const res = await transformCoordinate({
      sourceX: x.value,
      sourceY: y.value,
      sourceZ: z.value,
      sourceEpsg: sourceEpsg.value,
      targetEpsg: targetEpsg.value,
    })
    result.value = res?.data
    ElMessage.success('转换成功')
  } finally {
    loading.value = false
  }
}

const reset = () => {
  x.value = 0
  y.value = 0
  z.value = 0
  result.value = null
}
</script>

<style scoped>
.page { max-width: 1000px; }
</style>
