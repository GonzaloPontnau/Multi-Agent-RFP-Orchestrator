from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pinecone import Pinecone, ServerlessSpec

from app.core.config import settings
from app.core.logging import get_logger
from app.services.embeddings import EMBEDDING_DIMENSION, get_embeddings

logger = get_logger(__name__)

INDEX_NAME = "rfp-index"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


class RAGService:
    """Servicio de RAG con Pinecone como vector store."""

    def __init__(self):
        self._pc: Pinecone | None = None
        self._index = None
        self._embeddings = get_embeddings()
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
        )

    @property
    def pc(self) -> Pinecone:
        if self._pc is None:
            self._pc = Pinecone(api_key=settings.pinecone_api_key)
        return self._pc

    async def initialize_index(self) -> None:
        """Verifica o crea el índice en Pinecone."""
        try:
            existing = [idx.name for idx in self.pc.list_indexes()]
            
            if INDEX_NAME not in existing:
                logger.info(f"Creando índice '{INDEX_NAME}' en Pinecone")
                self.pc.create_index(
                    name=INDEX_NAME,
                    dimension=EMBEDDING_DIMENSION,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region=settings.pinecone_env),
                )
            else:
                logger.info(f"Índice '{INDEX_NAME}' ya existe")
            
            self._index = self.pc.Index(INDEX_NAME)
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
            loader = PyPDFLoader(str(file_path))
            pages = loader.load()
            chunks = self._splitter.split_documents(pages)
            
            vectors = []
            for i, chunk in enumerate(chunks):
                embedding = self._embeddings.embed_query(chunk.page_content)
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
                self._index.upsert(vectors=batch)
            
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
            query_embedding = self._embeddings.embed_query(query)
            results = self._index.query(
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


# Singleton
_rag_service: RAGService | None = None


def get_rag_service() -> RAGService:
    """Retorna instancia singleton del RAGService."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
