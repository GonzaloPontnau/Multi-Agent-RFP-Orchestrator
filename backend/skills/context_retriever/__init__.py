"""
Context Retriever Skill

Advanced context retrieval for TenderCortex agents with:
- MMR search for result diversity
- Metadata filtering for domain-specific searches
- Score thresholding to prevent hallucinations
"""

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

from .impl import (
    ContextRetriever,
    retrieve_context,
)

__all__ = [
    # Classes
    "ContextRetriever",
    # Models
    "ContextResult",
    "RetrievalInput",
    "RetrievalOutput",
    "SearchType",
    # Exceptions
    "ContextRetrieverError",
    "IndexEmptyError",
    "InvalidFilterError",
    "SearchTimeoutError",
    # Functions
    "retrieve_context",
]
