"""
Context Retriever - Data Definitions

Pydantic models for input validation and output schema.
Designed for optimal LLM function calling with rich descriptions.

Author: TenderCortex Team
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class SearchType(str, Enum):
    """
    Estrategia de búsqueda vectorial.
    
    - SIMILARITY: Búsqueda estándar por similitud coseno. Rápida pero puede
      retornar chunks muy similares entre sí (redundancia).
    - MMR: Maximal Marginal Relevance. Penaliza la redundancia para obtener
      resultados más diversos. Más lento pero mejor contexto.
    """
    SIMILARITY = "similarity"
    MMR = "mmr"


class RetrievalInput(BaseModel):
    """
    Esquema de entrada para la herramienta Context Retriever.
    
    Los campos están fuertemente tipados y documentados para guiar al LLM
    en la generación correcta de parámetros durante Function Calling.
    """
    
    query: str = Field(
        ...,
        min_length=3,
        description="La pregunta o concepto a buscar en la base vectorial. "
                    "Debe ser descriptivo para obtener mejores resultados."
    )
    
    top_k: int = Field(
        default=4,
        ge=1,
        le=20,
        description="Número de fragmentos de contexto a recuperar. "
                    "Valores más altos consumen más tokens pero dan más contexto."
    )
    
    search_type: SearchType = Field(
        default=SearchType.MMR,
        description="Estrategia de búsqueda. 'mmr' para diversidad, "
                    "'similarity' para máxima relevancia."
    )
    
    metadata_filter: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Filtros clave-valor para limitar la búsqueda. "
                    "Ejemplo: {'source': 'anexo_legal.pdf', 'page': {'$gt': 10}}"
    )
    
    score_threshold: float = Field(
        default=0.65,
        ge=0.0,
        le=1.0,
        description="Ignorar resultados con similitud menor a este valor. "
                    "Valores altos (>0.8) pueden retornar cero resultados."
    )
    
    lambda_mult: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Solo para MMR: Balance entre relevancia (1.0) y "
                    "diversidad (0.0). Default 0.5 es un buen balance."
    )
    
    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Normaliza y valida la query."""
        v = v.strip()
        if len(v) < 3:
            raise ValueError("La query debe tener al menos 3 caracteres")
        return v


class ContextResult(BaseModel):
    """
    Representa un fragmento de contexto recuperado con metadatos de cita.
    
    Cada resultado incluye información necesaria para auditoría y trazabilidad.
    """
    
    content: str = Field(
        ...,
        description="El contenido textual del fragmento recuperado."
    )
    
    page_number: int = Field(
        ...,
        ge=1,
        description="Número de página de origen en el documento (1-indexed)."
    )
    
    source_file: str = Field(
        ...,
        description="Nombre del archivo PDF de origen."
    )
    
    chunk_id: str = Field(
        ...,
        description="Identificador único del chunk para trazabilidad."
    )
    
    relevance_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Score de similitud/relevancia (0-1). Más alto = más relevante."
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadatos adicionales del chunk (category, chunk_type, etc.)"
    )
    
    def format_citation(self) -> str:
        """Genera una cita formateada para incluir en respuestas."""
        return f"[{self.source_file}, pág. {self.page_number}]"


class RetrievalOutput(BaseModel):
    """Resultado de la operación de recuperación de contexto."""
    
    results: List[ContextResult] = Field(
        default_factory=list,
        description="Lista de fragmentos de contexto ordenados por relevancia."
    )
    
    query: str = Field(
        description="La query original (normalizada)."
    )
    
    total_found: int = Field(
        default=0,
        description="Cantidad total de resultados encontrados antes del threshold."
    )
    
    search_type_used: SearchType = Field(
        description="Tipo de búsqueda utilizado."
    )
    
    warning: Optional[str] = Field(
        default=None,
        description="Advertencia si hay pocos resultados o baja confianza."
    )
    
    def has_results(self) -> bool:
        """Indica si hay resultados disponibles."""
        return len(self.results) > 0
    
    def get_context_string(self, separator: str = "\n\n---\n\n") -> str:
        """
        Genera un string combinando todos los contextos.
        
        Útil para inyectar directamente en prompts del LLM.
        """
        if not self.results:
            return ""
        
        parts = []
        for i, result in enumerate(self.results, 1):
            parts.append(
                f"[Fuente {i}: {result.source_file}, pág. {result.page_number}]\n"
                f"{result.content}"
            )
        return separator.join(parts)
    
    def get_citations(self) -> List[str]:
        """Genera lista de citas para incluir en respuestas."""
        return [r.format_citation() for r in self.results]


# Custom Exceptions

class ContextRetrieverError(Exception):
    """Excepción base para errores del Context Retriever."""
    pass


class IndexEmptyError(ContextRetrieverError):
    """El índice vectorial está vacío, no hay documentos indexados."""
    def __init__(self):
        super().__init__(
            "No hay documentos indexados en el vector store. "
            "Use RFPDocumentLoader para ingestar documentos primero."
        )


class SearchTimeoutError(ContextRetrieverError):
    """La búsqueda excedió el tiempo límite."""
    def __init__(self, query: str, timeout_seconds: float):
        self.query = query
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"La búsqueda para '{query[:50]}...' excedió el timeout de {timeout_seconds}s"
        )


class InvalidFilterError(ContextRetrieverError):
    """El filtro de metadatos es inválido o contiene operadores no soportados."""
    def __init__(self, filter_dict: dict, reason: str = ""):
        self.filter_dict = filter_dict
        self.reason = reason
        super().__init__(
            f"Filtro de metadatos inválido: {filter_dict}. {reason}"
        )
