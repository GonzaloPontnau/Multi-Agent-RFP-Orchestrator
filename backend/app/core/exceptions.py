"""
Custom exceptions for the RFP Multi-Agent Orchestrator.

This module provides a hierarchy of exceptions for consistent error handling
across the application. All exceptions inherit from RFPBaseException.

Example:
    try:
        await rag.ingest_document(path)
    except DocumentIngestionError as e:
        logger.error(f"Ingestion failed: {e}")
"""

from typing import Optional


class RFPBaseException(Exception):
    """
    Base exception class for all RFP Orchestrator errors.
    
    All custom exceptions in the project should inherit from this class
    to enable consistent error handling and logging.

    Attributes:
        message: Human-readable description of the error.
        details: Optional additional context for debugging.
    """

    def __init__(self, message: str, details: Optional[str] = None) -> None:
        """
        Initialize the base exception.

        Args:
            message: Human-readable description of the error.
            details: Optional additional context for debugging.
        """
        self.message = message
        self.details = details
        super().__init__(self.message)

    def __str__(self) -> str:
        """Return string representation with optional details."""
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class DocumentIngestionError(RFPBaseException):
    """
    Exception raised when document ingestion fails.
    
    This can occur during PDF parsing, chunking, or vector storage.

    Attributes:
        filename: Name of the file that failed to ingest.
        stage: The ingestion stage where the error occurred.
    """

    def __init__(
        self,
        message: str,
        filename: Optional[str] = None,
        stage: Optional[str] = None,
        details: Optional[str] = None,
    ) -> None:
        """
        Initialize document ingestion error.

        Args:
            message: Human-readable description of the error.
            filename: Name of the file that failed to ingest.
            stage: The ingestion stage where the error occurred
                   (e.g., 'parsing', 'chunking', 'embedding', 'upserting').
            details: Optional additional context for debugging.
        """
        self.filename = filename
        self.stage = stage
        
        enhanced_message = message
        if filename:
            enhanced_message = f"[{filename}] {enhanced_message}"
        if stage:
            enhanced_message = f"{enhanced_message} (stage: {stage})"
        
        super().__init__(enhanced_message, details)


class AgentProcessingError(RFPBaseException):
    """
    Exception raised when an agent fails to process a request.
    
    This includes errors in routing, generation, or auditing stages
    of the agent pipeline.

    Attributes:
        agent_name: Name/identifier of the agent that failed.
        original_error: The underlying exception if available.
    """

    def __init__(
        self,
        message: str,
        agent_name: str,
        original_error: Optional[Exception] = None,
        details: Optional[str] = None,
    ) -> None:
        """
        Initialize agent processing error.

        Args:
            message: Human-readable description of the error.
            agent_name: Name/identifier of the agent that failed.
            original_error: The underlying exception if available.
            details: Optional additional context for debugging.
        """
        self.agent_name = agent_name
        self.original_error = original_error
        
        enhanced_message = f"[Agent: {agent_name}] {message}"
        if original_error:
            enhanced_message = f"{enhanced_message} | Caused by: {type(original_error).__name__}: {str(original_error)[:200]}"
        
        super().__init__(enhanced_message, details)


class VectorStoreConnectionError(RFPBaseException):
    """
    Exception raised when connection to vector store fails.
    
    This includes Qdrant initialization, collection creation,
    and query execution errors.

    Attributes:
        operation: The operation that failed (e.g., 'connect', 'query', 'upsert').
        collection_name: Name of the vector store collection involved.
    """

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        index_name: Optional[str] = None,
        details: Optional[str] = None,
    ) -> None:
        """
        Initialize vector store connection error.

        Args:
            message: Human-readable description of the error.
            operation: The operation that failed.
            collection_name: Name of the vector store collection involved.
            details: Optional additional context for debugging.
        """
        self.operation = operation
        self.index_name = index_name
        
        enhanced_message = f"[VectorStore] {message}"
        if operation:
            enhanced_message = f"{enhanced_message} (operation: {operation})"
        if index_name:
            enhanced_message = f"{enhanced_message} (index: {index_name})"
        
        super().__init__(enhanced_message, details)


class LLMInvocationError(RFPBaseException):
    """
    Exception raised when LLM invocation fails.
    
    This includes rate limiting, API errors, and response parsing failures.

    Attributes:
        model_name: Name of the LLM model that failed.
        retry_count: Number of retry attempts made before failure.
    """

    def __init__(
        self,
        message: str,
        model_name: Optional[str] = None,
        retry_count: int = 0,
        details: Optional[str] = None,
    ) -> None:
        """
        Initialize LLM invocation error.

        Args:
            message: Human-readable description of the error.
            model_name: Name of the LLM model that failed.
            retry_count: Number of retry attempts made before failure.
            details: Optional additional context for debugging.
        """
        self.model_name = model_name
        self.retry_count = retry_count
        
        enhanced_message = f"[LLM] {message}"
        if model_name:
            enhanced_message = f"{enhanced_message} (model: {model_name})"
        if retry_count > 0:
            enhanced_message = f"{enhanced_message} (retries: {retry_count})"
        
        super().__init__(enhanced_message, details)


class RouterClassificationError(RFPBaseException):
    """
    Exception raised when question routing fails.
    
    This occurs when the router cannot determine the appropriate
    domain for a question.

    Attributes:
        question: The question that failed to route.
        fallback_domain: The domain used as fallback.
    """

    def __init__(
        self,
        message: str,
        question: Optional[str] = None,
        fallback_domain: str = "general",
        details: Optional[str] = None,
    ) -> None:
        """
        Initialize router classification error.

        Args:
            message: Human-readable description of the error.
            question: The question that failed to route (truncated).
            fallback_domain: The domain used as fallback.
            details: Optional additional context for debugging.
        """
        self.question = question[:100] if question else None
        self.fallback_domain = fallback_domain
        
        enhanced_message = f"[Router] {message}"
        if fallback_domain:
            enhanced_message = f"{enhanced_message} (fallback: {fallback_domain})"
        
        super().__init__(enhanced_message, details)
