from typing import Literal, TypedDict

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from app.core.logging import AgentLogger
from app.services import get_llm, get_rag_service
from app.agents.subagents import route_question, specialist_generate, DOMAINS

logger = AgentLogger("rfp_graph")

# Prompts para nodos de soporte (grader, auditor, refine)
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
4. Es coherente con el dominio de especialización asignado

Dominio del especialista: {domain}

Contexto disponible:
{context}

Pregunta:
{question}

Respuesta generada:
{answer}

Responde SOLO "pass" si la respuesta es adecuada, o "fail" si necesita mejora (sin explicación adicional)."""

REFINE_PROMPT = """Eres un experto en licitaciones especializado en el dominio: {domain}.
La respuesta anterior fue insuficiente. Revisa CUIDADOSAMENTE todo el contexto.

Busca específicamente según tu dominio:
- legal: normativas, artículos, obligaciones, sanciones
- technical: tecnologías, arquitectura, integraciones, SLAs técnicos
- financial: montos, porcentajes, garantías, pagos
- timeline: fechas, plazos, cronogramas, hitos
- requirements: requisitos, experiencia, personal, capacidades

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
    domain: str  # Dominio clasificado por el router
    answer: str
    audit_result: str
    revision_count: int
    # Campos para QuanT (Analista Cuantitativo)
    quant_chart: str | None
    quant_chart_type: str | None
    quant_insights: str | None
    quant_data_quality: str | None
    # Campos para Risk Sentinel (Auditor de Compliance)
    risk_level: str | None
    compliance_status: str | None
    risk_issues: list[str]
    gate_passed: bool | None
    # Flag para indicar que no hay documentos cargados
    no_documents: bool | None


def _get_docs(state: AgentState) -> list[Document]:
    """Obtiene documentos del estado priorizando filtered_context."""
    return state.get("filtered_context") or state.get("context", [])


NO_DOCUMENTS_MESSAGE = """No hay documentos cargados en el sistema.

Para poder responder tu pregunta, por favor:

1. **Sube uno o más documentos PDF** usando el área de carga en la interfaz
2. Espera a que se procesen los documentos
3. Vuelve a hacer tu pregunta

Una vez que hayas cargado los documentos de licitación, podré analizar y responder preguntas específicas sobre su contenido."""


async def retrieve_node(state: AgentState) -> dict:
    """Recupera documentos relevantes del vector store."""
    # Log inicio del pipeline completo
    logger.pipeline_start(state["question"])
    logger.node_enter("retrieve", state)
    logger.routing_decision("START", "retrieve", "Initial node - fetching documents from vector store")
    
    try:
        rag = get_rag_service()
        documents = await rag.similarity_search(state["question"], k=10)
        
        # Si no hay documentos, devolver mensaje predeterminado
        if not documents:
            logger.node_exit("retrieve", "NO DOCUMENTS - Vector store is empty")
            logger.routing_decision("retrieve", "END", "No documents found - returning predefined message")
            return {
                "context": [],
                "filtered_context": [],
                "revision_count": 0,
                "domain": "none",
                "answer": NO_DOCUMENTS_MESSAGE,
                "audit_result": "pass",  # Skip auditing
                "no_documents": True,  # Flag to skip remaining nodes
            }
        
        logger.node_exit("retrieve", f"{len(documents)} docs retrieved from Pinecone")
        logger.routing_decision("retrieve", "grade_documents", f"Passing {len(documents)} docs for relevance filtering")
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
        total_docs = len(state["context"])
        
        for i, doc in enumerate(state["context"], 1):
            prompt = GRADER_PROMPT.format(
                document=doc.page_content[:1500],
                question=state["question"]
            )
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            grade = response.content.strip().lower()
            
            is_relevant = "relevant" in grade and "not_relevant" not in grade
            if is_relevant:
                relevant_docs.append(doc)
            logger.debug("grade_documents", f"Doc {i}/{total_docs} (score: {doc.metadata.get('score', 'N/A')}) -> {grade}")
        
        # Si no hay docs relevantes, usar todos los originales como fallback
        if not relevant_docs:
            logger.debug("grade_documents", "No relevant docs found, using top 5 as fallback")
            relevant_docs = state["context"][:5]
        
        logger.node_exit("grade_documents", f"{len(relevant_docs)}/{total_docs} docs marked as relevant")
        logger.routing_decision("grade_documents", "router", f"Sending {len(relevant_docs)} relevant docs to router for domain classification")
        return {"filtered_context": relevant_docs}
    except Exception as e:
        logger.error("grade_documents", e)
        return {"filtered_context": state["context"][:5]}


async def router_node(state: AgentState) -> dict:
    """Clasifica la pregunta y la dirige al subagente especializado apropiado."""
    logger.node_enter("router", state)
    
    try:
        domain = await route_question(state["question"])
        logger.specialist_selected(domain, state["question"])
        logger.node_exit("router", f"classified as '{domain}' domain")
        logger.routing_decision("router", f"specialist_{domain}", f"Question classified as {domain.upper()} - routing to specialized subagent")
        return {"domain": domain}
    except Exception as e:
        logger.error("router", e)
        logger.routing_decision("router", "specialist_general", "Error in classification - defaulting to general specialist")
        return {"domain": "general"}


async def specialist_node(state: AgentState) -> dict:
    """Genera respuesta usando el subagente especializado según el dominio clasificado."""
    domain = state.get("domain", "general")
    logger.node_enter(f"specialist_{domain}", state)
    
    try:
        docs = _get_docs(state)
        logger.debug(f"specialist_{domain}", f"Using {len(docs)} docs with specialized {domain.upper()} prompt")
        
        answer = await specialist_generate(
            question=state["question"],
            context=docs,
            domain=domain
        )
        
        logger.node_exit(f"specialist_{domain}", f"Generated {len(answer)} chars response")
        logger.routing_decision(f"specialist_{domain}", "auditor", "Response generated - sending to auditor for quality check")
        return {"answer": answer}
    except Exception as e:
        logger.error(f"specialist_{domain}", e)
        return {"answer": f"Error en el agente ({type(e).__name__}): {str(e)[:200]}"}


async def auditor_node(state: AgentState) -> dict:
    """Verifica la calidad de la respuesta generada."""
    logger.node_enter("auditor", state)
    
    try:
        docs = _get_docs(state)
        context_text = "\n\n".join(doc.page_content for doc in docs)
        domain = state.get("domain", "general")
        revision_count = state.get("revision_count", 0)
        
        llm = get_llm(temperature=0.0)
        prompt = AUDITOR_PROMPT.format(
            domain=domain,
            context=context_text[:4000],
            question=state["question"],
            answer=state["answer"]
        )
        
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        result = response.content.strip().lower()
        
        audit_result = "pass" if "pass" in result else "fail"
        logger.node_exit("auditor", f"Quality check: {audit_result.upper()} (domain: {domain}, revision: {revision_count})")
        
        # Log routing decision based on audit result
        if audit_result == "pass":
            logger.routing_decision("auditor", "END", "Quality PASSED - finalizing response")
        elif revision_count < 2:
            logger.routing_decision("auditor", "refine", f"Quality FAILED - sending to refine (attempt {revision_count + 1}/2)")
        else:
            logger.routing_decision("auditor", "END", "Quality FAILED but max revisions reached - finalizing anyway")
        
        return {"audit_result": audit_result}
    except Exception as e:
        logger.error("auditor", e)
        return {"audit_result": "pass"}


async def refine_node(state: AgentState) -> dict:
    """Mejora una respuesta que no pasó la auditoría, usando contexto del dominio."""
    domain = state.get("domain", "general")
    current_revision = state.get("revision_count", 0) + 1
    logger.node_enter("refine", state)
    logger.debug("refine", f"Revision #{current_revision} - Improving answer using {domain.upper()} specialist prompt")
    
    try:
        docs = _get_docs(state)
        context_text = "\n\n---\n\n".join(doc.page_content for doc in docs)
        
        llm = get_llm(temperature=0.1)
        prompt = REFINE_PROMPT.format(
            domain=domain,
            context=context_text,
            question=state["question"],
            previous_answer=state["answer"]
        )
        
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        refined_answer = response.content
        
        logger.node_exit("refine", f"Revision #{current_revision} complete - {len(refined_answer)} chars")
        logger.routing_decision("refine", "auditor", f"Refined answer ready - re-checking quality (revision {current_revision})")
        return {"answer": refined_answer, "revision_count": current_revision}
    except Exception as e:
        logger.error("refine", e)
        return {"revision_count": current_revision}


async def quant_node(state: AgentState) -> dict:
    """Nodo para análisis cuantitativo con QuanT."""
    domain = state.get("domain", "general")
    
    # Solo ejecutar si el dominio es quantitative
    if domain != "quantitative":
        logger.debug("quant", f"Skipping QuanT - domain is {domain}")
        return {}
    
    logger.node_enter("quant", state)
    
    try:
        from app.agents.quant import quant_analyze
        
        docs = _get_docs(state)
        chart_b64, chart_type, insights, data_quality = await quant_analyze(
            state["question"],
            docs
        )
        
        logger.node_exit("quant", f"chart_type={chart_type}, quality={data_quality}")
        logger.routing_decision("quant", "risk_sentinel", "Quantitative analysis complete - sending to risk audit")
        
        return {
            "quant_chart": chart_b64,
            "quant_chart_type": chart_type,
            "quant_insights": insights,
            "quant_data_quality": data_quality,
            "answer": insights,  # El insight es la respuesta para dominio quantitative
        }
    except Exception as e:
        logger.error("quant", e)
        return {
            "quant_chart": None,
            "quant_chart_type": "none",
            "quant_insights": "Error al procesar análisis cuantitativo.",
            "quant_data_quality": "incomplete",
            "answer": "Error al procesar análisis cuantitativo.",
        }


async def risk_sentinel_node(state: AgentState) -> dict:
    """Nodo de auditoría avanzada con Risk Sentinel."""
    logger.node_enter("risk_sentinel", state)
    
    try:
        from app.agents.risk_sentinel import risk_audit
        
        docs = _get_docs(state)
        risk_level, compliance, issues, gate_passed = await risk_audit(
            state["answer"],
            docs,
            state["question"]
        )
        
        # Determinar audit_result basado en compliance
        audit_result = "pass" if compliance != "rejected" else "fail"
        
        logger.node_exit(
            "risk_sentinel",
            f"risk={risk_level}, compliance={compliance}, gate={gate_passed}"
        )
        
        # Log routing decision
        if compliance == "rejected":
            revision_count = state.get("revision_count", 0)
            if revision_count < 2:
                logger.routing_decision("risk_sentinel", "refine", f"REJECTED - sending to refine (attempt {revision_count + 1}/2)")
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
            "risk_issues": [f"Error en auditoría: {str(e)}"],
            "gate_passed": True,
            "audit_result": "pass",
        }


def route_after_router(state: AgentState) -> Literal["specialist", "quant"]:
    """Decide si usar el especialista normal o QuanT según el dominio."""
    domain = state.get("domain", "general")
    if domain == "quantitative":
        return "quant"
    return "specialist"


def should_continue_after_audit(state: AgentState) -> Literal["refine", "end"]:
    """Decide si refinar la respuesta o terminar."""
    revision_count = state.get("revision_count", 0)
    audit_result = state.get("audit_result", "pass")
    
    if audit_result == "fail" and revision_count < 2:
        return "refine"
    return "end"


# Construcción del grafo multi-agente con subagentes especializados
workflow = StateGraph(AgentState)

# Nodos del pipeline
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("grade_documents", grade_documents_node)
workflow.add_node("router", router_node)
workflow.add_node("specialist", specialist_node)
workflow.add_node("quant", quant_node)  # QuanT: Analista Cuantitativo
workflow.add_node("risk_sentinel", risk_sentinel_node)  # Risk Sentinel: Auditor de Compliance
workflow.add_node("auditor", auditor_node)  # Auditor simple (fallback)
workflow.add_node("refine", refine_node)

def route_after_retrieve(state: AgentState) -> Literal["grade_documents", "end"]:
    """Si no hay documentos, ir directo a END. Si hay, continuar con grade_documents."""
    if state.get("no_documents"):
        return "end"
    return "grade_documents"


# Flujo principal
workflow.add_edge(START, "retrieve")
workflow.add_conditional_edges(
    "retrieve",
    route_after_retrieve,
    {
        "grade_documents": "grade_documents",
        "end": END,
    }
)
workflow.add_edge("grade_documents", "router")

# Router dirige condicionalmente a specialist o quant
workflow.add_conditional_edges(
    "router",
    route_after_router,
    {
        "specialist": "specialist",
        "quant": "quant",
    }
)

# Tanto specialist como quant van a risk_sentinel
workflow.add_edge("specialist", "risk_sentinel")
workflow.add_edge("quant", "risk_sentinel")

# Risk Sentinel decide si aprobar o refinar
workflow.add_conditional_edges(
    "risk_sentinel",
    should_continue_after_audit,
    {
        "refine": "refine",
        "end": END,
    }
)

# Refine vuelve a risk_sentinel para re-evaluación
workflow.add_edge("refine", "risk_sentinel")

app = workflow.compile()
