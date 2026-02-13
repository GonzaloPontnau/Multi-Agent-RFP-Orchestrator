"""Nodos de grading y enrutamiento de dominio."""

import asyncio

from langchain_core.messages import HumanMessage

from app.agents.prompts import GRADER_PROMPT_BATCH
from app.agents.router import route_question
from app.agents.state import AgentState
from app.core.config import settings
from app.core.logging import AgentLogger
from app.services import get_llm

logger = AgentLogger("rfp_graph")


def _detect_data_heavy_question(question: str) -> bool:
    """Heuristica para detectar preguntas que requieren datos tabulares o numericos."""
    data_heavy_keywords = [
        "fecha",
        "cronograma",
        "plazo",
        "calendario",
        "hito",
        "presupuesto",
        "monto",
        "garantia",
        "pago",
        "financier",
        "tabla",
        "porcentaje",
        "%",
        "usd",
        "ars",
        "cantidad",
        "cuanto",
        "cuando",
        "timeline",
        "schedule",
    ]
    question_lower = question.lower()
    return any(kw in question_lower for kw in data_heavy_keywords)


async def _grade_documents_node(state: AgentState) -> dict:
    """Filtra documentos evaluando su relevancia en un solo llamado LLM."""
    logger.node_enter("grade_documents", state)

    try:
        llm = get_llm(temperature=settings.grader_temperature)
        total_docs = len(state["context"])
        original_docs = state["context"]

        doc_blocks = []
        for i, doc in enumerate(original_docs, 1):
            doc_blocks.append(f"[Documento {i}]\n{doc.page_content[:settings.grader_doc_truncation]}")

        documents_block = "\n\n---\n\n".join(doc_blocks)
        prompt = GRADER_PROMPT_BATCH.format(
            doc_count=total_docs,
            documents_block=documents_block,
            question=state["question"],
        )

        response = await llm.ainvoke([HumanMessage(content=prompt)])
        grades_text = response.content.strip().lower()

        relevant_docs = []
        for line in grades_text.split("\n"):
            line = line.strip()
            if not line or ":" not in line:
                continue
            parts = line.split(":", 1)
            try:
                doc_idx = int(parts[0].strip()) - 1
                grade = parts[1].strip()
                is_relevant = "relevant" in grade and "not_relevant" not in grade
                if 0 <= doc_idx < total_docs:
                    if is_relevant:
                        relevant_docs.append(original_docs[doc_idx])
                    logger.debug("grade_documents", f"Doc {doc_idx + 1}/{total_docs} -> {grade}")
            except (ValueError, IndexError):
                continue

        is_data_heavy = _detect_data_heavy_question(state["question"])
        if len(relevant_docs) < settings.safety_net_min_docs and is_data_heavy:
            logger.debug(
                "grade_documents",
                f"SAFETY NET: Only {len(relevant_docs)} docs after filter, "
                f"using top {settings.safety_net_fallback_docs}.",
            )
            relevant_docs = original_docs[: settings.safety_net_fallback_docs]
        elif not relevant_docs:
            logger.debug(
                "grade_documents",
                f"No relevant docs found, using top {settings.safety_net_fallback_docs} as fallback",
            )
            relevant_docs = original_docs[: settings.safety_net_fallback_docs]

        logger.node_exit(
            "grade_documents",
            f"{len(relevant_docs)}/{total_docs} docs marked as relevant (batch graded)",
        )
        logger.routing_decision(
            "grade_documents",
            "router",
            f"Sending {len(relevant_docs)} relevant docs to router for domain classification",
        )
        return {"filtered_context": relevant_docs}
    except Exception as e:
        logger.error("grade_documents", e)
        return {"filtered_context": state["context"][: settings.safety_net_fallback_docs]}


async def grade_and_route_node(state: AgentState) -> dict:
    """Ejecuta grading y routing en paralelo para reducir latencia."""
    logger.node_enter("grade_and_route", state)

    async def _grade():
        return await _grade_documents_node(state)

    async def _route():
        try:
            domain = await route_question(state["question"])
            logger.specialist_selected(domain, state["question"])
            logger.routing_decision("router", f"specialist_{domain}", f"Question classified as {domain.upper()}")
            return {"domain": domain}
        except Exception as e:
            logger.error("router", e)
            return {"domain": "general"}

    grade_result, route_result = await asyncio.gather(_grade(), _route())
    merged = {**grade_result, **route_result}
    logger.node_exit("grade_and_route", f"domain={merged.get('domain')}, docs={len(merged.get('filtered_context', []))}")
    return merged
