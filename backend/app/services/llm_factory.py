import httpx
from functools import lru_cache

from langchain_groq import ChatGroq

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1"


@lru_cache
def get_llm(temperature: float = 0.0) -> ChatGroq:
    """
    Factory singleton para instancias de ChatGroq.
    
    Modelo: Llama 3.3 70B (gratis, 14,400 req/dia)
    """
    logger.info(f"Inicializando LLM: {settings.groq_model} (temp={temperature})")
    return ChatGroq(
        model=settings.groq_model,
        temperature=temperature,
        api_key=settings.groq_api_key,
    )


async def check_groq_health() -> bool:
    """Verifica conectividad con Groq API."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{GROQ_API_URL}/models",
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
            )
            return response.status_code == 200
    except Exception:
        return False
