"""
Financial Table Parser - Data Definitions

Pydantic models for financial table extraction.
Designed for deterministic numerical data extraction from PDF tables.

Author: TenderCortex Team
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator
import os


class CurrencyType(str, Enum):
    """Supported currency types for parsing hints."""
    USD = "USD"
    EUR = "EUR"
    ARS = "ARS"
    BRL = "BRL"
    MXN = "MXN"
    CLP = "CLP"
    COP = "COP"
    PEN = "PEN"


class TableExtractionInput(BaseModel):
    """
    Esquema de entrada para la extracción de tablas financieras.
    
    Los campos están documentados para guiar al LLM en Function Calling.
    """
    
    file_path: str = Field(
        ...,
        description="Ruta absoluta al archivo PDF a procesar."
    )
    
    page_range: str = Field(
        ...,
        description="Páginas a analizar. Formatos: '5-10', '15', '1,3,5-7'. "
                    "Usar 'all' para todo el documento."
    )
    
    currency_hint: CurrencyType = Field(
        default=CurrencyType.USD,
        description="Moneda por defecto si no se detecta símbolo explícito."
    )
    
    confidence_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Umbral mínimo de confianza para considerar una tabla como financiera."
    )
    
    include_raw_data: bool = Field(
        default=True,
        description="Si True, incluye datos originales sin procesar para auditoría."
    )
    
    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        """Valida que la ruta sea absoluta y termine en .pdf."""
        if not v.lower().endswith(".pdf"):
            raise ValueError("Solo se aceptan archivos PDF (.pdf)")
        if not os.path.isabs(v):
            raise ValueError("La ruta debe ser absoluta")
        return v
    
    @field_validator("page_range")
    @classmethod
    def validate_page_range(cls, v: str) -> str:
        """Valida formato de rango de páginas."""
        v = v.strip().lower()
        if v == "all":
            return v
        
        # Validate format: numbers, commas, hyphens
        import re
        if not re.match(r'^[\d,\-\s]+$', v):
            raise ValueError(
                f"Formato de página inválido: '{v}'. "
                "Use: '5-10', '15', '1,3,5-7', o 'all'"
            )
        return v


class FinancialRow(BaseModel):
    """
    Representa una fila de datos financieros extraída y procesada.
    
    Los valores numéricos son floats listos para cálculos.
    """
    
    row_index: int = Field(
        ...,
        ge=0,
        description="Índice de la fila en la tabla original (0-indexed)."
    )
    
    description: str = Field(
        default="",
        description="Concepto, ítem o descripción de la fila."
    )
    
    unit_price: Optional[float] = Field(
        default=None,
        description="Precio unitario parseado como float."
    )
    
    quantity: Optional[float] = Field(
        default=None,
        description="Cantidad parseada como float."
    )
    
    total_price: Optional[float] = Field(
        default=None,
        description="Precio total parseado como float."
    )
    
    category: Optional[str] = Field(
        default=None,
        description="Categoría de la fila (de celdas fusionadas verticales)."
    )
    
    raw_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Datos originales de la fila sin procesar para auditoría."
    )
    
    def calculate_total(self) -> Optional[float]:
        """Calcula el total si hay precio unitario y cantidad."""
        if self.unit_price is not None and self.quantity is not None:
            return self.unit_price * self.quantity
        return self.total_price


class FinancialTableOutput(BaseModel):
    """
    Representa una tabla financiera extraída completamente procesada.
    """
    
    table_id: int = Field(
        ...,
        description="Identificador secuencial de la tabla en el documento."
    )
    
    page_number: int = Field(
        ...,
        ge=1,
        description="Número de página donde se encontró la tabla."
    )
    
    headers: List[str] = Field(
        default_factory=list,
        description="Encabezados de la tabla normalizados (snake_case)."
    )
    
    headers_original: List[str] = Field(
        default_factory=list,
        description="Encabezados originales sin normalizar."
    )
    
    rows: List[FinancialRow] = Field(
        default_factory=list,
        description="Filas de datos financieros parseados."
    )
    
    total_detected: float = Field(
        default=0.0,
        description="Suma calculada de la columna de totales para validación."
    )
    
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Score de confianza de que es una tabla financiera (0-1)."
    )
    
    currency_detected: Optional[str] = Field(
        default=None,
        description="Moneda detectada en la tabla (USD, EUR, etc.)."
    )
    
    warnings: List[str] = Field(
        default_factory=list,
        description="Advertencias durante el procesamiento."
    )
    
    def get_column_sum(self, column: str) -> float:
        """Calcula la suma de una columna específica."""
        total = 0.0
        for row in self.rows:
            value = getattr(row, column, None)
            if value is not None:
                total += value
        return total
    
    def to_dict_list(self) -> List[Dict[str, Any]]:
        """Convierte las filas a lista de diccionarios para JSON/DataFrame."""
        return [
            {
                "row_index": row.row_index,
                "description": row.description,
                "unit_price": row.unit_price,
                "quantity": row.quantity,
                "total_price": row.total_price,
                "category": row.category,
            }
            for row in self.rows
        ]


class ExtractionResult(BaseModel):
    """Resultado completo de la extracción de tablas financieras."""
    
    tables: List[FinancialTableOutput] = Field(
        default_factory=list,
        description="Lista de tablas financieras extraídas."
    )
    
    file_path: str = Field(
        description="Ruta del archivo procesado."
    )
    
    pages_processed: List[int] = Field(
        default_factory=list,
        description="Lista de páginas procesadas."
    )
    
    total_tables_found: int = Field(
        default=0,
        description="Total de tablas encontradas (antes de filtrar por confianza)."
    )
    
    grand_total: float = Field(
        default=0.0,
        description="Suma de todos los totales de todas las tablas."
    )
    
    warnings: List[str] = Field(
        default_factory=list,
        description="Advertencias globales del procesamiento."
    )
    
    def has_tables(self) -> bool:
        """Indica si se encontraron tablas financieras."""
        return len(self.tables) > 0


# Custom Exceptions

class FinancialParserError(Exception):
    """Excepción base para errores del parser financiero."""
    pass


class NoTablesFoundError(FinancialParserError):
    """No se encontraron tablas en las páginas especificadas."""
    def __init__(self, pages: List[int]):
        self.pages = pages
        super().__init__(
            f"No se encontraron tablas en las páginas: {pages}"
        )


class InvalidPageRangeError(FinancialParserError):
    """El rango de páginas es inválido o está fuera de los límites."""
    def __init__(self, page_range: str, max_pages: int):
        self.page_range = page_range
        self.max_pages = max_pages
        super().__init__(
            f"Rango de páginas inválido: '{page_range}'. "
            f"El documento tiene {max_pages} páginas."
        )


class ScannedDocumentError(FinancialParserError):
    """El documento parece ser un escaneo sin capa de texto."""
    def __init__(self, page: int):
        self.page = page
        super().__init__(
            f"La página {page} parece ser un escaneo sin texto. "
            f"Use RFPDocumentLoader con OCR primero."
        )
