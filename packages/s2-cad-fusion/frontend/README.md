# S2 CAD→GIS 前端

Vue3 + Vite + Element Plus 的前端界面，用于 CAD 图纸上传、坐标转换、数据融合的可视化操作。

## 页面

| 路由 | 页面 | 功能 |
| --- | --- | --- |
| `/upload` | 图纸上传 | 上传 DWG/DXF 文件并解析 |
| `/transform` | 转换结果 | 坐标转换（源坐标系 → 目标坐标系） |
| `/fusion` | 融合结果 | S1 设计 + CAD 图纸融合，查看 GeoJSON |

## 启动

```bash
npm install
npm run dev
```

默认端口 **5182**，访问 http://localhost:5182

开发环境通过 Vite proxy 将 `/api/s2` 代理到后端 `http://localhost:8082`。

## 构建

```bash
npm run build
```

产物输出到 `dist/`，可部署到 Nginx 等静态服务器（需将 `/api/s2` 反向代理到后端）。
