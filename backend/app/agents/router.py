"""
Router de dominio para clasificación de preguntas.

Clasifica preguntas en el dominio más específico usando el LLM.
Migrado desde subagents.py — fuente canónica de prompts: specialist_prompts.py.
"""

from langchain_core.messages import HumanMessage

from app.core.config import settings
from app.core.logging import AgentLogger
from app.services import get_llm
from app.agents.prompts import ROUTER_PROMPT, AVAILABLE_DOMAINS

logger = AgentLogger("router")


async def route_question(question: str) -> str:
    """Clasifica la pregunta en un dominio específico."""
    logger.node_enter("router", {"question": question})

    try:
        llm = get_llm(temperature=settings.router_temperature)
        prompt = ROUTER_PROMPT.format(question=question)
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        domain = response.content.strip().lower()

        if domain not in AVAILABLE_DOMAINS:
            domain = "general"

        logger.node_exit("router", f"dominio: {domain}")
        return domain
    except Exception as e:
        logger.error("router", e)
        return "general"
