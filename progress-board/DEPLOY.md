# 子赛题进度看板 · 部署指引（阿里云 ECS）

静态看板，零构建、零依赖。两个文件：`index.html` + `progress.json`。

## 一、本地预览（先把效果看一眼）

```bash
cd progress-board
python -m http.server 8099
# 浏览器打开 http://localhost:8099/
```
> 直接双击 index.html（file://）也能看，会用内嵌 fallback 数据；但部署/本地起服务时优先读 progress.json。

## 二、部署到阿里云 ECS

1. **买好 ECS**（已有），系统建议 Alibaba Cloud Linux / CentOS / Ubuntu 均可。
2. **装 nginx**
   ```bash
   # Alibaba Cloud Linux / CentOS
   yum install -y nginx && systemctl enable --now nginx
   # Ubuntu
   apt update && apt install -y nginx
   ```
3. **上传看板文件**
   ```bash
   # 在本机把两个文件传上去（二选一）
   scp -r progress-board/ root@<公网IP>:/usr/share/nginx/html/progress-board
   # 或 git 拉取：服务器上 git clone 后把 progress-board/ 软链/拷到 /usr/share/nginx/html/
   ```
4. **开安全组**：ECS 控制台 → 安全组 → 入方向放行 **80**（HTTP）/ **443**（HTTPS，有域名时）。
5. **访问**：`http://<公网IP>/progress-board/`

## 三、更新进度（日常）

- 改 `progress.json` 里对应的 `completion` / `features[].state` / `updatedAt`。
  - 状态值：`done`（已完成）、`doing`（进行中）、`todo`（待启动）。
- 改完刷新页面即生效（若用 git 部署，服务器 `git pull` 一下）。
- 想让服务器自动同步仓库，可加个 cron：
  ```bash
  # 每天 8 点拉最新 progress.json
  echo '0 8 * * * cd /usr/share/nginx/html/progress-board && git pull --ff-only' | crontab -
  ```

## 四、想加“自动信号”（可选进阶）

当前看板是**手动维护完成度**。若要进一步自动展示：
- **代码贡献量**：前端调用 GitHub API `https://api.github.com/repos/zhen237/xind2/contributors`（需放开 CORS 或用后端代理），显示每人 commit 数。
- **服务在线状态**：在各模块 `/health` 放行跨域后，看板 ping 各端口显示在线/离线。

这些属于“增强版”，需要 ECS 上对应服务在线或加一层后端代理，按需再做。
