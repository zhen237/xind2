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
import hashlib
import time
from collections import OrderedDict

# 自动加载同目录 .env（gitignore，含 LLM_API_KEY 等敏感配置）。
# 必须在下方读取配置前执行，且 try 包裹，避免未安装 dotenv 时模块加载失败。
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:  # pragma: no cover
    pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("m03-llm-service")

app = FastAPI(title="M03 大模型辅助设计服务", description="S1 通信工程智能辅助设计 · 云端 LLM 微服务")

# ---- 配置（仅来自环境变量，不写默认值中的真实密钥） ----
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.agnes-ai.cn/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "agnes-2.5-flash")
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


# ---------------- 提示词（通信工程专业调优，含术语表 + few-shot） ----------------
_PARSE_SYSTEM = (
    "你是『通信工程智能辅助设计助手』，服务于通信基础设施（基站/室分/管线）数智化设计。"
    "请将用户用自然语言描述的设计需求，解析为如下结构化参数，并严格只返回一个 JSON 对象"
    "（不要任何额外说明文字、不要 Markdown 代码块）：\n"
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
    "【字段含义】\n"
    "- template_type：基站类型。macro=宏基站(广域覆盖，塔高>30m)，micro=微基站/小站(补盲，塔高<20m)，"
    "indoor=室内分布系统(楼宇/地下室深度覆盖)。\n"
    "- coverage_radius：单站覆盖半径(米)。经验参考：城区宏站 300~700m，郊区 800~1500m，"
    "农村 1500~3000m；微站 100~300m；室分按楼层面积。\n"
    "- frequency_band：无线频段，必须归一化为下列标准取值之一：\n"
    "  FDD-LTE-900(900MHz,覆盖广穿透强) / FDD-LTE-1800(1800MHz,容量与覆盖均衡) /\n"
    "  FDD-LTE-2100(2100MHz) / 5G-N41(2.6GHz TDD) / 5G-N78(3.5GHz TDD,主流5G) /\n"
    "  5G-N79(4.9GHz) / 700MHz(广电/移动共建共享,超广覆盖)。\n"
    "  用户说『4G/1800』→FDD-LTE-1800；『5G/3.5G』→5G-N78；『5G/2.6G』→5G-N41；『700M/广电』→700MHz。\n"
    "- tower_height：铁塔/抱杆总高度(米)。\n"
    "- antenna_height：天线挂高(米)，通常略低于塔顶或等于 tower_height，仅在用户明确区分时填。\n"
    "- sector_count：扇区数。0=全向天线，3=三扇区(默认宏站)，6=六扇区(高容量)。\n"
    "- scenario：urban=城区/密集，suburban=郊区/县城，rural=农村/郊野，indoor=室内。\n"
    "- site_count：若用户给出目标站点总数则填，否则 null。\n"
    "- notes：无法结构化的补充(如『需与现有某站共址』『避开某敏感区』)。\n"
    "【坐标推断】center_longitude/latitude 未明确时，结合上下文地名(如『运城学院』≈111.0E,35.0N)合理推断；"
    "完全无法推断则留 null。\n"
    "【few-shot 示例】\n"
    "用户：在运城学院建一个宏基站，站高30米，覆盖半径500米，频段FDD-LTE-1800，三扇区，城区\n"
    "→ {\"template_type\":\"macro\",\"center_longitude\":111.0,\"center_latitude\":35.0,"
    "\"coverage_radius\":500,\"frequency_band\":\"FDD-LTE-1800\",\"tower_height\":30,"
    "\"antenna_height\":28,\"sector_count\":3,\"scenario\":\"urban\",\"site_count\":null,"
    "\"notes\":\"运城学院校园覆盖\"}\n"
    "用户：农村广覆盖，2.6G 5G，挂高45，全向，三站\n"
    "→ {\"template_type\":\"macro\",\"center_longitude\":null,\"center_latitude\":null,"
    "\"coverage_radius\":2000,\"frequency_band\":\"5G-N41\",\"tower_height\":45,"
    "\"antenna_height\":45,\"sector_count\":0,\"scenario\":\"rural\",\"site_count\":3,"
    "\"notes\":null}"
)

_REPORT_SYSTEM = (
    "你是通信工程设计方案评审专家，服务于『通信基建数智化设计与交付』赛道评审。"
    "根据输入的设计方案结构化数据（含站点经纬度、站型、频段、功率、挂高、扇区数、覆盖/RSRP 采样等），"
    "生成一份专业、严谨的中文 Markdown 评审/交付报告。须包含以下章节（每章用 ## 二级标题，"
    "正文用专业术语，数值带单位）：\n"
    "## 一、项目概况（建设背景、区域特征、设计目标）\n"
    "## 二、站点与设备清单（按站型/频段汇总的表格式统计：宏站/微站/室分数、频段分布）\n"
    "## 三、关键参数核对（站间距(ISD)与频段关系、挂高、扇区配置、发射功率是否符合工程经验值）\n"
    "## 四、覆盖与信号评估（RSRP 参考信号接收功率：>-85dBm 优 / -85~-95dBm 良 / -95~-105dBm 边缘 / <-105dBm 弱；"
    "结合 SINR、重叠覆盖、切换带分析，给出覆盖率估算）\n"
    "## 五、风险与优化建议（弱覆盖区、PCI 冲突/模3干扰、站间距过密/过疏、物业/选址难点、降本建议）\n"
    "## 六、结论（是否满足建设目标，是否具备交付条件）\n"
    "要求：\n"
    "1. 术语规范：使用 RSRP/dBm、SINR、ISD(站间距)、PCI、eNodeB/gNodeB、频段标注、天线增益(dBi)、"
    "EIRP 等专业表述；避免口语化。\n"
    "2. 数据驱动：凡输入有数值（站点数、RSRP 均值、覆盖率、功率等）必须引用并量化，不得编造输入未提供的指标。\n"
    "3. 只输出 Markdown 正文，不要代码块包裹，不要『以下是报告』之类开场白。"
)


# ---------------- 调用缓存 + 审计日志（E 健壮性） ----------------
# 防止相同/重复请求反复扣费；缓存 TTL 区分：解析结果确定性高(长缓存)，报告可能希望刷新(短缓存)。
_CACHE_TTL_PARSE = float(os.environ.get("LLM_CACHE_TTL_PARSE_S", "600"))
_CACHE_TTL_REPORT = float(os.environ.get("LLM_CACHE_TTL_REPORT_S", "120"))
_CACHE_MAX = int(os.environ.get("LLM_CACHE_MAX", "256"))
_cache: "OrderedDict[str, tuple[float, float, Any]]" = OrderedDict()  # key -> (expire_at, stored_at, value)


def _cache_key(kind: str, user: str) -> str:
    return hashlib.sha256(f"{kind}|{user}".encode("utf-8")).hexdigest()


def _cache_get(kind: str, user: str):
    k = _cache_key(kind, user)
    item = _cache.get(k)
    if not item:
        return None
    expire_at, _, value = item
    if time.time() > expire_at:
        _cache.pop(k, None)
        return None
    _cache.move_to_end(k)
    return value


def _cache_put(kind: str, user: str, value, ttl: float):
    k = _cache_key(kind, user)
    _cache[k] = (time.time() + ttl, time.time(), value)
    _cache.move_to_end(k)
    while len(_cache) > _CACHE_MAX:
        _cache.popitem(last=False)


def _audit(endpoint: str, in_chars: int, dur_s: float, cached: bool, ok: bool, note: str = ""):
    """审计日志：记录端点/输入长度/耗时/缓存命中/状态，绝不记录原文或密钥（脱敏）。"""
    logger.info(
        "LLM_AUDIT endpoint=%s in_chars=%d dur_ms=%.0f cached=%s ok=%s%s",
        endpoint, in_chars, dur_s * 1000, cached, ok,
        f" note={note}" if note else "",
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

        # 缓存命中（确定性解析结果，避免重复扣费）
        cached = _cache_get("parse", user_msg)
        if cached is not None:
            _audit("parse-design-params", len(user_msg), 0.0, True, True, "cache_hit")
            return ParseResponse(params=DesignParams(**cached))

        t0 = time.time()
        try:
            data = await asyncio.to_thread(_chat_json, _PARSE_SYSTEM, user_msg)
            params = DesignParams(**data)
        except HTTPException:
            _audit("parse-design-params", len(user_msg), time.time() - t0, False, False, "llm_error")
            raise
        except Exception as e:
            _audit("parse-design-params", len(user_msg), time.time() - t0, False, False, "schema_invalid")
            logger.error("参数校验失败: %s | data=%s", e, str(data)[:500])
            raise HTTPException(status_code=502, detail="大模型返回结构不合法，请稍后重试")
        _cache_put("parse", user_msg, data, _CACHE_TTL_PARSE)
        _audit("parse-design-params", len(user_msg), time.time() - t0, False, True)
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

        # 短 TTL 缓存：报告内容可能希望刷新，但相同输入短时间内重发仍复用
        cached = _cache_get("report", user_msg)
        if cached is not None:
            _audit("generate-report", len(user_msg), 0.0, True, True, "cache_hit")
            return ReportResponse(report_markdown=cached)

        t0 = time.time()
        try:
            markdown = await asyncio.to_thread(_chat_text, _REPORT_SYSTEM, user_msg)
        except HTTPException:
            _audit("generate-report", len(user_msg), time.time() - t0, False, False, "llm_error")
            raise
        if not markdown:
            _audit("generate-report", len(user_msg), time.time() - t0, False, False, "empty")
            raise HTTPException(status_code=502, detail="大模型未返回报告内容，请稍后重试")
        _cache_put("report", user_msg, markdown, _CACHE_TTL_REPORT)
        _audit("generate-report", len(user_msg), time.time() - t0, False, True)
        return ReportResponse(report_markdown=markdown)


@app.get("/health", summary="健康检查")
async def health_check():
    return {"status": "ok", "service": "m03-llm-service", "model": LLM_MODEL, "configured": bool(_client)}


if __name__ == "__main__":
    import uvicorn
    # 仅本机回环：大模型服务只供同机 M03 后端(localhost:9002)经 LlmServiceClient 调用，
    # 不暴露公网；密钥仅在本进程环境变量中，不落库/不进配置。
    uvicorn.run(app, host="127.0.0.1", port=9002)
