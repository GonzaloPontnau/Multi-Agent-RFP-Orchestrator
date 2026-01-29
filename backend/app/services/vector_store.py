import asyncio
from functools import lru_cache, wraps
from pathlib import Path
from typing import Callable, TypeVar

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from langchain_qdrant import QdrantVectorStore

from app.core.config import settings
from app.core.logging import get_logger
from app.services.embeddings import EMBEDDING_DIMENSION, get_embeddings

logger = get_logger(__name__)
T = TypeVar("T")

COLLECTION_NAME = "rfp_demo_collection"


def _ensure_initialized(method: Callable[..., T]) -> Callable[..., T]:
    """Decorador que inicializa el vector store antes de ejecutar el metodo."""
    @wraps(method)
    async def wrapper(self: "RAGService", *args, **kwargs) -> T:
        if self._vector_store is None:
            await self._initialize()
        return await method(self, *args, **kwargs)
    return wrapper


class RAGService:
    """Servicio de RAG con Qdrant in-memory como vector store.
    
    Zero-maintenance solution for ephemeral containers.
    Data is stored entirely in RAM and will be wiped on restart.
    """

    def __init__(self):
        self._client: QdrantClient | None = None
        self._vector_store: QdrantVectorStore | None = None
        self._embeddings = get_embeddings()
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )

    async def _initialize(self) -> None:
        """Inicializa el cliente Qdrant in-memory y el vector store."""
        try:
            # Create in-memory Qdrant client (no API keys, no persistence)
            self._client = QdrantClient(location=":memory:")
            
            # Create collection if it doesn't exist
            collections = await asyncio.to_thread(self._client.get_collections)
            collection_names = [c.name for c in collections.collections]
            
            if COLLECTION_NAME not in collection_names:
                logger.info(f"Creando colección '{COLLECTION_NAME}' en Qdrant in-memory")
                await asyncio.to_thread(
                    self._client.create_collection,
                    collection_name=COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=EMBEDDING_DIMENSION,
                        distance=Distance.COSINE,
                    ),
                )
            
            # Create LangChain vector store wrapper
            self._vector_store = QdrantVectorStore(
                client=self._client,
                collection_name=COLLECTION_NAME,
                embedding=self._embeddings,
            )
            
            logger.info("Qdrant in-memory inicializado correctamente")
        except Exception as e:
            logger.error(f"Error inicializando Qdrant in-memory: {e}")
            raise

    @_ensure_initialized
    async def ingest_document(self, file_path: Path, original_filename: str | None = None) -> int:
        """Procesa un PDF y sube los chunks al vector store in-memory."""
        source_name = original_filename or file_path.name

        try:
            loader = PyPDFLoader(str(file_path))
            pages = await asyncio.to_thread(loader.load)
            chunks = await asyncio.to_thread(self._splitter.split_documents, pages)

            # Add source metadata to each chunk
            for chunk in chunks:
                chunk.metadata["source"] = source_name

            # Add documents to vector store
            await asyncio.to_thread(self._vector_store.add_documents, chunks)

            logger.info(f"Ingestados {len(chunks)} chunks de '{source_name}'")
            return len(chunks)
        except Exception as e:
            logger.error(f"Error procesando documento '{file_path}': {e}")
            raise

    @_ensure_initialized
    async def similarity_search(self, query: str, k: int = 10) -> list[Document]:
        """Busca documentos relevantes para una query."""
        try:
            results = await asyncio.to_thread(
                self._vector_store.similarity_search_with_score,
                query,
                k=k,
            )
            return [
                Document(
                    page_content=doc.page_content,
                    metadata={
                        "source": doc.metadata.get("source", ""),
                        "page": doc.metadata.get("page", 0),
                        "score": score,
                    },
                )
                for doc, score in results
            ]
        except Exception as e:
            logger.error(f"Error en similarity_search: {e}")
            raise

    async def health_check(self) -> bool:
        """Verifica que el servicio esté operativo."""
        try:
            if self._client is None:
                await self._initialize()
            # Simple check: get collections list
            await asyncio.to_thread(self._client.get_collections)
            return True
        except Exception:
            return False

    @_ensure_initialized
    async def clear_index(self) -> bool:
        """Elimina todos los vectores recreando la colección."""
        try:
            # Recreate collection to wipe all data instantly
            await asyncio.to_thread(
                self._client.recreate_collection,
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=EMBEDDING_DIMENSION,
                    distance=Distance.COSINE,
                ),
            )
            
            # Recreate vector store wrapper
            self._vector_store = QdrantVectorStore(
                client=self._client,
                collection_name=COLLECTION_NAME,
                embedding=self._embeddings,
            )
            
            logger.info("Colección recreada exitosamente (datos limpiados)")
            return True
        except Exception as e:
            logger.error(f"Error limpiando colección: {e}")
            return False

    @_ensure_initialized
    async def get_stats(self) -> dict:
        """Obtiene estadisticas de la colección."""
        try:
            collection_info = await asyncio.to_thread(
                self._client.get_collection,
                collection_name=COLLECTION_NAME,
            )
            return {
                "total_vectors": collection_info.points_count,
                "dimension": EMBEDDING_DIMENSION,
            }
        except Exception as e:
            logger.error(f"Error obteniendo stats: {e}")
            return {"error": str(e)}

    @_ensure_initialized
    async def get_indexed_documents(self) -> list[dict]:
        """Obtiene lista de documentos indexados con metadata básica.
        
        Returns:
            Lista de dicts con 'name' (source) y 'chunks' (count estimado).
        """
        try:
            # Scroll through all points to extract unique sources
            # Using scroll instead of query for better coverage
            records, _ = await asyncio.to_thread(
                self._client.scroll,
                collection_name=COLLECTION_NAME,
                limit=1000,
                with_payload=True,
            )
            
            # Aggregate by source
            source_counts: dict[str, int] = {}
            for record in records:
                if record.payload:
                    source = record.payload.get("metadata", {}).get("source", "unknown")
                    source_counts[source] = source_counts.get(source, 0) + 1
            
            # Convert to list format expected by frontend
            documents = [
                {"name": source, "chunks": count}
                for source, count in source_counts.items()
            ]
            
            logger.debug(f"Found {len(documents)} indexed documents")
            return documents
        except Exception as e:
            logger.error(f"Error obteniendo documentos indexados: {e}")
            return []


@lru_cache
def get_rag_service() -> RAGService:
    """Retorna instancia singleton del RAGService."""
    return RAGService()
