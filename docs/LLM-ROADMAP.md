# S1 大模型落地路线（①+②，云端 API）

> 状态：骨架已落地（m03-llm-service + M03 后端代理已就绪、编译通过）。
> 决策：场景 = ① 自然语言→设计参数 + ② 自动生成报告；部署 = 先云端 API 验证（OpenAI 兼容协议，Key 仅服务端持有）。

## 1. 为什么是这两条

| 场景 | 贴题度 | 评审价值 | 落地成本 |
|------|--------|----------|----------|
| ① 自然语言→设计参数 | ★★★（直击"智能辅助设计"题眼） | 把"人话需求"转结构化参数，演示效果直观 | 低（一次 LLM 调用 + JSON 解析） |
| ② 设计方案→自动报告 | ★★★（交付物即评审材料） | 自动产出专业 Markdown 报告，省人工 | 低（一次 LLM 调用） |
| ③ 对话式 GIS 助手 | ★★ | 演示增强，但 QGIS 内嵌对话工程量大 | 高 |
| ④ 智能参数推荐 | ★★ | 需大量领域样本，易显"伪智能" | 中 |

选 ①+②：题眼命中 + 低成本 + 即时可见效果。③ 作为有余力时的演示增强。

## 2. 架构（密钥边界是核心）

```
[QGIS 插件 / 前端]  --JWT-->  [M03 后端 /api/m03/llm/**]  --内部HTTP(localhost:9002)-->  [m03-llm-service]
   (永不直接持 Key)            (JWT 鉴权 + RateLimit)                            (持有 LLM_API_KEY, 绑 127.0.0.1)
                                                                                      |
                                                                                      v
                                                                              [云端 LLM API / OpenAI 兼容]
```

- **m03-llm-service**：独立 FastAPI，仅监听 `127.0.0.1:9002`，由同机 M03 后端经 `LlmServiceClient` 调用。LLM API Key **只在该服务的环境变量中**，不进代码/配置/日志/仓库。
- **M03 后端代理**：`LlmServiceClient`（镜像 `TopologyEngineClient` 模式）调本机 9002；`LlmController` 暴露 `/api/m03/llm/parse-design-params` 与 `/api/m03/llm/generate-report`，由 `SecurityAutoConfiguration` **强制 JWT 鉴权**（未列入 permit-paths），并加 `@RateLimit` 防滥用。
- **前端/插件**：只持用户 JWT，调用 M03 的 `/api/m03/llm/**`，**永不直接持有 LLM Key**（吸取安全审查中"密钥须隔离"的教训）。

## 3. 两能力定义

### ① POST /parse-design-params — 自然语言 → 结构化设计参数
请求：
```json
{ "text": "在运城学院区域建一个宏基站，站高30米，覆盖半径500米，频段FDD-LTE-1800，三扇区，城区", "context": {} }
```
响应（`DesignParams`）：
```json
{ "params": {
  "template_type": "macro", "center_longitude": 111.0, "center_latitude": 35.0,
  "coverage_radius": 500, "frequency_band": "fdd-lte-1800", "tower_height": 30,
  "antenna_height": 30, "sector_count": 3, "scenario": "urban", "site_count": null, "notes": null
} }
```
实现：JSON 模式 + 强 schema 提示词，Pydantic 校验后回传；字段缺失/无法结构化部分落入 `notes`。

### ② POST /generate-report — 设计方案 → Markdown 报告
请求：
```json
{ "scheme": { /* DesignData 结构化数据 */ }, "context": { "projectName": "运城学院宏站" } }
```
响应：
```json
{ "report_markdown": "## 一、项目概况\n..." }
```
实现：将方案 JSON 注入评审专家提示词，产出含「项目概况/站点设备清单/关键参数核对/覆盖信号评估/风险建议」五段的 Markdown。

## 4. 云端 API 选型（OpenAI 兼容）
- 协议统一走 OpenAI Chat Completions 兼容：`LLM_BASE_URL` + `LLM_MODEL` 可配。
- 验证期用任意 OpenAI 兼容厂商（DeepSeek / 通义千问 / 智谱 / 本地 vLLM 均可），**换厂商只改两个环境变量**，代码零改动。
- `LLM_API_KEY` 来自运维注入的环境变量，绝不入仓（已在 `.env.example` 改为 `CHANGE_ME`，且 `git filter-repo` 已擦除历史明文）。

## 5. 安全 posture（对齐安全整改）
- 仅 `127.0.0.1` 监听，不暴露公网；密钥仅本进程环境变量。
- 上游错误脱敏：LLM 调用异常只记 `trace_id` + 类型，不向前端/后端回传含 Key 的原始报错（返回 502/503 通用提示）。
- 输入长度上限（`LLM_MAX_TEXT_LEN` / `LLM_MAX_SCHEME_LEN`）+ 并发信号量（`LLM_MAX_CONCURRENCY`）。
- `/api/m03/llm/**` 强制 JWT + RateLimit（2 QPS）。
- 配置项走环境变量，默认值不含任何真实密钥。

## 6. 分阶段实施计划
| 阶段 | 内容 | 状态 |
|------|------|------|
| A. 骨架 | m03-llm-service（main.py + requirements + README）、M03 LlmServiceClient + LlmController + DTO、application.yml 配置 | ✅ 已落地、编译通过 |
| B. 前端接入 | 设计页加「AI 解析需求」「AI 生成报告」按钮，调用 `/api/m03/llm/**`，解析结果回填表单 / 报告弹窗展示 | ⏳ 待做 |
| C. QGIS 接入 | 插件菜单加「智能生成报告」入口，调 M03 网关；参数解析结果回写设计模板 | ⏳ 待做 |
| D. 提示词调优 | 针对通信工程术语（频段/挂高/扇区/RSRP）做 few-shot，提升 ① 的字段命中率与 ② 的专业度 | ⏳ 待做 |
| E. 健壮性 | LLM 超时/降级（返回本地模板报告）、结果缓存（同方案哈希）、审计日志（谁何时生成）、可观测（调用量/耗时/失败率） | ⏳ 待做 |

## 7. 部署步骤（服务器侧）
```bash
# 1. 安装依赖
cd packages/m03-llm-service && pip install -r requirements.txt
# 2. 注入密钥（仅本机环境变量，建议写 systemd EnvironmentFile，勿入仓）
export LLM_API_KEY="sk-..." LLM_BASE_URL="https://api.openai.com/v1" LLM_MODEL="gpt-4o-mini"
# 3. 启动（仅本机回环）
python main.py   # 127.0.0.1:9002
# 4. M03 后端 application.yml 已含 llm.service.url=http://localhost:9002
# 注意：此 Key 在服务器本地，无需进 GitHub secrets（与 deploy.yml 的 MYSQL_PASSWORD 不同）
```
健康检查：`curl http://localhost:9002/health` → `{"status":"ok","configured":true,...}`

## 8. 评审加分点
- **真实业务闭环**：自然语言需求 → 可执行设计参数 → 自动评审报告，紧扣"数智化全流程"。
- **密钥零泄露**：Key 全程不落前端/插件/仓库，架构上隔离（对比常见"前端直接调 LLM"的反面教材）。
- **可替换**：OpenAI 兼容协议，验证期随便换厂商，不被单一厂商绑定。
- **不喧宾夺主**：LLM 是辅助设计的能力增强，不替代既有参数化引擎（拓扑引擎仍为主力算法），符合"智能辅助"定位。
