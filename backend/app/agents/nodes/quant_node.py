"""Nodo de analisis cuantitativo."""

from app.agents.state import AgentState, get_docs
from app.core.logging import AgentLogger

logger = AgentLogger("rfp_graph")


async def quant_node(state: AgentState) -> dict:
    """Ejecuta QuanT cuando el dominio clasificado es quantitative."""
    domain = state.get("domain", "general")
    if domain != "quantitative":
        logger.debug("quant", f"Skipping QuanT - domain is {domain}")
        return {}

    logger.node_enter("quant", state)
    try:
        from app.agents.quant import quant_analyze

        docs = get_docs(state)
        chart_b64, chart_type, insights, data_quality = await quant_analyze(state["question"], docs)
        logger.node_exit("quant", f"chart_type={chart_type}, quality={data_quality}")
        logger.routing_decision("quant", "risk_sentinel", "Quantitative analysis complete - sending to risk audit")
        return {
            "quant_chart": chart_b64,
            "quant_chart_type": chart_type,
            "quant_insights": insights,
            "quant_data_quality": data_quality,
            "answer": insights,
        }
    except Exception as e:
        logger.error("quant", e)
        return {
            "quant_chart": None,
            "quant_chart_type": "none",
            "quant_insights": "Error al procesar analisis cuantitativo.",
            "quant_data_quality": "incomplete",
            "answer": "Error al procesar analisis cuantitativo.",
        }
