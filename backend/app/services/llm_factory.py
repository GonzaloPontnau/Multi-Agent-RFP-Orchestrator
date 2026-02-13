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
    
    Modelo: OpenAI GPT-OSS 120B (500 tps, 1K RPM, 250K TPM)
    - Flagship open-weight de OpenAI con capacidades de razonamiento
    - Context window: 131K input / 65K output
    
    Rate Limit Tuning:
    - request_timeout: 60s (sufficient for complex responses)
    - max_retries: 3 (handle transient rate limit errors)
    """
    logger.info(f"Inicializando LLM: {settings.groq_model} (temp={temperature})")
    return ChatGroq(
        model=settings.groq_model,
        temperature=temperature,
        api_key=settings.groq_api_key,
        request_timeout=60,  # 60 seconds timeout for complex requests
        max_retries=3,  # Retry up to 3 times on rate limit/transient errors
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
