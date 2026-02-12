"""
Tech Stack Mapper - Data Definitions

Pydantic models for technology extraction and normalization.
Supports canonical mapping, categorization, and requirement levels.

Author: TenderCortex Team
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class TechCategory(str, Enum):
    """
    Taxonomía de categorías tecnológicas.
    """
    LANGUAGE = "language"
    FRAMEWORK = "framework"
    DATABASE = "database"
    INFRASTRUCTURE = "infrastructure"
    SECURITY_CERT = "security_cert"
    METHODOLOGY = "methodology"
    TOOL = "tool"
    OTHER = "other"


class RequirementLevel(str, Enum):
    """
    Nivel de requisito de la tecnología.
    
    - MANDATORY: Obligatorio, no negociable
    - NICE_TO_HAVE: Deseable, suma puntos
    - FORBIDDEN: Prohibido, no usar
    """
    MANDATORY = "mandatory"
    NICE_TO_HAVE = "nice_to_have"
    FORBIDDEN = "forbidden"


class TechEntity(BaseModel):
    """
    Representa una entidad tecnológica extraída y normalizada.
    """
    
    raw_text: str = Field(
        ...,
        description="Texto original encontrado en el documento."
    )
    
    canonical_name: str = Field(
        ...,
        description="Nombre estandarizado de la tecnología."
    )
    
    category: TechCategory = Field(
        default=TechCategory.OTHER,
        description="Categoría taxonómica de la tecnología."
    )
    
    version_constraint: Optional[str] = Field(
        default=None,
        description="Restricción de versión si existe (ej. '>=3.8', '17')."
    )
    
    requirement_level: RequirementLevel = Field(
        default=RequirementLevel.MANDATORY,
        description="Si es obligatorio, deseable o prohibido."
    )
    
    context_snippet: str = Field(
        default="",
        description="Frase donde se encontró para validación humana."
    )
    
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confianza de la detección (0-1)."
    )
    
    source_page: Optional[int] = Field(
        default=None,
        description="Página donde se encontró."
    )
    
    def get_emoji(self) -> str:
        """Retorna emoji según requirement level."""
        return {
            RequirementLevel.MANDATORY: "✅",
            RequirementLevel.NICE_TO_HAVE: "💡",
            RequirementLevel.FORBIDDEN: "🚫",
        }[self.requirement_level]
    
    def to_summary(self) -> str:
        """Genera resumen de una línea."""
        version = f" {self.version_constraint}" if self.version_constraint else ""
        return (
            f"{self.get_emoji()} {self.canonical_name}{version} "
            f"[{self.category.value}] - {self.requirement_level.value}"
        )


class CompatibilityResult(BaseModel):
    """Resultado de evaluación de compatibilidad con stack de empresa."""
    
    matched: List[str] = Field(
        default_factory=list,
        description="Tecnologías que la empresa tiene y el RFP requiere."
    )
    
    missing: List[str] = Field(
        default_factory=list,
        description="Tecnologías requeridas que la empresa no tiene."
    )
    
    extra: List[str] = Field(
        default_factory=list,
        description="Tecnologías de la empresa no requeridas."
    )
    
    conflicts: List[str] = Field(
        default_factory=list,
        description="Tecnologías que la empresa usa pero están prohibidas."
    )
    
    score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Score de compatibilidad (0-1)."
    )
    
    has_blockers: bool = Field(
        default=False,
        description="True si hay conflictos que bloquean la propuesta."
    )


class TechStackOutput(BaseModel):
    """
    Resultado completo del análisis de stack tecnológico.
    """
    
    entities: List[TechEntity] = Field(
        default_factory=list,
        description="Lista de tecnologías detectadas y normalizadas."
    )
    
    stack_summary: str = Field(
        default="",
        description="Resumen en lenguaje natural del stack solicitado."
    )
    
    mandatory_stack: List[TechEntity] = Field(
        default_factory=list,
        description="Solo tecnologías obligatorias."
    )
    
    nice_to_have_stack: List[TechEntity] = Field(
        default_factory=list,
        description="Tecnologías deseables."
    )
    
    forbidden_stack: List[TechEntity] = Field(
        default_factory=list,
        description="Tecnologías prohibidas."
    )
    
    by_category: Dict[str, List[TechEntity]] = Field(
        default_factory=dict,
        description="Tecnologías agrupadas por categoría."
    )
    
    compatibility: Optional[CompatibilityResult] = Field(
        default=None,
        description="Resultado de compatibilidad si se provee company_stack."
    )
    
    total_entities: int = Field(
        default=0,
        description="Total de entidades detectadas."
    )
    
    warnings: List[str] = Field(
        default_factory=list,
        description="Advertencias de ambigüedad o baja confianza."
    )
    
    def get_by_category(self, category: TechCategory) -> List[TechEntity]:
        """Retorna entidades de una categoría específica."""
        return [e for e in self.entities if e.category == category]
    
    def to_markdown_report(self) -> str:
        """Genera reporte en Markdown."""
        lines = [
            "## Análisis de Stack Tecnológico",
            "",
            f"**Total detectado**: {self.total_entities} tecnologías",
            "",
            "### Stack Obligatorio",
        ]
        
        if self.mandatory_stack:
            for e in self.mandatory_stack:
                lines.append(f"- {e.to_summary()}")
        else:
            lines.append("- Ninguno detectado")
        
        lines.extend(["", "### Tecnologías Deseables"])
        if self.nice_to_have_stack:
            for e in self.nice_to_have_stack:
                lines.append(f"- {e.to_summary()}")
        else:
            lines.append("- Ninguna")
        
        if self.forbidden_stack:
            lines.extend(["", "### ⚠️ Tecnologías Prohibidas"])
            for e in self.forbidden_stack:
                lines.append(f"- {e.to_summary()}")
        
        return "\n".join(lines)


# Custom Exceptions

class TechMapperError(Exception):
    """Excepción base para errores del mapper."""
    pass


class EmptyInputError(TechMapperError):
    """El input está vacío."""
    def __init__(self):
        super().__init__("El texto de entrada está vacío.")


class AmbiguousTechError(TechMapperError):
    """Tecnología ambigua detectada."""
    def __init__(self, tech: str, context: str):
        self.tech = tech
        self.context = context
        super().__init__(
            f"Tecnología ambigua '{tech}' detectada en contexto: '{context}'. "
            f"Requiere validación manual."
        )
