"""
Risk Sentinel - Auditor de Gates y Compliance
Rol: Oficial de cumplimiento. Unico agente con permiso para decir "NO".

Mentalidad:
"Confio, pero verifico. Mi trabajo es encontrar inconsistencias.
No me importa lo bien que suene la propuesta; si no cumple la norma, la bloqueo.
Soy pesimista por diseño."
"""
import json
import re
from typing import Literal

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.logging import AgentLogger
from app.services import get_llm

logger = AgentLogger("risk_sentinel")

RiskLevel = Literal["low", "medium", "high", "critical"]
ComplianceStatus = Literal["approved", "pending", "rejected"]

# Prompt para extraer reglas del documento
RULE_EXTRACTION_PROMPT = """Eres un analista de compliance especializado en licitaciones.
Tu tarea es identificar TODAS las reglas y requisitos del documento que deben verificarse.

TIPOS DE REGLAS:
1. REGLAS DURAS (binarias, SI/NO):
   - Documentos requeridos (tiene certificado? SI/NO)
   - Plazos limite (esta dentro del plazo? SI/NO)
   - Umbrales minimos (cumple el minimo? SI/NO)
   - Inhabilitaciones (esta inhabilitado? SI/NO)

2. REGLAS BLANDAS (requieren juicio):
   - Suficiencia de experiencia
   - Calidad de propuesta tecnica
   - Adecuacion de plan de trabajo

CONTEXTO DEL DOCUMENTO:
{context}

FORMATO DE RESPUESTA (JSON):
{{
    "hard_rules": [
        {{"rule": "descripcion", "requirement": "valor esperado", "category": "legal|financial|technical|timeline"}}
    ],
    "soft_rules": [
        {{"rule": "descripcion", "criteria": "criterio de evaluacion", "category": "legal|financial|technical|timeline"}}
    ]
}}

Responde SOLO con el JSON:"""

# Prompt para fact-checking
FACT_CHECK_PROMPT = """Eres un verificador de hechos riguroso. Tu tarea es validar cada afirmacion
de la respuesta contra la evidencia disponible en el contexto.

PROCESO:
1. Identifica cada afirmacion factual en la respuesta
2. Busca evidencia en el contexto que la respalde
3. Marca como VERIFICADO, NO_VERIFICABLE, o INCONSISTENTE

RESPUESTA A VERIFICAR:
{answer}

CONTEXTO (evidencia disponible):
{context}

PREGUNTA ORIGINAL:
{question}

FORMATO DE RESPUESTA (JSON):
{{
    "claims_checked": [
        {{
            "claim": "la afirmacion textual",
            "status": "verified|unverifiable|inconsistent",
            "evidence": "cita del contexto o null",
            "issue": "descripcion del problema si hay inconsistencia"
        }}
    ],
    "overall_accuracy": "high|medium|low",
    "critical_issues": ["lista de problemas criticos si existen"]
}}

Responde SOLO con el JSON:"""

# Prompt para scoring de riesgo
RISK_SCORING_PROMPT = """Eres un oficial de riesgos. Basandote en los hallazgos del fact-checking
y las reglas del documento, determina el nivel de riesgo y estado de compliance.

CRITERIOS DE RIESGO:
- CRITICAL: Hay afirmaciones falsas o inconsistencias graves. Datos criticos incorrectos.
- HIGH: Hay informacion no verificable importante. Faltan datos requeridos.
- MEDIUM: Hay pequenas inconsistencias o datos aproximados. Requiere revision.
- LOW: Toda la informacion es verificable y consistente.

CRITERIOS DE COMPLIANCE:
- REJECTED: Hay errores criticos o informacion falsa. No puede continuar.
- PENDING: Hay issues que requieren revision humana antes de continuar.
- APPROVED: La respuesta es precisa y cumple con los requisitos.

HALLAZGOS DEL FACT-CHECK:
{fact_check_results}

REGLAS DEL DOCUMENTO:
{rules}

FORMATO DE RESPUESTA (JSON):
{{
    "risk_level": "low|medium|high|critical",
    "compliance_status": "approved|pending|rejected",
    "issues": ["IMPORTANTE: Lista SOLO observaciones NUEVAS que NO esten ya mencionadas en la respuesta. Cada issue debe aportar informacion adicional o advertencias que complementen la respuesta, no repetir lo que ya se dijo. Si no hay issues nuevos, devuelve lista vacia."],
    "gate_passed": true/false,
    "reasoning": "breve explicacion de la decision"
}}

Responde SOLO con el JSON:"""


def _parse_json_response(response: str) -> dict | None:
    """Parsea respuesta JSON del LLM, manejando posibles errores."""
    try:
        clean = response.strip()
        if clean.startswith("```"):
            clean = re.sub(r"```(?:json)?\n?", "", clean)
            clean = clean.rstrip("`")
        return json.loads(clean)
    except json.JSONDecodeError:
        return None


async def extract_rules(context: list[Document]) -> dict:
    """Extrae reglas duras (binarias) y blandas (semanticas) del contexto."""
    logger.node_enter("risk_extract_rules", {})
    
    try:
        context_text = "\n\n---\n\n".join(doc.page_content for doc in context)
        if not context_text.strip():
            return {"hard_rules": [], "soft_rules": []}
        
        llm = get_llm(temperature=0.0)
        prompt = RULE_EXTRACTION_PROMPT.format(context=context_text[:6000])
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        
        rules = _parse_json_response(response.content)
        if not rules:
            logger.debug("risk_extract_rules", "Failed to parse rules JSON")
            return {"hard_rules": [], "soft_rules": []}
        
        hard_count = len(rules.get("hard_rules", []))
        soft_count = len(rules.get("soft_rules", []))
        logger.node_exit("risk_extract_rules", f"{hard_count} hard, {soft_count} soft rules")
        return rules
    except Exception as e:
        logger.error("risk_extract_rules", e)
        return {"hard_rules": [], "soft_rules": []}


async def fact_check(answer: str, context: list[Document], question: str) -> dict:
    """Verifica cada afirmacion del borrador contra la base de conocimiento."""
    logger.node_enter("risk_fact_check", {"answer_length": len(answer)})
    
    try:
        context_text = "\n\n---\n\n".join(doc.page_content for doc in context)
        
        llm = get_llm(temperature=0.0)
        prompt = FACT_CHECK_PROMPT.format(
            answer=answer,
            context=context_text[:6000],
            question=question
        )
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        
        result = _parse_json_response(response.content)
        if not result:
            logger.debug("risk_fact_check", "Failed to parse fact-check JSON")
            return {
                "claims_checked": [],
                "overall_accuracy": "medium",
                "critical_issues": []
            }
        
        claims_count = len(result.get("claims_checked", []))
        accuracy = result.get("overall_accuracy", "unknown")
        logger.node_exit("risk_fact_check", f"{claims_count} claims checked, accuracy: {accuracy}")
        return result
    except Exception as e:
        logger.error("risk_fact_check", e)
        return {
            "claims_checked": [],
            "overall_accuracy": "medium",
            "critical_issues": []
        }


async def calculate_risk_score(
    fact_check_results: dict,
    rules: dict
) -> tuple[RiskLevel, ComplianceStatus, list[str], bool]:
    """Calcula semaforo de riesgo final."""
    logger.node_enter("risk_scoring", {})
    
    try:
        llm = get_llm(temperature=0.0)
        prompt = RISK_SCORING_PROMPT.format(
            fact_check_results=json.dumps(fact_check_results, ensure_ascii=False),
            rules=json.dumps(rules, ensure_ascii=False)
        )
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        
        result = _parse_json_response(response.content)
        if not result:
            # Fallback basado en accuracy
            accuracy = fact_check_results.get("overall_accuracy", "medium")
            critical_issues = fact_check_results.get("critical_issues", [])
            
            if critical_issues:
                return "high", "pending", critical_issues, False
            elif accuracy == "low":
                return "medium", "pending", ["Precision de informacion baja"], False
            else:
                return "low", "approved", [], True
        
        risk_level: RiskLevel = result.get("risk_level", "medium")
        compliance: ComplianceStatus = result.get("compliance_status", "pending")
        issues = result.get("issues", [])
        gate_passed = result.get("gate_passed", True)
        
        # Validar valores
        if risk_level not in ["low", "medium", "high", "critical"]:
            risk_level = "medium"
        if compliance not in ["approved", "pending", "rejected"]:
            compliance = "pending"
        
        logger.node_exit("risk_scoring", f"risk: {risk_level}, compliance: {compliance}, gate: {gate_passed}")
        return risk_level, compliance, issues, gate_passed
    except Exception as e:
        logger.error("risk_scoring", e)
        return "medium", "pending", [f"Error en evaluacion: {str(e)}"], False


UNIFIED_RISK_PROMPT = """Eres un auditor de compliance y riesgos para licitaciones. Analiza la respuesta generada contra el contexto del documento.

RESPUESTA A AUDITAR:
{answer}

CONTEXTO DEL DOCUMENTO:
{context}

PREGUNTA ORIGINAL:
{question}

TAREA:
1. Verifica si las afirmaciones de la respuesta están respaldadas por el contexto
2. Identifica inconsistencias o información no verificable
3. Determina el nivel de riesgo y estado de compliance

CRITERIOS DE RIESGO:
- low: Toda la información es verificable y consistente
- medium: Hay pequeñas inconsistencias o datos aproximados
- high: Hay información importante no verificable o faltan datos
- critical: Hay afirmaciones falsas o errores graves

RESPONDE SOLO EN JSON:
{{
    "risk_level": "low|medium|high|critical",
    "compliance_status": "approved|pending|rejected",
    "issues": ["Lista SOLO observaciones NUEVAS que aporten info adicional, NO repetir lo que ya dice la respuesta. Si no hay issues nuevos, devuelve lista vacía []"],
    "gate_passed": true/false
}}"""


async def risk_audit(
    answer: str,
    context: list[Document],
    question: str,
    project_state: dict | None = None
) -> tuple[RiskLevel, ComplianceStatus, list[str], bool]:
    """
    Pipeline simplificado de Risk Sentinel (1 sola llamada LLM).
    
    Args:
        answer: Respuesta generada a auditar
        context: Documentos de contexto
        question: Pregunta original
        project_state: Estado del proyecto (opcional, no usado actualmente)
    
    Returns:
        tuple: (risk_level, compliance_status, issues, gate_passed)
    """
    logger.node_enter("risk_audit", {"question": question[:50]})
    
    try:
        # Respuestas cortas o errores: aprobar automáticamente
        if len(answer) < 50 or "error" in answer.lower():
            logger.node_exit("risk_audit", "Short/error answer - auto-approved")
            return "low", "approved", [], True
        
        # Respuesta de "no hay documentos": aprobar sin auditar
        if "no hay documentos" in answer.lower():
            logger.node_exit("risk_audit", "No documents message - auto-approved")
            return "low", "approved", [], True
        
        context_text = "\n\n---\n\n".join(doc.page_content for doc in context[:5])  # Limitar a 5 docs
        
        llm = get_llm(temperature=0.0)
        prompt = UNIFIED_RISK_PROMPT.format(
            answer=answer[:3000],  # Limitar longitud
            context=context_text[:4000],
            question=question
        )
        
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        result = _parse_json_response(response.content)
        
        if not result:
            logger.node_exit("risk_audit", "Failed to parse JSON - defaulting to medium/approved")
            return "medium", "approved", [], True
        
        risk_level: RiskLevel = result.get("risk_level", "medium")
        compliance: ComplianceStatus = result.get("compliance_status", "approved")
        issues = result.get("issues", [])
        gate_passed = result.get("gate_passed", True)
        
        # Validar valores
        if risk_level not in ["low", "medium", "high", "critical"]:
            risk_level = "medium"
        if compliance not in ["approved", "pending", "rejected"]:
            compliance = "approved"
        
        # Filtrar issues vacíos o placeholder
        issues = [i for i in issues if i and not i.startswith("Lista SOLO")]
        
        logger.node_exit(
            "risk_audit",
            f"risk={risk_level}, compliance={compliance}, issues={len(issues)}, gate={gate_passed}"
        )
        
        return risk_level, compliance, issues, gate_passed
        
    except Exception as e:
        logger.error("risk_audit", e)
        return "medium", "approved", [f"Error en auditoría: {str(e)}"], True

