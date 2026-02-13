"""Endpoints de consulta al pipeline de agentes."""

import hashlib
import json

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.agents import rfp_app
from app.agents.state import create_initial_state
from app.api.response_builder import build_query_response
from app.core.cache import TTLCache
from app.core.config import settings
from app.core.logging import AgentLogger, get_logger
from app.schemas import QueryRequest, QueryResponse

logger = get_logger(__name__)
agent_logger = AgentLogger("pipeline")
router = APIRouter()

_response_cache = TTLCache[QueryResponse](
    ttl_seconds=settings.cache_ttl_seconds,
    max_size=settings.cache_max_size,
)


def invalidate_cache() -> None:
    """Invalida respuestas cacheadas."""
    _response_cache.clear()


def _cache_key(question: str) -> str:
    """Genera clave estable para cache por pregunta normalizada."""
    normalized = question.strip().lower()
    return hashlib.sha256(normalized.encode()).hexdigest()


def _sse_event(event_type: str, data: dict) -> str:
    """Formatea payload como evento SSE."""
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/chat", response_model=QueryResponse)
async def chat(request: QueryRequest) -> QueryResponse:
    """Procesa una pregunta usando el grafo multi-agente."""
    cached = _response_cache.get(_cache_key(request.question))
    if cached is not None:
        logger.info(f"[CHAT] Cache HIT for question: {request.question[:60]}...")
        return cached

    try:
        initial_state = create_initial_state(request.question)
        agent_logger.pipeline_start(request.question, initial_state.get("trace_id"))
        result = await rfp_app.ainvoke(initial_state)
        agent_logger.pipeline_end(result)
        response = build_query_response(result)
        _response_cache.set(_cache_key(request.question), response)
        return response
    except Exception as e:
        logger.error(f"[CHAT] Error procesando consulta: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error procesando pregunta: {str(e)}",
        )


@router.post("/chat/stream")
async def chat_stream(request: QueryRequest) -> StreamingResponse:
    """Procesa una pregunta usando SSE para feedback en tiempo real."""

    async def _event_stream():
        try:
            yield _sse_event("status", {"step": "retrieve", "message": "Recuperando documentos..."})
            result = await rfp_app.ainvoke(create_initial_state(request.question))
            response = build_query_response(result)
            yield _sse_event("result", json.loads(response.model_dump_json()))
        except Exception as e:
            logger.error(f"[STREAM] Error: {e}", exc_info=True)
            yield _sse_event("error", {"detail": str(e)})

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
