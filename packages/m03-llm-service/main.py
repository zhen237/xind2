"""
m03-llm-service — S1 通信工程智能辅助设计 · 大模型微服务

能力（落地路线 ①+②，云端 API）：
  ① POST /parse-design-params : 自然语言设计需求 -> 结构化设计参数
  ② POST /generate-report     : 设计方案结构化数据 -> Markdown 评审/交付报告

安全要点（吸取安全审查教训）：
  - LLM API Key 仅来自环境变量 LLM_API_KEY，绝不进代码/配置/日志。
  - 仅监听 127.0.0.1（同机 M03 后端经 LlmServiceClient 调用，不暴露公网）。
  - 上游错误脱敏（不向前端/后端回传含 Key 的原始报错）。
  - 输入长度上限 + 并发信号量，防滥用/DoS。
  - 采用 OpenAI 兼容协议：更换云端厂商只需改 LLM_BASE_URL / LLM_MODEL。
"""
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import os
import json
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("m03-llm-service")

app = FastAPI(title="M03 大模型辅助设计服务", description="S1 通信工程智能辅助设计 · 云端 LLM 微服务")

# ---- 配置（仅来自环境变量，不写默认值中的真实密钥） ----
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini")
REQUEST_TIMEOUT = float(os.environ.get("LLM_TIMEOUT_S", "60"))
MAX_TEXT_LEN = int(os.environ.get("LLM_MAX_TEXT_LEN", "4000"))
MAX_SCHEME_LEN = int(os.environ.get("LLM_MAX_SCHEME_LEN", "20000"))
MAX_CONCURRENCY = int(os.environ.get("LLM_MAX_CONCURRENCY", "4"))

_semaphore = asyncio.Semaphore(MAX_CONCURRENCY)

# OpenAI 兼容客户端（lazy import，避免无网络时模块加载失败）
try:
    from openai import OpenAI
    _client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL, timeout=REQUEST_TIMEOUT) if LLM_API_KEY else None
except Exception as e:  # pragma: no cover
    logger.warning("OpenAI SDK 初始化失败(运行时将返回 503): %s", e)
    _client = None


# ---------------- 请求/响应模型 ----------------
class ParseRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_TEXT_LEN, description="自然语言设计需求")
    context: Optional[Dict[str, Any]] = Field(default=None, description="可选上下文(区域/既有参数等)")


class DesignParams(BaseModel):
    template_type: Optional[str] = None          # macro | micro | indoor
    center_longitude: Optional[float] = None
    center_latitude: Optional[float] = None
    coverage_radius: Optional[float] = None       # 米
    frequency_band: Optional[str] = None          # 如 fdd-lte-1800 / 5g-n41
    tower_height: Optional[float] = None           # 米
    antenna_height: Optional[float] = None
    sector_count: Optional[int] = None
    scenario: Optional[str] = None                 # urban | suburban | rural | indoor
    site_count: Optional[int] = None
    notes: Optional[str] = None


class ParseResponse(BaseModel):
    params: DesignParams


class ReportRequest(BaseModel):
    scheme: Dict[str, Any] = Field(..., description="设计方案结构化数据(来自 DesignData 等)")
    context: Optional[Dict[str, Any]] = Field(default=None, description="可选上下文(项目名/评审标准等)")


class ReportResponse(BaseModel):
    report_markdown: str


# ---------------- 提示词 ----------------
_PARSE_SYSTEM = (
    "你是通信工程智能辅助设计助手。请将用户用自然语言描述的设计需求，"
    "解析为如下结构化参数，并严格只返回一个 JSON 对象（不要任何额外说明文字）：\n"
    "{\n"
    '  "template_type": "macro" | "micro" | "indoor" | null,\n'
    '  "center_longitude": number | null,\n'
    '  "center_latitude": number | null,\n'
    '  "coverage_radius": number | null,\n'
    '  "frequency_band": string | null,\n'
    '  "tower_height": number | null,\n'
    '  "antenna_height": number | null,\n'
    '  "sector_count": integer | null,\n'
    '  "scenario": "urban" | "suburban" | "rural" | "indoor" | null,\n'
    '  "site_count": integer | null,\n'
    '  "notes": string | null\n'
    "}\n"
    "字段含义：template_type=基站类型；coverage_radius=覆盖半径(米)；frequency_band=频段；"
    "tower_height=铁塔高度(米)；antenna_height=天线挂高(米)；sector_count=扇区数；"
    "scenario=场景；site_count=站点数；notes=无法结构化的补充说明。\n"
    "位置坐标如未明确，结合上下文(如‘运城学院’)合理推断，无法推断则留 null。"
)

_REPORT_SYSTEM = (
    "你是通信工程设计方案评审专家。根据输入的设计方案结构化数据，"
    "生成一份专业、简洁的中文 Markdown 评审/交付报告，须包含以下章节：\n"
    "## 一、项目概况\n## 二、站点与设备清单\n## 三、关键参数核对\n"
    "## 四、覆盖与信号评估（RSRP）\n## 五、风险与优化建议\n"
    "只输出 Markdown 正文，不要代码块包裹。"
)


# ---------------- 工具 ----------------
def _client_or_503():
    if not _client:
        raise HTTPException(status_code=503, detail="大模型服务未配置(缺少 LLM_API_KEY)")
    return _client


def _chat_json(system: str, user: str) -> dict:
    """调用 LLM 并以 JSON 模式解析返回。失败时抛出 HTTPException（已脱敏）。"""
    client = _client_or_503()
    try:
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        content = resp.choices[0].message.content or "{}"
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error("LLM 返回非 JSON (trace_id=%s): %s", id(e), str(e)[:200])
        raise HTTPException(status_code=502, detail="大模型返回内容解析失败，请稍后重试")
    except HTTPException:
        raise
    except Exception as e:
        # 脱敏：不回传上游原始报错(可能含 Key)
        logger.error("LLM 调用异常 (trace_id=%s): %s", id(e), type(e).__name__)
        raise HTTPException(status_code=502, detail="大模型服务调用失败，请稍后重试")


def _chat_text(system: str, user: str) -> str:
    client = _client_or_503()
    try:
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.5,
        )
        return (resp.choices[0].message.content or "").strip()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("LLM 调用异常 (trace_id=%s): %s", id(e), type(e).__name__)
        raise HTTPException(status_code=502, detail="大模型服务调用失败，请稍后重试")


# ---------------- 端点 ----------------
@app.post("/parse-design-params", response_model=ParseResponse, summary="① 自然语言 -> 结构化设计参数")
async def parse_design_params(req: ParseRequest):
    async with _semaphore:
        user_msg = req.text
        if req.context:
            user_msg += "\n\n参考上下文(JSON):\n" + json.dumps(req.context, ensure_ascii=False)[:MAX_SCHEME_LEN]
        data = await asyncio.to_thread(_chat_json, _PARSE_SYSTEM, user_msg)
        try:
            params = DesignParams(**data)
        except Exception as e:
            logger.error("参数校验失败: %s | data=%s", e, str(data)[:500])
            raise HTTPException(status_code=502, detail="大模型返回结构不合法，请稍后重试")
        return ParseResponse(params=params)


@app.post("/generate-report", response_model=ReportResponse, summary="② 设计方案 -> Markdown 报告")
async def generate_report(req: ReportRequest):
    async with _semaphore:
        scheme_str = json.dumps(req.scheme, ensure_ascii=False)
        if len(scheme_str) > MAX_SCHEME_LEN:
            scheme_str = scheme_str[:MAX_SCHEME_LEN] + "\n...(已截断)"
        user_msg = "设计方案数据(JSON):\n" + scheme_str
        if req.context:
            user_msg += "\n\n参考上下文(JSON):\n" + json.dumps(req.context, ensure_ascii=False)[:2000]
        markdown = await asyncio.to_thread(_chat_text, _REPORT_SYSTEM, user_msg)
        if not markdown:
            raise HTTPException(status_code=502, detail="大模型未返回报告内容，请稍后重试")
        return ReportResponse(report_markdown=markdown)


@app.get("/health", summary="健康检查")
async def health_check():
    return {"status": "ok", "service": "m03-llm-service", "model": LLM_MODEL, "configured": bool(_client)}


if __name__ == "__main__":
    import uvicorn
    # 仅本机回环：大模型服务只供同机 M03 后端(localhost:9002)经 LlmServiceClient 调用，
    # 不暴露公网；密钥仅在本进程环境变量中，不落库/不进配置。
    uvicorn.run(app, host="127.0.0.1", port=9002)
