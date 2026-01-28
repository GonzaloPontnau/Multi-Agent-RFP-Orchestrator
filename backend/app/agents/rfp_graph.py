from typing import Literal, TypedDict

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from app.core.logging import AgentLogger
from app.services import get_llm, get_rag_service

logger = AgentLogger("rfp_graph")

# Prompts especializados para cada agente
SYSTEM_PROMPT = """Eres un experto en licitaciones. Responde solo con la información provista.
Si la información no está en el contexto, indica que no tienes datos suficientes para responder."""

GRADER_PROMPT = """Eres un evaluador de relevancia documental. Tu tarea es determinar si un documento
contiene información relevante para responder la pregunta del usuario.

Responde SOLO con "relevant" o "not_relevant" (sin comillas, sin explicación adicional).

Documento:
{document}

Pregunta:
{question}

Evaluación:"""

AUDITOR_PROMPT = """Eres un auditor de calidad de respuestas para licitaciones. Evalúa si la respuesta:
1. Responde directamente la pregunta
2. Contiene información específica (números, fechas, listas concretas)
3. NO dice "no tengo datos" si hay información relevante en el contexto

Contexto disponible:
{context}

Pregunta:
{question}

Respuesta generada:
{answer}

Responde SOLO "pass" si la respuesta es adecuada, o "fail" si necesita mejora (sin explicación adicional)."""

REFINE_PROMPT = """Eres un experto en licitaciones. La respuesta anterior fue insuficiente.
Revisa CUIDADOSAMENTE todo el contexto y extrae la información relevante.

Busca específicamente:
- Números, montos, porcentajes
- Fechas y plazos
- Listas y enumeraciones
- Condiciones y requisitos

Contexto completo:
{context}

Pregunta del usuario:
{question}

Respuesta anterior (insuficiente):
{previous_answer}

Genera una respuesta mejorada basada ÚNICAMENTE en el contexto. Si realmente no hay información, indícalo."""


class AgentState(TypedDict):
    question: str
    context: list[Document]
    filtered_context: list[Document]
    answer: str
    audit_result: str
    revision_count: int


async def retrieve_node(state: AgentState) -> dict:
    """Recupera documentos relevantes del vector store."""
    logger.node_enter("retrieve", state)
    
    try:
        rag = get_rag_service()
        documents = await rag.similarity_search(state["question"], k=10)
        logger.node_exit("retrieve", f"{len(documents)} docs encontrados")
        return {"context": documents, "revision_count": 0}
    except Exception as e:
        logger.error("retrieve", e)
        return {"context": [], "revision_count": 0}


async def grade_documents_node(state: AgentState) -> dict:
    """Filtra documentos evaluando su relevancia para la pregunta."""
    logger.node_enter("grade_documents", state)
    
    try:
        llm = get_llm(temperature=0.0)
        relevant_docs = []
        
        for doc in state["context"]:
            prompt = GRADER_PROMPT.format(
                document=doc.page_content[:1500],
                question=state["question"]
            )
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            grade = response.content.strip().lower()
            
            if "relevant" in grade and "not_relevant" not in grade:
                relevant_docs.append(doc)
                logger.debug("grade_documents", f"Doc relevante (score: {doc.metadata.get('score', 'N/A')})")
        
        # Si no hay docs relevantes, usar todos los originales como fallback
        if not relevant_docs:
            logger.debug("grade_documents", "Sin docs relevantes, usando originales")
            relevant_docs = state["context"][:5]
        
        logger.node_exit("grade_documents", f"{len(relevant_docs)} docs filtrados")
        return {"filtered_context": relevant_docs}
    except Exception as e:
        logger.error("grade_documents", e)
        return {"filtered_context": state["context"][:5]}


async def generate_node(state: AgentState) -> dict:
    """Genera respuesta basada en el contexto filtrado."""
    logger.node_enter("generate", state)
    
    try:
        docs = state.get("filtered_context") or state.get("context", [])
        context_text = "\n\n---\n\n".join(doc.page_content for doc in docs)
        
        if not context_text.strip():
            answer = "No encontré información relevante para responder tu pregunta."
            logger.node_exit("generate", "sin contexto")
            return {"answer": answer}
        
        llm = get_llm()
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"Contexto:\n{context_text}\n\nPregunta: {state['question']}"),
        ]
        
        response = await llm.ainvoke(messages)
        answer = response.content
        
        logger.node_exit("generate", f"{len(answer)} chars")
        return {"answer": answer}
    except Exception as e:
        logger.error("generate", e)
        return {"answer": "Ocurrió un error procesando tu pregunta. Intenta nuevamente."}


async def auditor_node(state: AgentState) -> dict:
    """Verifica la calidad de la respuesta generada."""
    logger.node_enter("auditor", state)
    
    try:
        docs = state.get("filtered_context") or state.get("context", [])
        context_text = "\n\n".join(doc.page_content for doc in docs)
        
        llm = get_llm(temperature=0.0)
        prompt = AUDITOR_PROMPT.format(
            context=context_text[:4000],
            question=state["question"],
            answer=state["answer"]
        )
        
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        result = response.content.strip().lower()
        
        audit_result = "pass" if "pass" in result else "fail"
        logger.node_exit("auditor", f"resultado: {audit_result}")
        return {"audit_result": audit_result}
    except Exception as e:
        logger.error("auditor", e)
        return {"audit_result": "pass"}


async def refine_node(state: AgentState) -> dict:
    """Mejora una respuesta que no pasó la auditoría."""
    logger.node_enter("refine", state)
    
    try:
        docs = state.get("filtered_context") or state.get("context", [])
        context_text = "\n\n---\n\n".join(doc.page_content for doc in docs)
        
        llm = get_llm(temperature=0.1)
        prompt = REFINE_PROMPT.format(
            context=context_text,
            question=state["question"],
            previous_answer=state["answer"]
        )
        
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        refined_answer = response.content
        
        new_count = state.get("revision_count", 0) + 1
        logger.node_exit("refine", f"revisión #{new_count}")
        return {"answer": refined_answer, "revision_count": new_count}
    except Exception as e:
        logger.error("refine", e)
        return {"revision_count": state.get("revision_count", 0) + 1}


def should_continue_after_audit(state: AgentState) -> Literal["refine", "end"]:
    """Decide si refinar la respuesta o terminar."""
    revision_count = state.get("revision_count", 0)
    audit_result = state.get("audit_result", "pass")
    
    if audit_result == "fail" and revision_count < 2:
        return "refine"
    return "end"


# Construcción del grafo multi-agente
workflow = StateGraph(AgentState)

workflow.add_node("retrieve", retrieve_node)
workflow.add_node("grade_documents", grade_documents_node)
workflow.add_node("generate", generate_node)
workflow.add_node("auditor", auditor_node)
workflow.add_node("refine", refine_node)

workflow.add_edge(START, "retrieve")
workflow.add_edge("retrieve", "grade_documents")
workflow.add_edge("grade_documents", "generate")
workflow.add_edge("generate", "auditor")

workflow.add_conditional_edges(
    "auditor",
    should_continue_after_audit,
    {
        "refine": "refine",
        "end": END,
    }
)

workflow.add_edge("refine", "auditor")

app = workflow.compile()
