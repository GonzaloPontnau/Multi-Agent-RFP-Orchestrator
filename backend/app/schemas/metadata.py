from typing import Literal

from pydantic import BaseModel, Field


class QuantAnalysis(BaseModel):
    """Output del subagente QuanT - Analista Cuantitativo."""
    chart_base64: str | None = Field(default=None, description="Grafico en formato base64")
    chart_type: str | None = Field(default=None, description="Tipo de grafico: bar, line, pie, table, none")
    insights: str = Field(description="Analisis textual de los datos")
    data_quality: str = Field(description="Estado de calidad de datos: clean/sanitized/incomplete")


class RiskAssessment(BaseModel):
    """Output del subagente Risk Sentinel - Auditor de Compliance."""
    risk_level: Literal["low", "medium", "high", "critical"] = Field(description="Nivel de riesgo detectado")
    compliance_status: Literal["approved", "pending", "rejected"] = Field(description="Estado de compliance")
    issues: list[str] = Field(default_factory=list, description="Lista de problemas detectados")
    gate_passed: bool = Field(description="Si paso el gate de revision actual")


class AgentMetadata(BaseModel):
    """Metadata sobre el flujo de agentes para trazabilidad."""
    domain: str = Field(description="Dominio clasificado por el router")
    specialist_used: str = Field(description="Nombre del subagente especializado que genero la respuesta")
    documents_retrieved: int = Field(description="Cantidad de documentos recuperados del vector store")
    documents_filtered: int = Field(description="Cantidad de documentos filtrados como relevantes")
    revision_count: int = Field(description="Numero de revisiones realizadas por el loop de refinamiento")
    audit_result: str = Field(description="Resultado de la auditoria de calidad (pass/fail)")
    quant_analysis: QuantAnalysis | None = Field(default=None, description="Analisis cuantitativo si aplica")
    risk_assessment: RiskAssessment | None = Field(default=None, description="Evaluacion de riesgo y compliance")
