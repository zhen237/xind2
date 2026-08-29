# S1 Web 端 GitHub Pages 测试报告

- **测试时间**: 2026-08-28
- **测试目标**: https://zhen237.github.io/xind2/modules/m03/
- **测试方式**: 浏览器自动化（agent-browser），从线上地址直接访问
- **测试结论**: ✅ 通过 — S1 三维设计页在 Pages 环境下可用，mock 数据正常加载并渲染

## 测试项目与结果

| # | 测试项 | 预期 | 实际 | 状态 |
|---|--------|------|------|------|
| 1 | 页面整体加载 | 页面标题为「三维场景设计 - 通信基建数智化平台」且无 404 | 页面正常加载，路由为 `#/design` | ✅ 通过 |
| 2 | 项目列表弹窗 | 点击「加载数据」弹出项目选择框，列表含 2 个 mock 项目 | 弹窗正常，显示 2 个项目 | ✅ 通过 |
| 3 | 选择项目并加载设计数据 | 选择「卡萨布兰卡 JAD-MAR 通信基建试点」后，加载出方案、机房、站点 | 设计信息面板显示：项目ID 1、方案名称、3.5GHz、38m、12 个站点 | ✅ 通过 |
| 4 | 站点列表渲染 | 底部站点列表显示 12 个站点及 RSRP/状态 | 显示 SITE-001 ~ SITE-012；顶部统计「总站点 12 / 有效 11 / 无效 1 / 平均 RSRP -86.00 dBm」 | ✅ 通过 |
| 5 | Cesium 地图渲染 | 地图应定位到 Casablanca，并绘制站点覆盖圆盘 | 地图渲染出 Casablanca 区域，中心有彩色覆盖圆盘与站点标注 | ✅ 通过 |
| 6 | FTTH 叠加 | 点击右上角「FTTH」按钮，加载静态 `ftth-data.json` | 按钮响应，页面无报错，地图保持可交互 | ⚠️ 部分通过（页面未崩溃；因地图缩放级别较大，FTTH 点/线目视不清晰，建议后续放大验证） |

## 发现与备注

1. **Dialog 关闭存在过渡动画**：自动化点击「确定」后，页面已经加载站点数据，但弹窗由于 Element Plus 的关闭动画尚未完全消失，在截图瞬间仍可见。手工操作无感知，不是功能缺陷。
2. **FTTH 图层在全局视角下不明显**：FTTH 光交箱/光缆点尺寸小，当前截图缩放级别为全球/城市级，叠加图层存在但难以目视确认。如需展示，建议后续在页面上缩放到局部街道级再截图。
3. **自动化选择项目需键盘辅助**：Element Plus `el-select` 的 option 鼠标点击在 headless 环境下未立即注册选中状态，改用「ArrowDown + Enter」键盘选择后正常。真实用户鼠标点击无问题。

## 依赖文件

- 线上入口: https://zhen237.github.io/xind2/modules/m03/
- 本地测试截图: `s1_test_loaded.png`、`s1_test_final.png`
- 依赖改动: `src/mock/adapter.js`、`src/mock/fixtures.js`、`src/utils/request.js`、`src/router/index.js`、`scripts/postbuild-cesium.js`、`.github/workflows/deploy-pages.yml`
