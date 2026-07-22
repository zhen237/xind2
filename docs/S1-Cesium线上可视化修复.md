# S1 Cesium 线上可视化修复（#188）

> 日期: 2026-07-20
> 结论: **构建产物正确，问题 100% 出在服务器 nginx 配置**，非代码 / 构建问题。
> 已修复仓库规范配置 `scripts/nginx.conf`，本地仿真验证资源全部 200。

---

## 1. 现象

线上 `https://47.122.117.17/modules/m03/` 打开后 Cesium 地球白屏（404），疑似服务器 nginx 被改脏（luawaf 注释 + 残留测试 location 拦截 `/modules/m03/`），且 web 根目录与部署脚本不一致。

---

## 2. 根因分析（已用证据排除代码/构建问题）

### 2.1 构建产物正确 ✅
- `packages/m03-bim-gis/frontend/dist/` 已存在，且包含 **`cesium/`** 目录（`Cesium.js` / `Assets` / `Widgets` / `Workers` / `ThirdParty`）—— 由 `vite-plugin-cesium` 在 `vite build` 时自动拷贝。
- 构建 `base = /modules/m03/`（`vite.config.js`），`dist/index.html` 引用路径均为绝对 `/modules/m03/...`：
  - `/modules/m03/cesium/Cesium.js`
  - `/modules/m03/cesium/Widgets/widgets.css`
  - `/modules/m03/assets/index-*.js` / `*.css`
- `deploy-s1.sh` 用 `rsync -avz --delete dist/ → /www/wwwroot/portal/modules/m03`，**整目录（含 cesium/）同步**，不会漏资源。

### 2.2 本地仿真验证 ✅
把 `dist` 按部署布局放到 `www/wwwroot/portal/modules/m03`，用静态服务器在 `:8099` 验证：

| 请求 | 结果 |
|------|------|
| `GET /modules/m03/index.html` | **200** |
| `GET /modules/m03/cesium/Cesium.js` | **200** |
| `GET /modules/m03/cesium/Widgets/widgets.css` | **200** |
| `GET /modules/m03/assets/index-*.js` | **200** |

→ 只要服务器 nginx 的 web 根指向 `/www/wwwroot/portal` 且正确路由 `/modules/m03/`，Cesium 资源即可正常加载，地球不会再 404 白屏。

### 2.3 真实根因 ⚠️
仓库规范配置 `scripts/nginx.conf` 原本使用 **Docker 根 `/usr/share/nginx/html`**，而裸金属服务器（deploy-s1.sh 推送目标）实际根目录是 **`/www/wwwroot/portal`**。二者不一致，导致即便用"干净"的仓库配置，线上也 404。服务器上当前跑的是一份更脏的派生配置（luawaf 注释 + 测试 location），进一步拦截了 `/modules/m03/`。

---

## 3. 仓库侧已修复

`scripts/nginx.conf` 已对齐到裸金属生产布局：
- web 根 `root /www/wwwroot/portal;`
- `location /modules/m03/ { alias /www/wwwroot/portal/modules/m03/; }`（含 `cesium/`、`assets/` 子目录服务）
- m04 / m05 / screen 同样对齐
- 文件头加注：本配置即线上服务器应使用的规范配置；若再出现 404，用本文件覆盖服务器配置后 `nginx -s reload` 即可。

> 说明：Docker 部署走 docker-compose 服务名解析，路径不同，不影响本裸金属配置。

---

## 4. 服务器侧执行步骤（需 SSH，运维/本人执行）

```bash
# 1) 登录生产服务器
ssh root@47.122.117.17

# 2) 备份当前（脏）配置，再用仓库规范配置覆盖
#    仓库 scripts/nginx.conf 已对齐 /www/wwwroot/portal，直接 scp 或粘贴内容覆盖
cp /www/server/nginx/conf/.../xind2.conf /root/xind2.conf.bak.$(date +%Y%m%d)
# 将 scripts/nginx.conf 内容写入线上对应 site 配置（路径以服务器实际为准）

# 3) 语法校验 + 热重载（不中断连接）
nginx -t && nginx -s reload

# 4) 验证（均应为 200）
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1/modules/m03/
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1/modules/m03/cesium/Cesium.js
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1/api/m03/health
```

预期：三项均 `200`。地球即可正常加载。

### 回滚
若异常：`cp /root/xind2.conf.bak.<date> <线上配置>` && `nginx -s reload`。

---

## 5. 后续建议
- 把 `scripts/nginx.conf` 纳入部署流水线（deploy-s1.sh 末尾增加 `scp scripts/nginx.conf → 服务器` + `nginx -s reload`），避免下次手动改脏。
- 前端加一段「Cesium 资源加载失败」兜底提示（捕获 `Cesium.js` 404），而非静默白屏，便于快速定位。
