from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.routers import review
import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="S3 Review Python Engine", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(review.router, prefix="/api/v1/s3/review")

@app.get("/")
async def root():
    return {"code": 200, "message": "S3 Review Python Engine is running", "data": None}

@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    start_time = time.time()
    client_host = request.client.host if request.client else "unknown"
    
    logger.info(f"===== Incoming Request =====")
    logger.info(f"method: {request.method}")
    logger.info(f"path: {request.url.path}")
    logger.info(f"query: {request.url.query}")
    logger.info(f"client: {client_host}")
    logger.info(f"==============================")
    
    try:
        response = await call_next(request)
    except Exception as e:
        duration = round(time.time() - start_time, 2)
        logger.error(f"===== Request Error =====")
        logger.error(f"method: {request.method}")
        logger.error(f"path: {request.url.path}")
        logger.error(f"error: {str(e)}")
        logger.error(f"duration: {duration}s")
        logger.error(f"==============================", exc_info=True)
        raise
    
    duration = round(time.time() - start_time, 2)
    
    logger.info(f"===== Request Completed =====")
    logger.info(f"method: {request.method}")
    logger.info(f"path: {request.url.path}")
    logger.info(f"status_code: {response.status_code}")
    logger.info(f"duration: {duration}s")
    logger.info(f"==============================")
    
    return response

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_details = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error.get("loc", []))
        error_details.append({
            "field": field,
            "message": error.get("msg", ""),
            "type": error.get("type", "")
        })
    
    logger.error(f"===== Validation Error =====")
    logger.error(f"path: {request.url.path}")
    logger.error(f"details: {error_details}")
    logger.error(f"==============================")
    
    return JSONResponse(
        status_code=400,
        content={
            "code": 400,
            "message": "参数校验失败",
            "detail": error_details,
            "data": None
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"===== Global Exception =====")
    logger.error(f"path: {request.url.path}")
    logger.error(f"error: {str(exc)}")
    logger.error(f"==============================", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "message": f"服务器内部错误: {str(exc)}",
            "data": None
        }
    )
