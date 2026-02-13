"""
Estado del grafo multi-agente (AgentState) y utilidades relacionadas.
"""

from typing import TypedDict
from uuid import uuid4

from langchain_core.documents import Document


class AgentState(TypedDict):
    question: str
    context: list[Document]
    filtered_context: list[Document]
    domain: str
    answer: str
    audit_result: str
    revision_count: int
    # Campos para QuanT (Analista Cuantitativo)
    quant_chart: str | None
    quant_chart_type: str | None
    quant_insights: str | None
    quant_data_quality: str | None
    # Campos para Risk Sentinel (Auditor de Compliance)
    risk_level: str | None
    compliance_status: str | None
    risk_issues: list[str]
    gate_passed: bool | None
    # Flag para indicar que no hay documentos cargados
    no_documents: bool | None
    # Identificador de trazabilidad por request
    trace_id: str | None


def get_docs(state: AgentState) -> list[Document]:
    """Obtiene documentos del estado priorizando filtered_context."""
    return state.get("filtered_context") or state.get("context", [])


def create_initial_state(question: str) -> dict:
    """Crea el estado inicial para invocar el grafo RFP."""
    trace_id = uuid4().hex[:8]
    return {
        "trace_id": trace_id,
        "question": question,
        "context": [],
        "filtered_context": [],
        "domain": "",
        "answer": "",
        "audit_result": "",
        "revision_count": 0,
        "quant_chart": None,
        "quant_chart_type": None,
        "quant_insights": None,
        "quant_data_quality": None,
        "risk_level": None,
        "compliance_status": None,
        "risk_issues": [],
        "gate_passed": None,
        "no_documents": None,
    }


NO_DOCUMENTS_MESSAGE = """No hay documentos cargados en el sistema.

Para poder responder tu pregunta, por favor:

1. **Sube uno o más documentos PDF** usando el área de carga en la interfaz
2. Espera a que se procesen los documentos
3. Vuelve a hacer tu pregunta

Una vez que hayas cargado los documentos de licitación, podré analizar y responder preguntas específicas sobre su contenido."""
