import asyncio
from functools import lru_cache
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pinecone import Pinecone, ServerlessSpec

from app.core.config import settings
from app.core.logging import get_logger
from app.services.embeddings import EMBEDDING_DIMENSION, get_embeddings

logger = get_logger(__name__)


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
        """Verifica o crea el índice en Pinecone."""
        index_name = settings.pinecone_index_name
        
        try:
            existing = await asyncio.to_thread(
                lambda: [idx.name for idx in self.pc.list_indexes()]
            )
            
            if index_name not in existing:
                logger.info(f"Creando índice '{index_name}' en Pinecone")
                await asyncio.to_thread(
                    self.pc.create_index,
                    name=index_name,
                    dimension=EMBEDDING_DIMENSION,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region=settings.pinecone_env),
                )
            else:
                logger.info(f"Índice '{index_name}' ya existe")
            
            self._index = await asyncio.to_thread(self.pc.Index, index_name)
        except Exception as e:
            logger.error(f"Error conectando a Pinecone: {e}")
            raise

    async def ingest_document(self, file_path: Path) -> int:
        """
        Procesa un PDF y sube los chunks a Pinecone.
        
        Returns:
            Número de chunks procesados
        """
        if self._index is None:
            await self.initialize_index()

        try:
            # Operaciones CPU-bound en thread separado
            loader = PyPDFLoader(str(file_path))
            pages = await asyncio.to_thread(loader.load)
            chunks = await asyncio.to_thread(self._splitter.split_documents, pages)
            
            vectors = []
            for i, chunk in enumerate(chunks):
                embedding = await asyncio.to_thread(
                    self._embeddings.embed_query, chunk.page_content
                )
                vectors.append({
                    "id": f"{file_path.stem}_{i}",
                    "values": embedding,
                    "metadata": {
                        "text": chunk.page_content,
                        "source": file_path.name,
                        "page": chunk.metadata.get("page", 0),
                    },
                })
            
            # Upsert en batches de 100
            for batch_start in range(0, len(vectors), 100):
                batch = vectors[batch_start : batch_start + 100]
                await asyncio.to_thread(self._index.upsert, vectors=batch)
            
            logger.info(f"Ingestados {len(chunks)} chunks de '{file_path.name}'")
            return len(chunks)
            
        except Exception as e:
            logger.error(f"Error procesando documento '{file_path}': {e}")
            raise

    async def similarity_search(self, query: str, k: int = 5) -> list[Document]:
        """
        Busca documentos relevantes para una query.
        
        Args:
            query: Texto de búsqueda
            k: Número de resultados
        """
        if self._index is None:
            await self.initialize_index()

        try:
            query_embedding = await asyncio.to_thread(
                self._embeddings.embed_query, query
            )
            results = await asyncio.to_thread(
                self._index.query,
                vector=query_embedding,
                top_k=k,
                include_metadata=True,
            )
            
            documents = [
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
            
            logger.debug(f"Encontrados {len(documents)} documentos para query")
            return documents
            
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


@lru_cache
def get_rag_service() -> RAGService:
    """Retorna instancia singleton thread-safe del RAGService."""
    return RAGService()
