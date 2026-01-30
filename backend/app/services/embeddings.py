from functools import lru_cache

from langchain_huggingface import HuggingFaceEndpointEmbeddings

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Using API-based embeddings to save RAM on Render free tier
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384


@lru_cache
def get_embeddings() -> HuggingFaceEndpointEmbeddings:
    """
    Factory singleton para embeddings via HuggingFace Inference API.
    
    Usa la API de HuggingFace en lugar de cargar el modelo localmente,
    lo que reduce significativamente el consumo de RAM.
    
    Modelo: all-MiniLM-L6-v2 (384 dimensiones)
    """
    logger.info(f"Inicializando embeddings via API: {MODEL_NAME}")
    return HuggingFaceEndpointEmbeddings(
        model=MODEL_NAME,
        huggingfacehub_api_token=settings.huggingface_api_key,
    )
