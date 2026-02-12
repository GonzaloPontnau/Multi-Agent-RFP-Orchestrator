"""
Financial Table Parser Skill

Deterministic financial table extraction from PDF documents.
Provides clean numerical data for calculations.
"""

from .definition import (
    CurrencyType,
    ExtractionResult,
    FinancialParserError,
    FinancialRow,
    FinancialTableOutput,
    InvalidPageRangeError,
    NoTablesFoundError,
    ScannedDocumentError,
    TableExtractionInput,
)

from .impl import (
    FinancialTableParser,
    extract_financial_tables,
)

__all__ = [
    # Classes
    "FinancialTableParser",
    # Models
    "CurrencyType",
    "ExtractionResult",
    "FinancialRow",
    "FinancialTableOutput",
    "TableExtractionInput",
    # Exceptions
    "FinancialParserError",
    "InvalidPageRangeError",
    "NoTablesFoundError",
    "ScannedDocumentError",
    # Functions
    "extract_financial_tables",
]
