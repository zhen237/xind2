# 进度看板 · 维护与部署说明

进度看板已**整合进门户（m06-portal）**，作为「系统管理 → 进度看板」路由页面（`/system/progress`），不再作为独立站点部署。

## 数据来源（唯一）

```
packages/m06-portal/progress-board/progress.json
```

- 五位负责人手动维护 `completion` / `features[].state` / `updatedAt` 等字段。
- 状态值：`done`（已完成）、`doing`（进行中）、`todo`（待启动）。
- 该文件在**构建时被打包进门户 bundle**，前端通过 `import` 直接读取，**不存在运行时 fetch、没有重复副本**。

## 本地开发预览

```bash
cd packages/m06-portal
npm install
npm run dev
# 浏览器打开 http://localhost:5173 → 系统管理 → 进度看板
# 修改 progress.json 后 Vite 自动热更新，无需手动刷新
```

## 生产部署（宝塔裸机，配合门户整体）

进度看板随门户一起构建和部署，没有独立部署步骤：

1. 本地 `cd packages/m06-portal && npm run build` → 产物在 `dist/`
2. 将 `dist/` 整体上传到宝塔站点根目录（`/www/wwwroot/<站点>/`）
3. 宝塔站点「设置 → 配置文件」的 `location /` 段加 SPA 回退：
   ```nginx
   try_files $uri $uri/ /index.html;
   ```
4. 浏览器访问 `http://<公网IP>/` → 登录 → 系统管理 → 进度看板

> 更新进度：改 `progress-board/progress.json` → 重新 `npm run build` → 重新上传 `dist/` 即可。

## 历史备注

早期版本曾把看板作为独立静态站点（`index.html` + `progress.json` 经 nginx 托管），
并配有 `deploy.sh` 一键部署脚本。现已整合进门户，相关独立文件与脚本均已移除，避免重复维护。
