from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routers.meet import router as meet_router
from utils import setup_logging


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging()
    settings.storage_path.mkdir(parents=True, exist_ok=True)
    status = settings.pipeline_status()
    logger = __import__("logging").getLogger("meet")
    logger.info("[启动] Meet 后端 | 端口=%s", settings.app_port)
    logger.info("[启动] 链路=%s", status["pipeline"])
    for name, step in status["steps"].items():
        flag = "就绪" if step["ready"] else "未就绪"
        logger.info("[启动] %s | %s", name, flag)
    if status["missing"]:
        logger.warning("[启动] 缺少配置: %s", ", ".join(status["missing"]))
    yield


app = FastAPI(title="Meet API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(meet_router)


@app.get("/")
async def root():
    return {
        "service": "Meet API",
        "endpoints": {
            "health": "GET /api/health",
            "voice": "POST /api/meet/voice",
            "docs": "GET /docs",
        },
    }


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "port": settings.app_port,
        "storage_dir": str(settings.storage_path),
        "pipeline": settings.pipeline_status(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_reload,
    )
