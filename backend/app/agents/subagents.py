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

ROUTER_PROMPT = """Eres un clasificador de preguntas sobre licitaciones. Tu tarea es determinar qué dominio 
es más relevante para responder la pregunta del usuario.

DOMINIOS DISPONIBLES:
- legal: Normativa, jurisdicción, propiedad intelectual, confidencialidad, protección de datos, contratos, sanciones
- technical: Arquitectura, stack tecnológico, integraciones, módulos, APIs, infraestructura, data center, seguridad técnica
- financial: Presupuesto, montos, pagos, hitos financieros, garantías monetarias, fuentes de financiamiento, ajustes
- timeline: Cronograma, fechas, plazos, fases, hitos temporales, duración del contrato
- requirements: Requisitos de participación, capacidad técnica, experiencia, personal clave, inhabilidades
- quantitative: Análisis numérico, comparaciones de montos, tendencias, estadísticas, gráficos, visualizaciones de datos
- general: Preguntas generales que no encajan en categorías específicas o abarcan múltiples dominios

CRITERIO PARA QUANTITATIVE:
Usa "quantitative" cuando la pregunta pida explícitamente:
- Comparar números/montos entre sí
- Ver tendencias o evolución de datos
- Generar gráficos o visualizaciones
- Análisis estadístico de datos del documento

Pregunta: {question}

Responde SOLO con el nombre del dominio (una palabra, sin explicación): """

# Prompts especializados por dominio
SPECIALIST_PROMPTS = {
    "legal": """Eres un experto en aspectos LEGALES y NORMATIVOS de licitaciones públicas.
Tu especialidad incluye:
- Marco legal y normativo aplicable
- Jurisdicción y resolución de controversias
- Propiedad intelectual y licencias
- Confidencialidad y protección de datos (Ley 25.326, GDPR)
- Penalidades y sanciones
- Obligaciones contractuales

INSTRUCCIONES:
- Cita artículos, leyes y normativas específicas cuando estén disponibles
- Destaca plazos legales importantes
- Indica claramente las obligaciones y consecuencias de incumplimiento
- Si mencionas montos de multas o penalidades, resáltalos en **negrita**""",

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
- Cronograma del proceso licitatorio (fechas clave)
- Duración del contrato y fases
- Hitos de implementación
- Plazos de entrega y milestones
- Ventanas de mantenimiento
- Períodos de impugnación y resolución

INSTRUCCIONES:
- Presenta las fechas en orden cronológico
- Calcula duraciones entre hitos cuando sea útil
- Destaca fechas límite críticas en **negrita**
- Menciona consecuencias de incumplimiento de plazos""",

    "requirements": """Eres un experto en REQUISITOS DE PARTICIPACIÓN para licitaciones.
Tu especialidad incluye:
- Capacidad jurídica (tipos de oferentes permitidos)
- Capacidad técnica (experiencia general y específica)
- Personal clave requerido (roles, certificaciones, experiencia)
- Capacidad financiera (patrimonio, liquidez, facturación)
- Inhabilidades y restricciones
- Documentación requerida

INSTRUCCIONES:
- Lista requisitos de forma clara y estructurada
- Indica cantidades y umbrales específicos
- Diferencia entre requisitos obligatorios y deseables
- Presenta el personal clave en formato de tabla cuando sea apropiado""",

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
        return "Ocurrió un error procesando tu pregunta. Intenta nuevamente."
