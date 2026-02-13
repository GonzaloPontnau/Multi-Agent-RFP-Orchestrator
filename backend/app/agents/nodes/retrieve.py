"""Nodo de recuperacion de contexto."""

from app.agents.state import AgentState, NO_DOCUMENTS_MESSAGE
from app.core.config import settings
from app.core.logging import AgentLogger
from app.services import get_rag_service

logger = AgentLogger("rfp_graph")


async def retrieve_node(state: AgentState) -> dict:
    """Recupera documentos relevantes del vector store."""
    logger.pipeline_start(state["question"], state.get("trace_id"))
    logger.node_enter("retrieve", state)
    logger.routing_decision("START", "retrieve", "Initial node - fetching documents from vector store")

    try:
        rag = get_rag_service()
        documents = await rag.similarity_search(state["question"], k=settings.retrieval_k)

        if not documents:
            logger.node_exit("retrieve", "NO DOCUMENTS - Vector store is empty")
            logger.routing_decision("retrieve", "END", "No documents found - returning predefined message")
            return {
                "context": [],
                "filtered_context": [],
                "revision_count": 0,
                "domain": "none",
                "answer": NO_DOCUMENTS_MESSAGE,
                "audit_result": "pass",
                "no_documents": True,
            }

        logger.node_exit("retrieve", f"{len(documents)} docs retrieved from vector store")
        logger.routing_decision(
            "retrieve",
            "grade_documents",
            f"Passing {len(documents)} docs for relevance filtering",
        )
        return {"context": documents, "revision_count": 0}
    except Exception as e:
        logger.error("retrieve", e)
        return {"context": [], "revision_count": 0}
