"""Nodo de generacion por especialista."""

from app.agents.state import AgentState, get_docs
from app.core.exceptions import AgentProcessingError
from app.core.logging import AgentLogger
from app.services import get_container

logger = AgentLogger("rfp_graph")


async def specialist_node(state: AgentState) -> dict:
    """Genera respuesta usando el subagente especializado segun dominio."""
    domain = state.get("domain", "general")
    if domain == "quantitative":
        logger.debug("specialist_quantitative", "Quantitative routed to specialist - using general fallback")
        domain = "general"

    logger.node_enter(f"specialist_{domain}", state)
    try:
        docs = get_docs(state)
        logger.debug(f"specialist_{domain}", f"Using {len(docs)} docs with specialized {domain.upper()} prompt")
        container = get_container()
        agent = container.agent_factory.create(domain)
        answer = await agent.generate(question=state["question"], context=docs)
        logger.node_exit(f"specialist_{domain}", f"Generated {len(answer)} chars response")
        logger.routing_decision(f"specialist_{domain}", "auditor", "Response generated - sending to auditor for quality check")
        return {"answer": answer}
    except AgentProcessingError as e:
        logger.error(f"specialist_{domain}", e)
        return {"answer": f"Error en el agente especializado: {str(e)[:300]}"}
    except Exception as e:
        logger.error(f"specialist_{domain}", e)
        return {"answer": f"Error en el agente ({type(e).__name__}): {str(e)[:200]}"}
