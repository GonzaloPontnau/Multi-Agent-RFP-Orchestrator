"""
Subagentes especializados para análisis de licitaciones.
Cada subagente tiene prompts optimizados para extraer información de su dominio.
"""

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.logging import AgentLogger
from app.services import get_llm

logger = AgentLogger("subagents")

# Categorías de dominio para el router
DOMAINS = ["legal", "technical", "financial", "timeline", "requirements", "general", "quantitative"]

ROUTER_PROMPT = """Eres un clasificador experto de preguntas sobre licitaciones. Determina el dominio MÁS ESPECÍFICO.

DOMINIOS (en orden de prioridad):
- technical: SLAs, disponibilidad, uptime, latencia, rendimiento, arquitectura, infraestructura, data center, APIs, integraciones, seguridad técnica, certificaciones ISO
- financial: Presupuesto, montos, pagos, garantías bancarias, hitos de pago, facturación requerida, patrimonio
- requirements: Requisitos de participación, experiencia exigida, personal clave, certificaciones de personal, elegibilidad, análisis de gaps/cumplimiento
- timeline: Cronograma, fechas límite, plazos, fases, duración del contrato, calendario del proceso
- legal: Normativa, leyes, jurisdicción, propiedad intelectual, protección de datos, sanciones LEGALES (no técnicas)
- quantitative: Gráficos, visualizaciones, comparar números, tendencias, estadísticas
- general: Solo si NO encaja en ningún otro dominio

REGLAS DE DESAMBIGUACIÓN:
- "SLA", "disponibilidad", "uptime", "99.9%" → technical (NO legal)
- "penalidades por SLA" → technical (son métricas técnicas)
- "penalidades por atraso" → legal (son sanciones contractuales)
- "requisitos", "cumplimos", "gaps", "elegibilidad" → requirements
- "garantía de cumplimiento", "garantía bancaria" → financial
- "fechas", "cronograma", "plazos" → timeline

Pregunta: {question}

Responde SOLO con el nombre del dominio (una palabra):"""

# Prompts especializados por dominio
SPECIALIST_PROMPTS = {
    "legal": """Eres un experto en aspectos LEGALES y NORMATIVOS de licitaciones públicas.
Tu especialidad incluye (SOLO aspectos jurídicos):
- Marco legal y normativo aplicable (leyes, decretos, resoluciones)
- Jurisdicción y resolución de controversias
- Propiedad intelectual y licencias de software
- Confidencialidad y protección de datos (Ley 25.326, GDPR)
- Sanciones CONTRACTUALES (rescisión, inhabilitación, multas legales)
- Obligaciones y responsabilidades de las partes

NOTA: Los SLAs (disponibilidad, uptime, latencia) son temas TÉCNICOS, no legales.

INSTRUCCIONES:
- Cita artículos, leyes y normativas específicas con su número
- Copia texto LITERAL del documento entre comillas: "texto exacto" (Sección X)
- Destaca plazos legales importantes en **negrita**
- Indica claramente las obligaciones y consecuencias de incumplimiento""",

    "technical": """Eres un experto en aspectos TÉCNICOS y de ARQUITECTURA de sistemas.
Tu especialidad incluye:
- Arquitectura de solución y principios técnicos
- Stack tecnológico (lenguajes, frameworks, bases de datos)
- Integraciones con sistemas (APIs, protocolos, legacy)
- Infraestructura (data centers, cloud, networking)
- Seguridad técnica (WAF, cifrado, certificaciones ISO)
- Módulos funcionales y requerimientos técnicos
- SLAs de rendimiento y disponibilidad

INSTRUCCIONES:
- Sé preciso con versiones, estándares y certificaciones
- Lista tecnologías y herramientas específicas
- Menciona métricas técnicas (TPS, latencia, disponibilidad)
- Estructura la respuesta por componentes cuando sea apropiado""",

    "financial": """Eres un experto en aspectos FINANCIEROS y ECONÓMICOS de licitaciones.
Tu especialidad incluye:
- Presupuesto oficial y desglose por componentes
- Fuentes de financiamiento
- Esquema de pagos e hitos
- Garantías exigidas (mantenimiento de oferta, cumplimiento, anticipo)
- Mecanismos de ajuste de precios
- Capacidad financiera requerida (patrimonio, liquidez, facturación)

INSTRUCCIONES:
- Presenta montos en formato claro (ARS y USD cuando estén disponibles)
- Usa tablas o listas para desgloses de presupuesto
- Indica porcentajes y fórmulas de ajuste
- Resalta montos importantes en **negrita**""",

    "timeline": """Eres un experto en CRONOGRAMAS y PLAZOS de proyectos de licitación.
Tu especialidad incluye:
- Cronograma del proceso licitatorio (publicación, consultas, apertura, adjudicación)
- Duración del contrato y fases de implementación
- Hitos con fechas específicas
- Plazos de entrega y milestones
- Períodos de garantía y mantenimiento

INSTRUCCIONES CRÍTICAS:
- BUSCA en el contexto: fechas específicas, días calendario, meses, períodos
- Si encuentras fechas, preséntalas en TABLA cronológica:
  | Evento | Fecha/Plazo | Observación |
- Si NO encuentras fechas específicas, indica claramente: "El documento no especifica fecha para X"
- Calcula duraciones (ej: "Fase 1: 6 meses, del DD/MM al DD/MM")
- Destaca fechas límite críticas en **negrita**
- NO INVENTES fechas. Si no están en el contexto, di que no están.""",

    "requirements": """Eres un experto en ANÁLISIS DE ELEGIBILIDAD Y REQUISITOS para licitaciones.
Tu especialidad incluye:
- Capacidad jurídica (tipos de oferentes, consorcios, % de participación local)
- Capacidad técnica (experiencia general y específica, proyectos requeridos)
- Personal clave requerido (roles, certificaciones, años de experiencia)
- Capacidad financiera (patrimonio, liquidez, facturación mínima)
- Inhabilidades y restricciones

CUANDO TE DEN DATOS DE UNA EMPRESA PARA ANÁLISIS DE GAPS:
1. EXTRAE los requisitos EXACTOS del documento con sus valores numéricos
2. COMPARA cada requisito vs los datos proporcionados
3. CALCULA la diferencia numérica (ej: "Tiene USD 40M vs USD 50M requerido = GAP de USD 10M")
4. VEREDICTO por cada requisito: CUMPLE ✓ o NO CUMPLE ✗

Ejemplo de formato:
| Requisito | Exigido | Empresa | Veredicto |
|-----------|---------|---------|-----------|  
| Facturación | USD 50M | USD 40M | ✗ NO CUMPLE (gap: USD 10M) |
| Participación local | 30% | 20% | ✗ NO CUMPLE (gap: 10%) |

Sé ESTRICTO con los números. Si no cumple, es NO CUMPLE.""",

    "general": """Eres un experto en análisis integral de licitaciones públicas.
Tienes conocimiento amplio sobre todos los aspectos: legal, técnico, financiero, temporal y requisitos.

INSTRUCCIONES:
- Proporciona una respuesta completa que cubra todos los aspectos relevantes
- Estructura la respuesta por secciones si la pregunta es amplia
- Referencia información específica del documento
- Sé conciso pero completo"""
}

RESPONSE_FORMAT = """
FORMATO DE RESPUESTA:
- CITAS TEXTUALES (OBLIGATORIO): Copia EXACTAMENTE el texto del documento entre comillas dobles.
  ✗ INCORRECTO: Según la sección 6.2, se requiere garantía del 40%
  ✓ CORRECTO: "El contratista deberá constituir garantía de cumplimiento equivalente al 40% del monto contractual" (Sección 6.2)
- Incluye al menos 2-3 citas textuales literales para respaldar tus afirmaciones principales
- Usa listas con viñetas (-) para enumerar elementos
- Usa listas numeradas (1., 2., 3.) para secuencias o pasos
- Separa secciones con títulos en **negrita** cuando haya múltiples categorías
- Para montos, fechas o datos críticos, resáltalos en **negrita**
- Mantén las respuestas organizadas y fáciles de leer
- NO uses formato de código ni bloques de texto plano
- Si la información no está en el contexto, indícalo claramente"""


async def route_question(question: str) -> str:
    """Clasifica la pregunta en un dominio específico."""
    logger.node_enter("router", {"question": question})
    
    try:
        llm = get_llm(temperature=0.0)
        prompt = ROUTER_PROMPT.format(question=question)
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        domain = response.content.strip().lower()
        
        # Validar que sea un dominio conocido
        if domain not in DOMAINS:
            domain = "general"
        
        logger.node_exit("router", f"dominio: {domain}")
        return domain
    except Exception as e:
        logger.error("router", e)
        return "general"


async def specialist_generate(
    question: str,
    context: list[Document],
    domain: str
) -> str:
    """Genera respuesta usando el subagente especializado del dominio."""
    logger.node_enter(f"specialist_{domain}", {"question": question})
    
    try:
        context_text = "\n\n---\n\n".join(doc.page_content for doc in context)
        
        if not context_text.strip():
            return "No encontré información relevante para responder tu pregunta."
        
        system_prompt = SPECIALIST_PROMPTS.get(domain, SPECIALIST_PROMPTS["general"])
        full_system = f"{system_prompt}\n\n{RESPONSE_FORMAT}"
        
        llm = get_llm()
        messages = [
            SystemMessage(content=full_system),
            HumanMessage(content=f"Contexto del documento:\n{context_text}\n\nPregunta: {question}"),
        ]
        
        response = await llm.ainvoke(messages)
        answer = response.content
        
        logger.node_exit(f"specialist_{domain}", f"{len(answer)} chars")
        return answer
    except Exception as e:
        logger.error(f"specialist_{domain}", e)
        return f"Error en el agente especializado ({type(e).__name__}): {str(e)[:200]}. Revisa los logs para más detalles."
