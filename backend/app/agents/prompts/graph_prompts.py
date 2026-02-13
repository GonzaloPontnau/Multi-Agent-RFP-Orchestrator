"""
Prompts utilizados por los nodos de infraestructura del grafo (grader, refiner).
"""

GRADER_PROMPT_BATCH = """Eres un evaluador de relevancia documental. Tu tarea es determinar si cada documento
contiene información relevante para responder la pregunta del usuario.

REGLAS CRÍTICAS DE RELEVANCIA:
1. SIEMPRE marca como "relevant" documentos que contengan:
   - TABLAS (cronogramas, presupuestos, requisitos tabulados)
   - FECHAS específicas (DD/MM/AAAA, plazos, cronogramas)
   - MONTOS FINANCIEROS (USD, ARS, porcentajes de garantía)
   - PORCENTAJES (% de participación, SLAs, penalidades)
   - LISTAS NUMERADAS de requisitos o especificaciones

2. Estos documentos son relevantes INCLUSO si tienen poco texto narrativo.
   Un documento con solo una tabla de fechas ES RELEVANTE para preguntas de cronograma.

3. Evalúa el CONTENIDO ESTRUCTURADO (tablas, listas) con el mismo peso que el texto.

A continuación se presentan {doc_count} documentos numerados. Evalúa CADA uno.

{documents_block}

Pregunta:
{question}

Responde con una línea por documento, EXACTAMENTE en este formato (sin texto extra):
1:relevant
2:not_relevant
3:relevant
..."""

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
