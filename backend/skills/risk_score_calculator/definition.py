"""
Risk Score Calculator - Data Definitions

Pydantic models for bid viability scoring.
Implements weighted scoring with kill switch logic.

Author: TenderCortex Team
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class RiskCategory(str, Enum):
    """Categorías de riesgo para clasificación multidimensional."""
    FINANCIAL = "financial"
    LEGAL = "legal"
    TECHNICAL = "technical"
    REPUTATIONAL = "reputational"


class Severity(str, Enum):
    """
    Niveles de severidad con pesos asociados.
    
    - LOW: Riesgo menor, impacto limitado (2 pts)
    - MEDIUM: Riesgo moderado (5 pts)
    - HIGH: Riesgo significativo (15 pts)
    - CRITICAL: Showstopper - Kill Switch automático
    """
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Recommendation(str, Enum):
    """Recomendaciones de decisión."""
    GO = "GO"
    NO_GO = "NO_GO"
    REVIEW = "REVIEW"


class RiskFactorInput(BaseModel):
    """
    Representa un riesgo individual detectado por un agente.
    
    Este modelo es la entrada estandarizada que todos los agentes
    deben usar para reportar riesgos al calculador.
    """
    
    description: str = Field(
        ...,
        min_length=5,
        description="Descripción breve y clara del riesgo detectado."
    )
    
    category: RiskCategory = Field(
        ...,
        description="Categoría del riesgo: financial, legal, technical, reputational."
    )
    
    severity: Severity = Field(
        ...,
        description="Nivel de severidad: low, medium, high, critical."
    )
    
    probability: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Probabilidad de ocurrencia (0.0 a 1.0). "
                    "Default 1.0 = certeza."
    )
    
    source_agent: str = Field(
        ...,
        description="Nombre del agente que reportó el riesgo "
                    "(ej. 'LegalAgent', 'FinancialAgent')."
    )
    
    evidence: Optional[str] = Field(
        default=None,
        description="Fragmento del documento que respalda el riesgo."
    )
    
    page_reference: Optional[int] = Field(
        default=None,
        ge=1,
        description="Página del pliego donde se identificó el riesgo."
    )
    
    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Normaliza la descripción."""
        return v.strip()


class RiskMatrixCell(BaseModel):
    """Celda de la matriz de riesgo para visualización."""
    
    impact_level: str = Field(
        description="Nivel de impacto: low, medium, high"
    )
    
    probability_level: str = Field(
        description="Nivel de probabilidad: low, medium, high"
    )
    
    risks: List[str] = Field(
        default_factory=list,
        description="Descripciones de riesgos en esta celda."
    )
    
    color: str = Field(
        default="green",
        description="Color de la celda: green, yellow, red."
    )


class CategoryBreakdown(BaseModel):
    """Desglose de score por categoría."""
    
    category: RiskCategory = Field(description="Categoría del desglose.")
    score: float = Field(ge=0, le=100, description="Score de la categoría.")
    risk_count: int = Field(ge=0, description="Cantidad de riesgos.")
    total_penalty: float = Field(ge=0, description="Penalización total.")


class RiskAssessmentOutput(BaseModel):
    """
    Resultado completo del cálculo de viabilidad.
    
    Contiene el score, recomendación y desglose detallado.
    """
    
    total_score: float = Field(
        ...,
        ge=0,
        le=100,
        description="Puntuación final de viabilidad (0-100)."
    )
    
    recommendation: Recommendation = Field(
        ...,
        description="Recomendación: GO, NO_GO, REVIEW."
    )
    
    recommendation_reason: str = Field(
        default="",
        description="Razón de la recomendación."
    )
    
    critical_flags: List[str] = Field(
        default_factory=list,
        description="Lista de riesgos CRITICAL que activaron el Kill Switch."
    )
    
    kill_switch_activated: bool = Field(
        default=False,
        description="Indica si se activó el Kill Switch."
    )
    
    breakdown_by_category: Dict[str, CategoryBreakdown] = Field(
        default_factory=dict,
        description="Puntuación desglosada por categoría."
    )
    
    total_risks: int = Field(
        default=0,
        ge=0,
        description="Total de riesgos evaluados."
    )
    
    high_risks_count: int = Field(
        default=0,
        ge=0,
        description="Cantidad de riesgos HIGH."
    )
    
    risk_matrix: List[RiskMatrixCell] = Field(
        default_factory=list,
        description="Matriz 3x3 de clasificación de riesgos."
    )
    
    def get_traffic_light(self) -> str:
        """Retorna el emoji de semáforo según la recomendación."""
        return {
            Recommendation.GO: "🟢",
            Recommendation.REVIEW: "🟡",
            Recommendation.NO_GO: "🔴",
        }[self.recommendation]
    
    def to_summary(self) -> str:
        """Genera un resumen ejecutivo de una línea."""
        emoji = self.get_traffic_light()
        return (
            f"{emoji} Score: {self.total_score:.1f}/100 | "
            f"Rec: {self.recommendation.value} | "
            f"Riesgos: {self.total_risks} "
            f"({'⚠️ Kill Switch' if self.kill_switch_activated else 'Normal'})"
        )
    
    def to_report(self) -> str:
        """Genera un reporte detallado para el usuario."""
        lines = [
            f"## Resultado de Evaluación de Viabilidad",
            f"",
            f"**Score Total**: {self.total_score:.1f}/100 {self.get_traffic_light()}",
            f"**Recomendación**: {self.recommendation.value}",
            f"**Razón**: {self.recommendation_reason}",
            f"",
        ]
        
        if self.kill_switch_activated:
            lines.extend([
                "### ⚠️ Kill Switch Activado",
                "Los siguientes riesgos críticos descalifican la propuesta:",
                "",
            ])
            for flag in self.critical_flags:
                lines.append(f"- 🔴 {flag}")
            lines.append("")
        
        lines.append("### Desglose por Categoría")
        lines.append("")
        lines.append("| Categoría | Score | Riesgos | Penalización |")
        lines.append("|-----------|-------|---------|--------------|")
        
        for cat, breakdown in self.breakdown_by_category.items():
            lines.append(
                f"| {cat.capitalize()} | {breakdown.score:.1f} | "
                f"{breakdown.risk_count} | -{breakdown.total_penalty:.1f} |"
            )
        
        return "\n".join(lines)


# Custom Exceptions

class RiskCalculatorError(Exception):
    """Excepción base para errores del calculador."""
    pass


class InvalidRiskDataError(RiskCalculatorError):
    """Los datos de riesgo son inválidos."""
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Datos de riesgo inválidos: {reason}")


class EmptyRiskListError(RiskCalculatorError):
    """La lista de riesgos está vacía."""
    def __init__(self):
        super().__init__(
            "La lista de riesgos está vacía. "
            "Se requiere al menos un riesgo para calcular."
        )
