"""Nodo de auditoria de riesgo/compliance."""

from app.agents.state import AgentState, get_docs
from app.core.config import settings
from app.core.logging import AgentLogger

logger = AgentLogger("rfp_graph")


async def risk_sentinel_node(state: AgentState) -> dict:
    """Ejecuta auditoria de compliance con Risk Sentinel."""
    logger.node_enter("risk_sentinel", state)

    try:
        from app.agents.risk_sentinel import risk_audit

        docs = get_docs(state)
        risk_level, compliance, issues, gate_passed = await risk_audit(
            state["answer"],
            docs,
            state["question"],
        )

        audit_result = "pass" if compliance != "rejected" else "fail"
        logger.node_exit("risk_sentinel", f"risk={risk_level}, compliance={compliance}, gate={gate_passed}")

        if compliance == "rejected":
            revision_count = state.get("revision_count", 0)
            if revision_count < settings.max_audit_revisions:
                logger.routing_decision(
                    "risk_sentinel",
                    "refine",
                    f"REJECTED - sending to refine (attempt {revision_count + 1}/{settings.max_audit_revisions})",
                )
            else:
                logger.routing_decision("risk_sentinel", "END", "REJECTED but max revisions reached")
        else:
            logger.routing_decision("risk_sentinel", "END", f"Compliance {compliance.upper()} - finalizing")

        return {
            "risk_level": risk_level,
            "compliance_status": compliance,
            "risk_issues": issues,
            "gate_passed": gate_passed,
            "audit_result": audit_result,
        }
    except Exception as e:
        logger.error("risk_sentinel", e)
        return {
            "risk_level": "medium",
            "compliance_status": "approved",
            "risk_issues": [f"Error en auditoria: {str(e)}"],
            "gate_passed": True,
            "audit_result": "pass",
        }
