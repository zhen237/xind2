# 位置服务修复报告 - 运城学院默认位置

## 问题描述

应用程序重新启动后，位置服务仍显示为武汉/北京，而非预期的运城学院。

**根本原因**:
1. 多个Vue组件硬编码了北京坐标（116.4074, 39.9042）
2. 缺少统一的位置配置管理机制
3. 各组件之间位置数据不同步

---

## 解决方案

### 1. 创建统一位置配置文件

**文件**: `frontend/src/config/location.js`

```javascript
/**
 * 默认位置配置
 * 修改此处即可全局更新默认位置
 */
export const DEFAULT_LOCATION = {
  name: '运城学院',
  longitude: 110.932025,
  latitude: 35.123754,
  cameraHeight: 50000,
  defaultCoverageRadius: 500,
  defaultGridSize: 200,
  defaultSectorCount: 3
}

/**
 * 预设位置列表（用户可快速切换）
 */
export const PRESET_LOCATIONS = [
  { id: 'yuncheng', name: '运城学院', longitude: 110.932025, latitude: 35.123754 },
  { id: 'beijing', name: '北京', longitude: 116.4074, latitude: 39.9042 },
  { id: 'wuhan', name: '武汉', longitude: 114.39, latitude: 30.506 }
]
```

### 2. 更新所有Vue组件

#### 修改的文件列表

| 文件路径 | 修改内容 |
|---------|---------|
| `views/Design.vue` | 导入DEFAULT_LOCATION，使用配置初始化参数和相机位置 |
| `components/CesiumViewer.vue` | 导入DEFAULT_LOCATION，更新flyToDefault方法和regions数据 |
| `components/CesiumStationScene.vue` | 导入DEFAULT_LOCATION，更新所有基站坐标和表单默认值 |

#### 修改示例

**修改前** (硬编码北京坐标):
```javascript
const generateParams = reactive({
  centerLongitude: '116.4074',
  centerLatitude: '39.9042',
  // ...
})

viewer.camera.flyTo({
  destination: Cesium.Cartesian3.fromDegrees(116.4074, 39.9042, 50000)
})
```

**修改后** (使用统一配置):
```javascript
import { DEFAULT_LOCATION } from '@/config/location.js'

const generateParams = reactive({
  centerLongitude: DEFAULT_LOCATION.longitude.toString(),
  centerLatitude: DEFAULT_LOCATION.latitude.toString(),
  // ...
})

viewer.camera.flyTo({
  destination: Cesium.Cartesian3.fromDegrees(
    DEFAULT_LOCATION.longitude,
    DEFAULT_LOCATION.latitude,
    DEFAULT_LOCATION.cameraHeight
  )
})
```

### 3. 更新区域数据

**CesiumViewer.vue** 中的regions数据已从北京区域更新为运城区域:

| 原数据 | 新数据 |
|-------|-------|
| 北京市朝阳区 (116.400-116.500, 39.900-40.000) | 运城市盐湖区 (110.900-110.960, 35.100-35.150) |
| 北京市海淀区 (116.250-116.350, 39.950-40.050) | 运城学院校区 (110.920-110.940, 35.115-35.135) |
| 北京市西城区 (116.350-116.450, 39.900-39.950) | 运城市区 (110.910-110.950, 35.110-35.130) |

---

## 验证结果

运行验证脚本 `scripts/verify_location_config.py`:

```
[1/3] 检查硬编码的北京坐标...
  ✓ 所有Vue文件已清理北京坐标

[2/3] 检查位置配置文件...
  ✓ 位置配置文件存在: config/location.js
  ✓ 默认位置已设置为运城学院 (110.932025, 35.123754)

[3/3] 检查各组件是否使用统一配置...
  ✓ components\CesiumStationScene.vue
  ✓ components\CesiumViewer.vue
  ✓ views\Design.vue

检查结果: 3/3 个组件使用统一位置配置
✓ 位置配置修复完成!
```

---

## 技术细节

### 位置数据来源

运城学院坐标通过以下方式确认:
- **来源1**: Bigemap地图服务 - 经度: 110.932025, 纬度: 35.123754
- **来源2**: POI数据服务 - 大地坐标: 110.926505, 35.124778
- **最终采用**: 110.932025, 35.123754 (精度更高)

### 坐标精度验证

测试脚本 `scripts/test_yuncheng_college.py` 验证结果:
- ✅ 首站坐标: 110.932025, 35.123754 (与中心点完全一致)
- ✅ 站点间距: 200-270米 (符合网格设置)
- ✅ 覆盖范围: 500米半径完全覆盖校区
- ✅ 平均RSRP: -81.9 dBm (良好覆盖)

---

## 配置管理优势

### 1. 单一数据源
所有位置数据来自 `config/location.js`，修改一处即可全局生效。

### 2. 易于扩展
添加新位置只需在 `PRESET_LOCATIONS` 数组中添加配置:
```javascript
{
  id: 'shanghai',
  name: '上海',
  longitude: 121.473701,
  latitude: 31.230416
}
```

### 3. 类型安全
使用ES6模块导出，TypeScript友好。

### 4. 运行时可配置
可扩展为从后端API获取位置配置，支持动态切换。

---

## 浏览器缓存处理

如果重启后仍显示旧位置，请按以下步骤操作:

1. **清除浏览器缓存**
   - Chrome/Edge: `Ctrl + Shift + Delete`
   - 选择"缓存的图片和文件"
   - 点击"清除数据"

2. **强制刷新**
   - `Ctrl + F5` 或 `Ctrl + Shift + R`

3. **禁用服务工作者** (如果使用)
   - 开发者工具 → Application → Service Workers → Unregister

4. **验证配置生效**
   - 打开浏览器控制台
   - 输入: `localStorage.clear()`
   - 刷新页面

---

## 相关文件清单

### 新增文件
- `frontend/src/config/location.js` - 统一位置配置
- `scripts/verify_location_config.py` - 配置验证脚本
- `scripts/test_show_sites_fix.py` - 显示站点功能测试

### 修改文件
- `frontend/src/views/Design.vue` - 主设计页面
- `frontend/src/components/CesiumViewer.vue` - 3D查看器组件
- `frontend/src/components/CesiumStationScene.vue` - 基站场景组件

### 文档文件
- `scripts/show_sites_fix_report.md` - 显示站点修复报告
- `scripts/test_yuncheng_college_report.md` - 运城学院测试报告

---

## 后续优化建议

1. **位置持久化**: 使用localStorage保存用户最后选择的位置
2. **GPS定位**: 添加浏览器Geolocation API支持，自动获取当前位置
3. **位置搜索**: 添加地图搜索功能，用户可输入地名自动获取坐标
4. **位置预设管理**: 提供UI让用户自定义保存常用位置
5. **后端配置**: 将位置配置移至后端，支持管理员动态更新

---

**修复状态**: ✅ 已完成  
**测试状态**: ✅ 已通过  
**修复日期**: 2026-07-02  
**版本**: v1.2
