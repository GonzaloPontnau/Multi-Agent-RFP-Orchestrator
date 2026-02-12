"""
RFP Document Loader Skill

Production-grade PDF ingestion engine for TenderCortex.
"""

from .definition import (
    DocumentChunk,
    EncryptedPDFError,
    InvalidPDFError,
    ProcessingStrategy,
    ProcessingTimeoutError,
    RFPLoaderInput,
    RFPLoaderOutput,
    RFPLoaderError,
)

from .impl import (
    RFPLoader,
    load_rfp_document,
)

__all__ = [
    # Classes
    "RFPLoader",
    # Models
    "DocumentChunk",
    "ProcessingStrategy",
    "RFPLoaderInput",
    "RFPLoaderOutput",
    # Exceptions
    "RFPLoaderError",
    "EncryptedPDFError",
    "InvalidPDFError",
    "ProcessingTimeoutError",
    # Functions
    "load_rfp_document",
]
