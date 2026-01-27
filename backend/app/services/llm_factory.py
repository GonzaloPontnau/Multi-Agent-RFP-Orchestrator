from functools import lru_cache

from langchain_ollama import ChatOllama

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@lru_cache
def get_llm(model: str = "llama3", temperature: float = 0.0) -> ChatOllama:
    """
    Factory singleton para instancias de ChatOllama.
    
    Args:
        model: Nombre del modelo en Ollama
        temperature: 0.0 para respuestas determinísticas
    """
    logger.info(f"Inicializando LLM: {model} (temp={temperature})")
    return ChatOllama(
        model=model,
        temperature=temperature,
        base_url=settings.ollama_base_url,
    )
