"""Construccion de respuestas API desde el estado del grafo."""

from app.schemas import AgentMetadata, QuantAnalysis, QueryResponse, RiskAssessment


def build_query_response(result: dict) -> QueryResponse:
    """Convierte el resultado del grafo en QueryResponse tipado."""
    context_docs = result.get("context", [])
    filtered_docs = result.get("filtered_context") or context_docs
    sources = list({doc.metadata.get("source", "") for doc in filtered_docs if doc.metadata.get("source")})

    quant_analysis = None
    if result.get("quant_chart") or result.get("quant_insights"):
        quant_analysis = QuantAnalysis(
            chart_base64=result.get("quant_chart"),
            chart_type=result.get("quant_chart_type"),
            insights=result.get("quant_insights", ""),
            data_quality=result.get("quant_data_quality", "incomplete"),
        )

    risk_assessment = None
    if result.get("risk_level"):
        risk_assessment = RiskAssessment(
            risk_level=result.get("risk_level", "medium"),
            compliance_status=result.get("compliance_status", "pending"),
            issues=result.get("risk_issues", []),
            gate_passed=result.get("gate_passed", True),
        )

    domain = result.get("domain", "general")
    specialist_name = "quant" if domain == "quantitative" else f"specialist_{domain}"
    metadata = AgentMetadata(
        domain=domain,
        specialist_used=specialist_name,
        documents_retrieved=len(context_docs),
        documents_filtered=len(filtered_docs),
        revision_count=result.get("revision_count", 0),
        audit_result=result.get("audit_result", "N/A"),
        quant_analysis=quant_analysis,
        risk_assessment=risk_assessment,
    )

    return QueryResponse(answer=result["answer"], sources=sources, agent_metadata=metadata)
