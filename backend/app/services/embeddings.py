from functools import lru_cache

from langchain_huggingface import HuggingFaceEmbeddings

from app.core.logging import get_logger

logger = get_logger(__name__)

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384


@lru_cache
def get_embeddings() -> HuggingFaceEmbeddings:
    """
    Factory singleton para embeddings locales (CPU optimized).
    
    Modelo: all-MiniLM-L6-v2 (384 dimensiones)
    """
    logger.info(f"Cargando modelo de embeddings: {MODEL_NAME}")
    return HuggingFaceEmbeddings(
        model_name=MODEL_NAME,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
