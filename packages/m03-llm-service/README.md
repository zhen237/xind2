# m03-llm-service — S1 大模型辅助设计微服务

独立 FastAPI 服务，承载 S1 通信工程智能辅助设计的 ①+② 能力，仅监听本机回环，
由同机 M03 后端经 `LlmServiceClient` 调用（**密钥不离开本服务**）。

## 能力
- `POST /parse-design-params` — 自然语言设计需求 → 结构化设计参数 (JSON)
- `POST /generate-report` — 设计方案结构化数据 → Markdown 评审/交付报告
- `GET /health` — 健康检查（返回 model 与 configured 状态）

## 环境变量（密钥仅此处，绝不进代码/配置/镜像）
| 变量 | 说明 | 默认 |
|------|------|------|
| `LLM_API_KEY` | 云端 LLM 厂商 API Key（必填，缺失则 /health.configured=false 且调用返回 503） | 空 |
| `LLM_BASE_URL` | OpenAI 兼容协议基址 | `https://api.openai.com/v1` |
| `LLM_MODEL` | 模型名 | `gpt-4o-mini` |
| `LLM_TIMEOUT_S` | 单次调用超时(秒) | `60` |
| `LLM_MAX_TEXT_LEN` | 自然语言输入长度上限 | `4000` |
| `LLM_MAX_SCHEME_LEN` | 方案 JSON 长度上限 | `20000` |
| `LLM_MAX_CONCURRENCY` | 并发信号量 | `4` |

> 更换云端厂商（DeepSeek / 通义 / 智谱 / 本地 vLLM 等）只需改 `LLM_BASE_URL` 与 `LLM_MODEL`，
> 协议均为 OpenAI Chat Completions 兼容。

## 运行
```bash
cd packages/m03-llm-service
pip install -r requirements.txt
export LLM_API_KEY="sk-..."            # 来自运维密钥，非仓库
export LLM_BASE_URL="https://api.openai.com/v1"
export LLM_MODEL="gpt-4o-mini"
python main.py                         # 监听 127.0.0.1:9002
```

## 与 M03 后端对接
M03 后端 `application.yml` 配置：
```yaml
llm:
  service:
    url: http://localhost:9002
    timeout-ms: 60000
```
`/api/m03/llm/**` 由 SecurityAutoConfiguration 强制 JWT 鉴权（前端/插件持用户 Token 调用），
M03 后端再以内部 HTTP 调用本服务 —— 用户/前端永不直接持有 LLM Key。
