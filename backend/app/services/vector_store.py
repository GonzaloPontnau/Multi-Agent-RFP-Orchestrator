import asyncio
import unicodedata
from functools import lru_cache, wraps
from pathlib import Path
from typing import Callable, TypeVar

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pinecone import Pinecone, ServerlessSpec

from app.core.config import settings
from app.core.logging import get_logger
from app.services.embeddings import EMBEDDING_DIMENSION, get_embeddings

logger = get_logger(__name__)
T = TypeVar("T")


def _sanitize_to_ascii(text: str) -> str:
    """Normaliza texto a ASCII para IDs de Pinecone."""
    normalized = unicodedata.normalize("NFKD", text)
    return normalized.encode("ascii", "ignore").decode("ascii").replace(" ", "_")


def _ensure_index(method: Callable[..., T]) -> Callable[..., T]:
    """Decorador que inicializa el indice antes de ejecutar el metodo."""
    @wraps(method)
    async def wrapper(self: "RAGService", *args, **kwargs) -> T:
        if self._index is None:
            await self.initialize_index()
        return await method(self, *args, **kwargs)
    return wrapper


class RAGService:
    """Servicio de RAG con Pinecone como vector store."""

    def __init__(self):
        self._pc: Pinecone | None = None
        self._index = None
        self._embeddings = get_embeddings()
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )

    @property
    def pc(self) -> Pinecone:
        if self._pc is None:
            self._pc = Pinecone(api_key=settings.pinecone_api_key)
        return self._pc

    async def initialize_index(self) -> None:
        """Verifica o crea el indice en Pinecone."""
        index_name = settings.pinecone_index_name
        try:
            existing = await asyncio.to_thread(
                lambda: [idx.name for idx in self.pc.list_indexes()]
            )
            if index_name not in existing:
                logger.info(f"Creando indice '{index_name}' en Pinecone")
                await asyncio.to_thread(
                    self.pc.create_index,
                    name=index_name,
                    dimension=EMBEDDING_DIMENSION,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region=settings.pinecone_env),
                )
            self._index = await asyncio.to_thread(self.pc.Index, index_name)
        except Exception as e:
            logger.error(f"Error conectando a Pinecone: {e}")
            raise

    @_ensure_index
    async def ingest_document(self, file_path: Path, original_filename: str | None = None) -> int:
        """Procesa un PDF y sube los chunks a Pinecone."""
        source_name = original_filename or file_path.name
        source_id = _sanitize_to_ascii(Path(source_name).stem)

        try:
            loader = PyPDFLoader(str(file_path))
            pages = await asyncio.to_thread(loader.load)
            chunks = await asyncio.to_thread(self._splitter.split_documents, pages)

            vectors = [
                {
                    "id": f"{source_id}_{i}",
                    "values": await asyncio.to_thread(self._embeddings.embed_query, chunk.page_content),
                    "metadata": {
                        "text": chunk.page_content,
                        "source": source_name,
                        "page": chunk.metadata.get("page", 0),
                    },
                }
                for i, chunk in enumerate(chunks)
            ]

            for batch_start in range(0, len(vectors), 100):
                batch = vectors[batch_start:batch_start + 100]
                await asyncio.to_thread(self._index.upsert, vectors=batch)

            logger.info(f"Ingestados {len(chunks)} chunks de '{source_name}'")
            return len(chunks)
        except Exception as e:
            logger.error(f"Error procesando documento '{file_path}': {e}")
            raise

    @_ensure_index
    async def similarity_search(self, query: str, k: int = 10) -> list[Document]:
        """Busca documentos relevantes para una query."""
        try:
            query_embedding = await asyncio.to_thread(self._embeddings.embed_query, query)
            results = await asyncio.to_thread(
                self._index.query,
                vector=query_embedding,
                top_k=k,
                include_metadata=True,
            )
            return [
                Document(
                    page_content=match.metadata["text"],
                    metadata={
                        "source": match.metadata.get("source", ""),
                        "page": match.metadata.get("page", 0),
                        "score": match.score,
                    },
                )
                for match in results.matches
            ]
        except Exception as e:
            logger.error(f"Error en similarity_search: {e}")
            raise

    async def health_check(self) -> bool:
        """Verifica conectividad con Pinecone."""
        try:
            await asyncio.to_thread(self.pc.list_indexes)
            return True
        except Exception:
            return False

    @_ensure_index
    async def clear_index(self) -> bool:
        """Elimina todos los vectores del indice."""
        try:
            await asyncio.to_thread(self._index.delete, delete_all=True)
            logger.info("Indice limpiado exitosamente")
            return True
        except Exception as e:
            logger.error(f"Error limpiando indice: {e}")
            return False

    @_ensure_index
    async def get_stats(self) -> dict:
        """Obtiene estadisticas del indice."""
        try:
            stats = await asyncio.to_thread(self._index.describe_index_stats)
            return {"total_vectors": stats.total_vector_count, "dimension": stats.dimension}
        except Exception as e:
            logger.error(f"Error obteniendo stats: {e}")
            return {"error": str(e)}


@lru_cache
def get_rag_service() -> RAGService:
    """Retorna instancia singleton del RAGService."""
    return RAGService()
