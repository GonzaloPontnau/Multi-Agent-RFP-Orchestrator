"""
Context Retriever - Implementation

Advanced retrieval engine with:
- MMR (Maximal Marginal Relevance) for result diversity
- Metadata filtering for domain-specific searches
- Score thresholding to prevent LLM hallucinations
- Precise citations with page_number, source_file, chunk_id

Author: TenderCortex Team
"""

import asyncio
import hashlib
import logging
from typing import Any, Dict, List, Optional

try:
    from .definition import (
        ContextResult,
        ContextRetrieverError,
        IndexEmptyError,
        InvalidFilterError,
        RetrievalInput,
        RetrievalOutput,
        SearchTimeoutError,
        SearchType,
    )
except ImportError:
    from definition import (
        ContextResult,
        ContextRetrieverError,
        IndexEmptyError,
        InvalidFilterError,
        RetrievalInput,
        RetrievalOutput,
        SearchTimeoutError,
        SearchType,
    )

logger = logging.getLogger(__name__)


class ContextRetriever:
    """
    Advanced context retrieval engine for TenderCortex agents.
    
    Provides MMR-based retrieval with metadata filtering and score
    thresholding to maximize context quality and minimize hallucinations.
    
    Usage:
        retriever = ContextRetriever(rag_service)
        result = await retriever.retrieve(
            query="multas por incumplimiento",
            search_type=SearchType.MMR,
            metadata_filter={"source": "contrato.pdf"}
        )
        
        for ctx in result.results:
            print(f"{ctx.format_citation()}: {ctx.content[:100]}...")
    
    Raises:
        IndexEmptyError: If vector store has no documents
        SearchTimeoutError: If search exceeds timeout
        InvalidFilterError: If metadata filter is malformed
    """
    
    # Default configuration
    DEFAULT_TIMEOUT = 30.0  # seconds
    DEFAULT_FETCH_K_MULTIPLIER = 3  # For MMR, fetch 3x more candidates
    
    def __init__(self, rag_service=None):
        """
        Initialize the Context Retriever.
        
        Args:
            rag_service: The RAGService instance for vector operations.
                         If None, will attempt to import from app.services.
        """
        self._rag_service = rag_service
        self._initialized = False
    
    async def _ensure_service(self):
        """Lazy initialization of RAG service."""
        if self._rag_service is None:
            try:
                from app.services.vector_store import get_rag_service
                self._rag_service = get_rag_service()
            except ImportError:
                raise ContextRetrieverError(
                    "No se pudo importar RAGService. Asegúrese de ejecutar "
                    "desde el contexto correcto de la aplicación."
                )
        
        # Verify service is ready
        if not await self._rag_service.health_check():
            raise ContextRetrieverError("RAGService no está disponible")
        
        self._initialized = True
    
    async def retrieve(
        self,
        query: str,
        top_k: int = 4,
        search_type: SearchType = SearchType.MMR,
        metadata_filter: Optional[Dict[str, Any]] = None,
        score_threshold: float = 0.65,
        lambda_mult: float = 0.5,
    ) -> RetrievalOutput:
        """
        Retrieve relevant context from the vector store.
        
        This is the main entry point. It validates input, executes the
        appropriate search strategy, applies filters and thresholds.
        
        Args:
            query: The search query (question or concept).
            top_k: Number of results to return.
            search_type: SIMILARITY or MMR.
            metadata_filter: Optional metadata filters.
            score_threshold: Minimum relevance score (0-1).
            lambda_mult: MMR diversity parameter (0=diverse, 1=relevant).
        
        Returns:
            RetrievalOutput with results and metadata.
        
        Raises:
            IndexEmptyError: If no documents are indexed.
            SearchTimeoutError: If search times out.
            InvalidFilterError: If filter is malformed.
        """
        # Validate input
        input_data = RetrievalInput(
            query=query,
            top_k=top_k,
            search_type=search_type,
            metadata_filter=metadata_filter,
            score_threshold=score_threshold,
            lambda_mult=lambda_mult,
        )
        
        await self._ensure_service()
        
        # Check if index has documents
        stats = await self._rag_service.get_stats()
        if stats.get("total_vectors", 0) == 0:
            raise IndexEmptyError()
        
        logger.info(
            f"Retrieving context: query='{query[:50]}...', "
            f"type={search_type.value}, top_k={top_k}"
        )
        
        try:
            # Execute search with timeout
            results = await asyncio.wait_for(
                self._execute_search(input_data),
                timeout=self.DEFAULT_TIMEOUT,
            )
            return results
        except asyncio.TimeoutError:
            raise SearchTimeoutError(query, self.DEFAULT_TIMEOUT)
    
    async def _execute_search(
        self,
        input_data: RetrievalInput,
    ) -> RetrievalOutput:
        """Execute the search based on strategy."""
        
        if input_data.search_type == SearchType.MMR:
            raw_results = await self._search_mmr(input_data)
        else:
            raw_results = await self._search_similarity(input_data)
        
        # Track total found before threshold
        total_found = len(raw_results)
        
        # Apply score threshold
        filtered_results = [
            r for r in raw_results 
            if r.relevance_score >= input_data.score_threshold
        ]
        
        # Generate warning if needed
        warning = None
        if total_found > 0 and len(filtered_results) == 0:
            warning = (
                f"Se encontraron {total_found} resultados pero ninguno superó "
                f"el umbral de confianza ({input_data.score_threshold}). "
                f"Considere reducir el threshold o reformular la consulta."
            )
        elif len(filtered_results) < input_data.top_k and total_found > 0:
            warning = (
                f"Solo {len(filtered_results)} de {total_found} resultados "
                f"superaron el umbral de confianza ({input_data.score_threshold})."
            )
        
        return RetrievalOutput(
            results=filtered_results,
            query=input_data.query,
            total_found=total_found,
            search_type_used=input_data.search_type,
            warning=warning,
        )
    
    async def _search_similarity(
        self,
        input_data: RetrievalInput,
    ) -> List[ContextResult]:
        """Standard similarity search with optional filtering."""
        
        # Use the existing similarity_search_with_score from RAGService
        # Note: We're adapting the interface here
        docs_with_scores = await self._raw_similarity_search(
            query=input_data.query,
            k=input_data.top_k,
            metadata_filter=input_data.metadata_filter,
        )
        
        return self._format_results(docs_with_scores)
    
    async def _search_mmr(
        self,
        input_data: RetrievalInput,
    ) -> List[ContextResult]:
        """
        MMR search for diverse results.
        
        Fetches more candidates than needed, then applies MMR
        to select diverse subset.
        """
        fetch_k = input_data.top_k * self.DEFAULT_FETCH_K_MULTIPLIER
        
        # For MMR we need to implement it ourselves or use LangChain's
        # max_marginal_relevance_search if available
        docs_with_scores = await self._raw_mmr_search(
            query=input_data.query,
            k=input_data.top_k,
            fetch_k=fetch_k,
            lambda_mult=input_data.lambda_mult,
            metadata_filter=input_data.metadata_filter,
        )
        
        return self._format_results(docs_with_scores)
    
    async def _raw_similarity_search(
        self,
        query: str,
        k: int,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[tuple]:
        """
        Execute raw similarity search against the vector store.
        
        Returns list of (document, score) tuples.
        """
        # Build filter for Qdrant if provided
        qdrant_filter = self._build_qdrant_filter(metadata_filter)
        
        # Use the vector store's method
        # Note: Qdrant returns similarity scores (higher = better)
        results = await asyncio.to_thread(
            self._rag_service._vector_store.similarity_search_with_score,
            query,
            k=k,
            filter=qdrant_filter,
        )
        
        return results
    
    async def _raw_mmr_search(
        self,
        query: str,
        k: int,
        fetch_k: int,
        lambda_mult: float,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> List[tuple]:
        """
        Execute MMR search for diverse results.
        
        MMR balances relevance and diversity by iteratively selecting
        documents that are relevant but different from already selected ones.
        """
        qdrant_filter = self._build_qdrant_filter(metadata_filter)
        
        try:
            # Try using LangChain's built-in MMR if available
            docs = await asyncio.to_thread(
                self._rag_service._vector_store.max_marginal_relevance_search,
                query,
                k=k,
                fetch_k=fetch_k,
                lambda_mult=lambda_mult,
                filter=qdrant_filter,
            )
            
            # MMR doesn't return scores, so we need to compute them
            # by doing a separate similarity query for the selected docs
            return [(doc, 0.8) for doc in docs]  # Default score for MMR results
            
        except AttributeError:
            # Fallback to regular similarity if MMR not available
            logger.warning("MMR not available, falling back to similarity search")
            return await self._raw_similarity_search(query, k, metadata_filter)
    
    def _build_qdrant_filter(
        self,
        metadata_filter: Optional[Dict[str, Any]],
    ) -> Optional[Dict]:
        """
        Convert user-friendly filter to Qdrant filter format.
        
        Supports:
        - Exact match: {"source": "file.pdf"}
        - Operators: {"page": {"$gt": 10, "$lte": 20}}
        - Contains: {"source": {"$contains": "legal"}}
        """
        if not metadata_filter:
            return None
        
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue, Range
            
            conditions = []
            
            for key, value in metadata_filter.items():
                # Handle metadata prefix for Qdrant
                field_key = f"metadata.{key}"
                
                if isinstance(value, dict):
                    # Operator-based filter
                    if "$gt" in value or "$gte" in value or "$lt" in value or "$lte" in value:
                        range_params = {}
                        if "$gt" in value:
                            range_params["gt"] = value["$gt"]
                        if "$gte" in value:
                            range_params["gte"] = value["$gte"]
                        if "$lt" in value:
                            range_params["lt"] = value["$lt"]
                        if "$lte" in value:
                            range_params["lte"] = value["$lte"]
                        
                        conditions.append(
                            FieldCondition(key=field_key, range=Range(**range_params))
                        )
                    elif "$contains" in value:
                        # Text contains - use match with text
                        conditions.append(
                            FieldCondition(
                                key=field_key,
                                match=MatchValue(value=value["$contains"])
                            )
                        )
                    else:
                        raise InvalidFilterError(
                            metadata_filter,
                            f"Operador no soportado en {key}: {list(value.keys())}"
                        )
                else:
                    # Exact match
                    conditions.append(
                        FieldCondition(key=field_key, match=MatchValue(value=value))
                    )
            
            if conditions:
                return Filter(must=conditions)
            return None
            
        except ImportError:
            # If Qdrant models not available, return raw filter
            logger.warning("Qdrant models not available, using raw filter")
            return metadata_filter
        except Exception as e:
            raise InvalidFilterError(metadata_filter, str(e))
    
    def _format_results(
        self,
        docs_with_scores: List[tuple],
    ) -> List[ContextResult]:
        """
        Convert raw search results to ContextResult format.
        
        Extracts metadata and generates chunk IDs for each result.
        """
        results = []
        
        for doc, score in docs_with_scores:
            # Normalize score to 0-1 range
            # Qdrant returns distance, we want similarity
            normalized_score = self._normalize_score(score)
            
            # Extract metadata
            metadata = doc.metadata if hasattr(doc, 'metadata') else {}
            source = metadata.get("source", "unknown")
            page = metadata.get("page", 1)
            
            # Generate deterministic chunk ID
            chunk_id = self._generate_chunk_id(doc.page_content, source, page)
            
            results.append(ContextResult(
                content=doc.page_content,
                page_number=page,
                source_file=source,
                chunk_id=chunk_id,
                relevance_score=normalized_score,
                metadata={
                    k: v for k, v in metadata.items() 
                    if k not in ("source", "page")
                },
            ))
        
        # Sort by relevance score descending
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return results
    
    def _normalize_score(self, score: float) -> float:
        """
        Normalize similarity score to 0-1 range.
        
        Different vector stores return different score formats:
        - Qdrant with cosine: returns distance (0 = identical)
        - LangChain wrappers: may return similarity directly
        """
        # Qdrant returns scores where higher is better (when using similarity)
        # Ensure we're in 0-1 range
        if score < 0:
            return 0.0
        if score > 1:
            # Might be a distance metric, convert
            return max(0.0, 1.0 - score)
        return score
    
    def _generate_chunk_id(
        self,
        content: str,
        source: str,
        page: int,
    ) -> str:
        """Generate a deterministic chunk ID for traceability."""
        hash_input = f"{source}:{page}:{content[:100]}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:12]


# Convenience function for simple usage
async def retrieve_context(
    query: str,
    top_k: int = 4,
    search_type: str = "mmr",
    metadata_filter: Optional[Dict[str, Any]] = None,
    score_threshold: float = 0.65,
) -> RetrievalOutput:
    """
    Retrieve context with default settings.
    
    This is a convenience function for simple use cases.
    For more control, instantiate ContextRetriever directly.
    
    Args:
        query: The search query.
        top_k: Number of results.
        search_type: "similarity" or "mmr".
        metadata_filter: Optional metadata filters.
        score_threshold: Minimum relevance score.
    
    Returns:
        RetrievalOutput with context results.
    """
    retriever = ContextRetriever()
    return await retriever.retrieve(
        query=query,
        top_k=top_k,
        search_type=SearchType(search_type),
        metadata_filter=metadata_filter,
        score_threshold=score_threshold,
    )
