"""
RFP Document Loader - Data Definitions

Pydantic models for input validation and output schema.
Strongly typed for optimal LLM function calling.

Author: TenderCortex Team
"""

from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator
import os


class ProcessingStrategy(str, Enum):
    """
    Define la profundidad y el costo computacional del análisis de PDF.
    
    - FAST: Solo extrae texto nativo, sin OCR ni análisis de layout
    - OCR_ONLY: Fuerza OCR en todas las páginas (útil para escaneos)
    - HI_RES: Análisis completo con detección de tablas y layout (lento pero preciso)
    """
    FAST = "fast"
    OCR_ONLY = "ocr_only"
    HI_RES = "hi_res"


class RFPLoaderInput(BaseModel):
    """
    Esquema de entrada para la herramienta RFP Document Loader.
    
    Los campos están fuertemente tipados y documentados para guiar al LLM
    en la generación correcta de parámetros durante Function Calling.
    """
    
    file_path: str = Field(
        ...,
        description="Ruta absoluta al archivo PDF en el sistema de archivos local. "
                    "Debe existir y ser legible. Solo se aceptan archivos .pdf"
    )
    
    strategy: ProcessingStrategy = Field(
        default=ProcessingStrategy.HI_RES,
        description="Estrategia de procesamiento. Usar 'fast' para previews rápidos, "
                    "'ocr_only' para escaneos, 'hi_res' para análisis completo con tablas."
    )
    
    extract_tables: bool = Field(
        default=True,
        description="Si es True, detecta tablas y las convierte a formato Markdown. "
                    "Desactivar para procesamiento más rápido si no hay tablas relevantes."
    )
    
    max_pages: Optional[int] = Field(
        default=500,
        description="Límite máximo de páginas a procesar. Documentos más largos "
                    "lanzarán TimeoutError para prevenir bloqueos del sistema."
    )
    
    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        """Valida que la ruta exista y sea un archivo PDF."""
        if not v.lower().endswith(".pdf"):
            raise ValueError("Solo se aceptan archivos PDF (.pdf)")
        if not os.path.isabs(v):
            raise ValueError("La ruta debe ser absoluta")
        return v


class DocumentChunk(BaseModel):
    """
    Representa un fragmento de documento procesado con metadatos ricos.
    
    Cada chunk es una unidad atómica optimizada para indexación vectorial,
    preservando contexto y trazabilidad hacia el documento original.
    """
    
    content: str = Field(
        ...,
        description="El contenido textual limpio y procesado del chunk."
    )
    
    page_number: int = Field(
        ...,
        ge=1,
        description="Página de origen en el PDF (1-indexed)."
    )
    
    chunk_type: Literal["text", "table", "image_caption"] = Field(
        default="text",
        description="Tipo de contenido: 'text' para párrafos, 'table' para tablas "
                    "extraídas, 'image_caption' para texto asociado a imágenes."
    )
    
    source_file: str = Field(
        ...,
        description="Nombre del archivo PDF de origen."
    )
    
    metadata: dict = Field(
        default_factory=dict,
        description="Metadatos adicionales: coordenadas bbox, confianza OCR, "
                    "índice de chunk dentro de la página, etc."
    )
    
    def to_langchain_document(self):
        """Convierte a formato Document de LangChain para compatibilidad."""
        from langchain_core.documents import Document
        return Document(
            page_content=self.content,
            metadata={
                "source": self.source_file,
                "page": self.page_number,
                "chunk_type": self.chunk_type,
                **self.metadata
            }
        )


class RFPLoaderOutput(BaseModel):
    """Resultado del procesamiento de un documento RFP."""
    
    chunks: list[DocumentChunk] = Field(
        default_factory=list,
        description="Lista de chunks extraídos del documento."
    )
    
    total_pages: int = Field(
        default=0,
        description="Número total de páginas en el PDF."
    )
    
    processing_strategy: ProcessingStrategy = Field(
        description="Estrategia utilizada para el procesamiento."
    )
    
    tables_extracted: int = Field(
        default=0,
        description="Número de tablas detectadas y convertidas a Markdown."
    )
    
    ocr_used: bool = Field(
        default=False,
        description="Indica si se utilizó OCR durante el procesamiento."
    )
    
    warnings: list[str] = Field(
        default_factory=list,
        description="Advertencias generadas durante el procesamiento."
    )


# Custom Exceptions

class RFPLoaderError(Exception):
    """Excepción base para errores del RFP Loader."""
    pass


class EncryptedPDFError(RFPLoaderError):
    """El PDF está protegido con contraseña y no puede ser procesado."""
    def __init__(self, file_path: str):
        self.file_path = file_path
        super().__init__(f"PDF encriptado/protegido: {file_path}")


class InvalidPDFError(RFPLoaderError):
    """El archivo no es un PDF válido o está corrupto."""
    def __init__(self, file_path: str, reason: str = ""):
        self.file_path = file_path
        self.reason = reason
        super().__init__(f"PDF inválido '{file_path}': {reason}")


class ProcessingTimeoutError(RFPLoaderError):
    """El procesamiento excedió el tiempo límite."""
    def __init__(self, file_path: str, pages: int, max_pages: int):
        self.file_path = file_path
        self.pages = pages
        self.max_pages = max_pages
        super().__init__(
            f"Documento '{file_path}' tiene {pages} páginas, "
            f"excede el límite de {max_pages}"
        )
