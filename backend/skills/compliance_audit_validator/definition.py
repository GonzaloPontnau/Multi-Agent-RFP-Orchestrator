"""
Compliance Audit Validator - Data Definitions

Pydantic models for requirement compliance auditing.
Implements traffic light protocol with gap analysis.

Author: TenderCortex Team
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class ComplianceStatus(str, Enum):
    """
    Traffic Light Protocol for compliance status.
    
    - COMPLIANT: Cumple totalmente el requisito.
    - NON_COMPLIANT: Incumplimiento claro (crítico si es MANDATORY).
    - PARTIAL: Cumple parcialmente, requiere aclaración.
    - MISSING_INFO: No hay información suficiente para decidir.
    """
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIAL = "partial"
    MISSING_INFO = "missing_info"


class SeverityLevel(str, Enum):
    """
    Severidad del requisito detectada por análisis de lenguaje.
    
    - MANDATORY: Kill Criteria (DEBE, SHALL, MUST, obligatorio).
    - DESIRABLE: Scoring Criteria (se valorará, preferible, plus).
    """
    MANDATORY = "mandatory"
    DESIRABLE = "desirable"


class RequirementCategory(str, Enum):
    """Categorías de requisitos para clasificación."""
    LEGAL = "legal"
    TECHNICAL = "technical"
    FINANCIAL = "financial"
    ADMINISTRATIVE = "administrative"
    EXPERIENCE = "experience"
    CERTIFICATION = "certification"
    OTHER = "other"


class ComplianceCheckInput(BaseModel):
    """
    Esquema de entrada para la validación de cumplimiento.
    
    Los campos están documentados para guiar al LLM en Function Calling.
    """
    
    requirement_text: str = Field(
        ...,
        min_length=10,
        description="El texto exacto del requisito extraído del pliego. "
                    "Debe incluir el contexto completo de la exigencia."
    )
    
    requirement_source_page: int = Field(
        ...,
        ge=1,
        description="Número de página donde aparece el requisito en el pliego."
    )
    
    company_context: str = Field(
        ...,
        min_length=10,
        description="Fragmentos relevantes del perfil de la empresa que podrían "
                    "demostrar cumplimiento. Incluir: CVs, certificaciones, "
                    "contratos previos, estados financieros."
    )
    
    requirement_category: Optional[RequirementCategory] = Field(
        default=None,
        description="Categoría opcional del requisito para clasificación."
    )
    
    @field_validator("requirement_text")
    @classmethod
    def validate_requirement_text(cls, v: str) -> str:
        """Valida y normaliza el texto del requisito."""
        v = v.strip()
        if len(v) < 10:
            raise ValueError("El texto del requisito es demasiado corto")
        return v
    
    @field_validator("company_context")
    @classmethod
    def validate_company_context(cls, v: str) -> str:
        """Valida el contexto de la empresa."""
        v = v.strip()
        if len(v) < 10:
            raise ValueError("El contexto de la empresa es demasiado corto")
        return v


class AuditResult(BaseModel):
    """
    Resultado de la auditoría de un requisito específico.
    
    Contiene el veredicto, razonamiento y análisis de brechas.
    """
    
    status: ComplianceStatus = Field(
        ...,
        description="Veredicto del cumplimiento: COMPLIANT, NON_COMPLIANT, "
                    "PARTIAL, o MISSING_INFO."
    )
    
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Nivel de certeza del veredicto (0.0 - 1.0). "
                    "Scores < 0.7 sugieren revisar manualmente."
    )
    
    reasoning: str = Field(
        ...,
        description="Explicación paso a paso del veredicto. "
                    "Debe ser auditable y trazable."
    )
    
    gap_analysis: Optional[str] = Field(
        default=None,
        description="Qué falta exactamente para cumplir el requisito. "
                    "Solo aplica para NON_COMPLIANT o PARTIAL."
    )
    
    severity_detected: SeverityLevel = Field(
        ...,
        description="Si el requisito parece obligatorio (MANDATORY) u "
                    "opcional/puntuable (DESIRABLE)."
    )
    
    evidence_found: Optional[str] = Field(
        default=None,
        description="Fragmento exacto del company_context que respalda "
                    "el veredicto. Para auditoría."
    )
    
    requirement_page: int = Field(
        ...,
        ge=1,
        description="Página de referencia del requisito."
    )
    
    def is_showstopper(self) -> bool:
        """Indica si este resultado es un Showstopper (descalificante)."""
        return (
            self.severity_detected == SeverityLevel.MANDATORY and 
            self.status == ComplianceStatus.NON_COMPLIANT
        )
    
    def to_summary(self) -> str:
        """Genera un resumen ejecutivo del resultado."""
        emoji = {
            ComplianceStatus.COMPLIANT: "🟢",
            ComplianceStatus.NON_COMPLIANT: "🔴",
            ComplianceStatus.PARTIAL: "🟡",
            ComplianceStatus.MISSING_INFO: "⚪",
        }
        severity_label = "⚠️ OBLIGATORIO" if self.severity_detected == SeverityLevel.MANDATORY else "📊 Puntuable"
        return (
            f"{emoji[self.status]} {self.status.value.upper()} | "
            f"{severity_label} | Pág. {self.requirement_page} | "
            f"Confianza: {self.confidence_score:.0%}"
        )


class BatchAuditResult(BaseModel):
    """Resultado de auditoría de múltiples requisitos."""
    
    results: List[AuditResult] = Field(
        default_factory=list,
        description="Lista de resultados de auditoría."
    )
    
    total_requirements: int = Field(
        default=0,
        description="Total de requisitos evaluados."
    )
    
    compliant_count: int = Field(
        default=0,
        description="Cantidad de requisitos cumplidos."
    )
    
    non_compliant_count: int = Field(
        default=0,
        description="Cantidad de incumplimientos."
    )
    
    showstoppers: List[AuditResult] = Field(
        default_factory=list,
        description="Lista de requisitos obligatorios no cumplidos (Kill Criteria)."
    )
    
    overall_status: ComplianceStatus = Field(
        default=ComplianceStatus.MISSING_INFO,
        description="Estado general de la propuesta."
    )
    
    def calculate_stats(self):
        """Calcula estadísticas del batch."""
        self.total_requirements = len(self.results)
        self.compliant_count = sum(
            1 for r in self.results if r.status == ComplianceStatus.COMPLIANT
        )
        self.non_compliant_count = sum(
            1 for r in self.results if r.status == ComplianceStatus.NON_COMPLIANT
        )
        self.showstoppers = [
            r for r in self.results 
            if r.severity_detected == SeverityLevel.MANDATORY 
            and r.status == ComplianceStatus.NON_COMPLIANT
        ]
        
        # Overall status
        if self.showstoppers:
            self.overall_status = ComplianceStatus.NON_COMPLIANT
        elif self.non_compliant_count > 0:
            self.overall_status = ComplianceStatus.PARTIAL
        elif self.compliant_count == self.total_requirements:
            self.overall_status = ComplianceStatus.COMPLIANT
        else:
            self.overall_status = ComplianceStatus.PARTIAL


# Custom Exceptions

class ComplianceValidatorError(Exception):
    """Excepción base para errores del validador."""
    pass


class LLMServiceError(ComplianceValidatorError):
    """Error al comunicarse con el servicio LLM."""
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        self.original_error = original_error
        super().__init__(f"Error en servicio LLM: {message}")


class InsufficientContextError(ComplianceValidatorError):
    """El contexto proporcionado es insuficiente para evaluar."""
    def __init__(self, requirement: str):
        self.requirement = requirement
        super().__init__(
            f"Contexto insuficiente para evaluar: '{requirement[:50]}...'"
        )


class ParseResponseError(ComplianceValidatorError):
    """Error al parsear la respuesta del LLM."""
    def __init__(self, raw_response: str):
        self.raw_response = raw_response
        super().__init__(
            f"No se pudo parsear la respuesta del LLM: {raw_response[:100]}..."
        )
