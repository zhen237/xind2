# twin-webgl 数字孪生 WebGL 构建资源

## 关于 `Build/twin-webgl.data.gz`

`Build/twin-webgl.data.gz`（99.61MB）**已移出版本库**，仅保留在本地磁盘 / 生产服务器上。

**移出原因**：GitHub 对单个文件有 100MB 硬上限，而该文件已达 99.61MB，距上限仅剩 0.39MB 余量。若继续入库，下次用 Unity 重新 Export WebGL 后文件大概率超过 100MB，导致无法推送。

**它是什么**：Unity 2022.3.62f3c1 使用 IL2CPP 后端导出的 WebGL 构建资源包。文件为 `UnityWebData1.0` 容器格式，解压后约 123.52MB，其中包含约 118.8MB 的 `data.unity3d`。

**怎么拿到（三种，任选其一）**：

1. 从生产服务器拉取：
   `124.220.37.119:/opt/xind2/dist/s5/twin-webgl/Build/twin-webgl.data.gz`
2. 从团队共享盘获取。
3. 用 **Unity 编辑器 2022.3.62f3c1** 打开仓库外的 Unity 工程目录 `lianxi/`（约 2GB，已被 `.gitignore` 忽略），重新 Export WebGL。

**哪些文件不能动**：`twin-webgl.loader.js`、`twin-webgl.wasm.gz`、`twin-webgl.framework.js.gz` 仍在本仓库中跟踪，请勿删除——它们是运行必需的。

**影响**：`TwinView.vue` 会以 iframe 方式嵌入 `twin-webgl/index.html`。若本地缺少 `Build/twin-webgl.data.gz`，数字孪生页面将加载失败。
