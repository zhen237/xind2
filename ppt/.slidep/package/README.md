# @tencent/slidep

AI 生成 PPT 工具集。提供项目启动、JSX 页面校验、主题检索、GAS 风格脚本执行四类命令。

需要对接 [https://git.woa.com/docx-online/docx-online/blob/master/library/collab/editor/server/editor_sdk_api.md](edtior_sdk) 进行开发，开发前记得阅读这个 api 文档。 

## 安装

```bash
npm install -g @tencent/slidep
```

源码构建：

```bash
cd packages/slidep
pnpm install && pnpm run build
```

构建产物（`dist/`）：`slidep.js` / `slidep-start.js` / `slidep-stop.js` / `slidep-validate.js` / `slidep-template.js` / `slidep-script.js` / `worker.mjs`。

## 命令一览

| 命令 | 功能 |
|------|------|
| `slidep start` | 初始化项目并监听 `pages/`，把变更声明式 reconcile 到后端 |
| `slidep stop` | 关闭 `slidep start` 启动的后台 daemon |
| `slidep validate <file>` | 校验单个 JSX 页、提取 `image://` 占位符 |
| `slidep template search <kw...>` | 在内置主题库中按关键词检索 |
| `slidep script [file]` | 在 Worker 沙箱中跑 GAS 风格脚本，通过 MCP 控制后端 |
| `slidep export-images <pptx>` | 把 PPT/PPTX 调用后端转成每页一张 PNG 落盘 |
| `slidep version` | 输出版本号 |

所有命令都把 **结果 JSON 写 stdout，日志写 stderr**，便于上游脚本解析。

---

## slidep start

初始化项目目录、打开后端文件、监听 `pages/*.{mdx,tsx,jsx}`，每次变更都向后端 reconcile 出与本地一致的页序。

```bash
slidep start [options]
```

| 选项 | 默认 | 说明 |
|------|------|------|
| `--project <dir>` | `cwd` | 项目根目录 |
| `--filename <name>` | `空白幻灯片.pptx` | 后端落盘文件名 |
| `--dev` | false | 前台运行（默认 daemon），便于调试看日志 |

后端地址通过环境变量 `TENCENT_DOCS_LOCAL_MCP` 指定（缺省 `http://localhost:39099`）。

**示例：**

```bash
slidep start --project .
slidep start --project . --filename "demo.pptx" --dev
```

daemon 模式下父进程不输出任何内容（成功退出 0，pid 写入 `<projectDir>/.slidep/pid`）；开发模式（`--dev`）会把启动信息打印到 stdout：

```json
{
  "success": true,
  "watching": true,
  "projectDir": "/path/to/project",
  "fileId": "640700b7029d9c88dbeea4788584f9b2",
  "backendUrl": "http://localhost:39099",
  "filePath": "/path/to/project/空白幻灯片.pptx"
}
```

启动失败（已有实例在跑）时打印 `{ success: false, reason: "already running", pid, pidFile, projectDir }` 并退出 1。

---

## slidep stop

```bash
slidep stop [--project <dir>] [--force|-9] [--timeout <sec>]
```

读取 `<projectDir>/.slidep/pid`，默认 `SIGTERM` 优雅退出，`--force` 改用 `SIGKILL`，最长等待 `--timeout` 秒（默认 10）。pid 文件不存在时视作成功（幂等）。

**退出码：**

| 码 | 含义 |
|----|------|
| 0 | 已停止，或本就未运行 |
| 1 | 超时未退出 / 读 pid 失败 |
| 2 | 参数错误 |

---

## slidep validate

```bash
slidep validate <file> [--project <dir>] [--no-overflow-check]
```

调用 `SlideX.validate()` 校验单个 `.mdx`/`.tsx`/`.jsx` 文件，提取 `image://` 占位符并查询 `resources/cache/cache_index.json` 标记 done/pending；同时把解析映射写入 `resources/image-resolve/<slideId>.json`，供后续 render 阶段替换为本地路径。

**stdout：**

```json
{
  "success": true,
  "id": "slide_1",
  "status": "ready",
  "total_resources": 2,
  "done_resources": 2,
  "pending_resources": 0,
  "image_placeholders": [
    { "type": "search", "original": "image://search/商务", "params": { "keyword": "商务" } }
  ]
}
```

`status`：`ready`（无 pending） / `resolving`（有 pending）。

`image://` 占位符语法：

- `image://search/<keyword>` — 关键词搜图
- `image://generate/<keyword>` — AI 生图
- `data:...;base64,...` — 内联 base64（自动跳过）

---

## slidep template search

```bash
slidep template search <keyword...> [options]
```

| 选项 | 默认 | 说明 |
|------|------|------|
| `-l, --limit <n>` | 10（≤30） | 最多返回数 |
| `-m, --min-score <f>` | 0 | 最小分数（exclusive） |
| `-r, --min-results <n>` | 0 | 最少返回数；不足时按信息量补齐 score=0 占位 |
| `--themes-dir <path>` | `<package>/resources/themes` | 主题目录 |

匹配 frontmatter 的 `name` / `description` / `audience` 三字段，BM25 + IDF 评分（融合权重 0.15 / 0.55 / 0.30），分数归一到 `[0, 1]`，按降序输出。

**stdout：**

```json
[
  {
    "name": "商务蓝白",
    "description": "...",
    "audience": "...",
    "fileName": "business-blue-white.DESIGN.md",
    "filePath": "/abs/path",
    "score": 0.95
  }
]
```

主题文件格式：

```markdown
---
name: 商务蓝白
description: 适合商务汇报的蓝白配色主题
audience: 企业用户
---
正文（被忽略）
```

---

## slidep script

在独立 Worker 中执行 GAS 风格脚本，通过 MCP 协议调用幻灯片编辑器 SDK。

```bash
slidep script <file> [options]
slidep script -e "<code>" [options]
```

| 选项 | 默认 | 说明 |
|------|------|------|
| `-e, --code <code>` | — | 内联脚本（与文件参数互斥） |
| `--upstream-url <url>` | `$SLIDE_MCP_URL` 或 `http://localhost:39099/mcp` | MCP 服务器地址 |
| `--file-path <path>` | — | 调试模式：自动 open 该文件到 md5 槽 |
| `--timeout <sec>` | 60 | 脚本执行超时 |
| `--log-mcp` / `-v` | false | stderr 输出 MCP 调用简要日志 |
| `--log-mcp-file <path>` | — | 写完整 JSONL 日志到文件 |

**落盘由脚本控制**：CLI 不做 auto-save，需要落盘时脚本里显式调 `presentation.save()`。

**脚本 API**（GAS 风格，详见 SCRIPT-API-MCP 映射对照手册）：

```javascript
const presentation = SlidesApp.getActivePresentation();
const slide = presentation.appendSlide();
slide.insertTextBox('Hello', 100, 50, 400, 80)
     .getText().getTextStyle().setFontSize(24).setBold(true);
presentation.save();
```

**退出码：**

| 码 | 常量 | 含义 |
|----|------|------|
| 0 | SUCCESS | 执行成功 |
| 1 | SCRIPT_ERROR | 脚本异常 |
| 2 | ARG_ERROR | 参数错误 |
| 3 | UPSTREAM_ERROR | MCP 上游不可达 |
| 4 | TIMEOUT | 执行超时 |

---

## slidep export-images

把 `.ppt` / `.pptx` 调用 `docs.qq.com` 后端转成每页一张 PNG 落到本地。后端流水线为 `LibreOffice → pdftoppm`；本命令负责凭据获取、COS 直传、触发转换、并发下载。

```bash
slidep export-images <pptx> [options]
```

| 选项 | 默认 | 说明 |
|------|------|------|
| `-o, --outdir <dir>` | `cwd` | 输出目录，自动 `mkdir -p` |
| `--timeout <sec>` | 300 | upload / convert / download 各自的 HTTP 超时 |
| `-h, --help` | — | 帮助 |

**输出文件名**：`<pptx 去后缀的 basename>_<NN>.png`，`NN` 按总页数自适应补零（12 页 → `_01..12.png`，120 页 → `_001..120.png`）。

**stdout**（成功）：

```json
{
  "success": true,
  "input": "/abs/path/deck.pptx",
  "outdir": "/abs/path/out",
  "page_count": 12,
  "files": ["/abs/path/out/deck_01.png", "..."]
}
```

**stdout**（失败）：

```json
{ "success": false, "error": "convert failed: HTTP 500 ...", "page_count": 12, "downloaded": 4 }
```

**示例：**

```bash
slidep export-images deck.pptx
slidep export-images ./decks/foo.pptx --outdir ./out
slidep export-images deck.pptx --timeout 600
```

**安全约束**：下载阶段强校验预签名 URL host 必须是 `*.myqcloud.com`，不跟随重定向，避免被指向内网（SSRF 防护）。

---

## 项目状态文件

| 文件 | 说明 |
|------|------|
| `.slidep/state.json` | `{ fileId, lastCommit }`，fileId 由项目路径 md5 派生 |
| `.slidep/pid` | daemon 子进程 PID，由 `slidep stop` 使用 |
| `.slidep/logs.log` | 应用日志（跨多次 start 持续追加） |
| `.slidep/bak/<basename>.bak-<ts>.<ext>` | 启动时对已存在 pptx 的备份 |
| `resources/cache/cache_index.json` | `image://` 关键词 → 本地图缓存映射 |
| `resources/image-resolve/<slideId>.json` | 单页占位符解析结果（`null` 表示 pending） |

## 环境变量

| 变量 | 说明 |
|------|------|
| `TENCENT_DOCS_LOCAL_MCP` | 后端 SDK / MCP 地址 |
| `SLIDE_MCP_URL` | `slidep script` 默认 MCP URL |
| `SLIDEP_LOG_LEVEL` | `debug` / `info`（默认） / `warn` / `error` / `silent` |
| `SLIDEP_DIAG` | `1` 时启用 validate 的诊断报告 |

## 许可证

内部使用。
