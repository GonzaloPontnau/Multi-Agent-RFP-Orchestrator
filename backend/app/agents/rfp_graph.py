"""Wiring del grafo LangGraph para el pipeline RFP."""

from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.agents.nodes import (
    grade_and_route_node,
    quant_node,
    refine_node,
    retrieve_node,
    risk_sentinel_node,
    specialist_node,
)
from app.agents.state import AgentState
from app.core.config import settings


def route_after_retrieve(state: AgentState) -> Literal["grade_and_route", "end"]:
    """Si no hay documentos, terminar; de lo contrario continuar el flujo."""
    if state.get("no_documents"):
        return "end"
    return "grade_and_route"


def route_after_router(state: AgentState) -> Literal["specialist", "quant"]:
    """Selecciona ruta de ejecucion por dominio."""
    if state.get("domain", "general") == "quantitative":
        return "quant"
    return "specialist"


def should_continue_after_audit(state: AgentState) -> Literal["refine", "end"]:
    """Determina si se requiere refinamiento adicional."""
    revision_count = state.get("revision_count", 0)
    audit_result = state.get("audit_result", "pass")
    if audit_result == "fail" and revision_count < settings.max_audit_revisions:
        return "refine"
    return "end"


workflow = StateGraph(AgentState)
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("grade_and_route", grade_and_route_node)
workflow.add_node("specialist", specialist_node)
workflow.add_node("quant", quant_node)
workflow.add_node("risk_sentinel", risk_sentinel_node)
workflow.add_node("refine", refine_node)

workflow.add_edge(START, "retrieve")
workflow.add_conditional_edges(
    "retrieve",
    route_after_retrieve,
    {
        "grade_and_route": "grade_and_route",
        "end": END,
    },
)
workflow.add_conditional_edges(
    "grade_and_route",
    route_after_router,
    {
        "specialist": "specialist",
        "quant": "quant",
    },
)
workflow.add_edge("specialist", "risk_sentinel")
workflow.add_edge("quant", "risk_sentinel")
workflow.add_conditional_edges(
    "risk_sentinel",
    should_continue_after_audit,
    {
        "refine": "refine",
        "end": END,
    },
)
workflow.add_edge("refine", "risk_sentinel")

app = workflow.compile()
