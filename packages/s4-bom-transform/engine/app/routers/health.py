"""健康检查端点。"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health():
    return {
        "module": "s4-bom-engine",
        "version": "0.0.1",
        "status": "UP",
    }
