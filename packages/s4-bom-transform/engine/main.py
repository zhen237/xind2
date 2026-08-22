"""
S4 BOM 施工指令转化 Python 引擎。
FastAPI (Python 3.10) — 内部端口 8100，由 Java 后端通过 HTTP 调用。
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import health, bom

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("s4-engine")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"S4 BOM Engine starting on port {settings.port} ...")
    yield
    logger.info("S4 BOM Engine shutting down.")


app = FastAPI(
    title="S4 BOM Transform Engine",
    description="施工指令转化 — 物料映射 / 辅材计算 / 线缆估算 / Excel 导出",
    version="0.0.1",
    lifespan=lifespan,
)

# CORS (dev only) — 收紧为本地前端；通配符 + credentials 的组合本身无效且不安全
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5190", "http://127.0.0.1:5190"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(bom.router, prefix="/api/v1/bom")


if __name__ == "__main__":
    import uvicorn
    # 默认 127.0.0.1（不暴露局域网）；联调需要时 S4_HOST=0.0.0.0 python main.py
    uvicorn.run(app, host=settings.host, port=settings.port, reload=False)
