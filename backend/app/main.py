from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core import get_logger, settings

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Iniciando RFP Orchestrator [{settings.app_env}]")
    yield
    logger.info("Cerrando RFP Orchestrator")


app = FastAPI(
    title="RFP Multi-Agent Orchestrator",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    return {"status": "ok", "env": settings.app_env}
