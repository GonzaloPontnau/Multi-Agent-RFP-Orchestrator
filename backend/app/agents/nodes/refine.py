"""Nodo de refinamiento de respuesta."""

from langchain_core.messages import HumanMessage

from app.agents.prompts import REFINE_PROMPT
from app.agents.state import AgentState, get_docs
from app.core.config import settings
from app.core.logging import AgentLogger
from app.services import get_llm

logger = AgentLogger("rfp_graph")


async def refine_node(state: AgentState) -> dict:
    """Mejora una respuesta que no paso la auditoria."""
    domain = state.get("domain", "general")
    current_revision = state.get("revision_count", 0) + 1
    logger.node_enter("refine", state)
    logger.debug("refine", f"Revision #{current_revision} - Improving answer using {domain.upper()} specialist prompt")

    try:
        docs = get_docs(state)
        context_text = "\n\n---\n\n".join(doc.page_content for doc in docs)
        llm = get_llm(temperature=settings.refine_temperature)
        prompt = REFINE_PROMPT.format(
            domain=domain,
            context=context_text,
            question=state["question"],
            previous_answer=state["answer"],
        )
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        refined_answer = response.content
        logger.node_exit("refine", f"Revision #{current_revision} complete - {len(refined_answer)} chars")
        logger.routing_decision(
            "refine",
            "auditor",
            f"Refined answer ready - re-checking quality (revision {current_revision})",
        )
        return {"answer": refined_answer, "revision_count": current_revision}
    except Exception as e:
        logger.error("refine", e)
        return {"revision_count": current_revision}
