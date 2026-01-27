from typing import TypedDict

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from app.core.logging import AgentLogger
from app.services import get_llm, get_rag_service

logger = AgentLogger("rfp_graph")

SYSTEM_PROMPT = """Eres un experto en licitaciones. Responde solo con la información provista.
Si la información no está en el contexto, indica que no tienes datos suficientes para responder."""


class AgentState(TypedDict):
    question: str
    context: list[Document]
    answer: str


async def retrieve_node(state: AgentState) -> dict:
    """Recupera documentos relevantes del vector store."""
    logger.node_enter("retrieve", state)
    
    rag = get_rag_service()
    documents = await rag.similarity_search(state["question"])
    
    logger.node_exit("retrieve", f"{len(documents)} docs encontrados")
    return {"context": documents}


async def generate_node(state: AgentState) -> dict:
    """Genera respuesta basada en el contexto recuperado."""
    logger.node_enter("generate", state)
    
    context_text = "\n\n".join(doc.page_content for doc in state["context"])
    
    llm = get_llm()
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Contexto:\n{context_text}\n\nPregunta: {state['question']}"),
    ]
    
    response = await llm.ainvoke(messages)
    answer = response.content
    
    logger.node_exit("generate", f"{len(answer)} chars")
    return {"answer": answer}


# Construcción del grafo
workflow = StateGraph(AgentState)

workflow.add_node("retrieve", retrieve_node)
workflow.add_node("generate", generate_node)

workflow.add_edge(START, "retrieve")
workflow.add_edge("retrieve", "generate")
workflow.add_edge("generate", END)

# Grafo compilado listo para invocar
app = workflow.compile()
