"""
QuanT - Analista Cuantitativo
Rol: Cerebro matematico y visual. Garantiza que ningun numero sea una alucinacion
y que los datos cuenten una historia visual.

Mentalidad:
"No soy un escritor, soy un calculador. No adivino tendencias, las computo.
Si los datos estan sucios, los limpio antes de usarlos.
Mi salida es siempre evidencia visual o numerica verificada."
"""
import base64
import io
import json
import re
from typing import Literal

import matplotlib
matplotlib.use('Agg')  # Backend sin GUI para servidores
import matplotlib.pyplot as plt
import numpy as np

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.logging import AgentLogger
from app.services import get_llm

logger = AgentLogger("quant")

ChartType = Literal["bar", "line", "pie", "table", "none"]

# Prompt para extraer datos numericos del contexto
EXTRACTION_PROMPT = """Eres un extractor de datos numericos especializado en documentos de licitaciones.
Tu tarea es identificar y extraer TODOS los datos numericos relevantes del contexto para responder la pregunta.

INSTRUCCIONES:
1. Busca montos, porcentajes, cantidades, fechas con valores, metricas
2. Identifica las categorias o etiquetas asociadas a cada numero
3. Detecta si hay series temporales o comparaciones
4. Indica si los datos estan completos o hay valores faltantes

FORMATO DE RESPUESTA (JSON estricto):
{{
    "data_found": true/false,
    "data_type": "comparison" | "timeline" | "distribution" | "single_value" | "table",
    "categories": ["categoria1", "categoria2", ...],
    "values": [valor1, valor2, ...],
    "unit": "USD" | "ARS" | "%" | "dias" | "unidades" | "otro",
    "data_quality": "clean" | "sanitized" | "incomplete",
    "notes": "observaciones sobre los datos"
}}

Si NO hay datos numericos relevantes, responde:
{{
    "data_found": false,
    "data_type": "none",
    "categories": [],
    "values": [],
    "unit": "",
    "data_quality": "incomplete",
    "notes": "No se encontraron datos numericos relevantes para la pregunta"
}}

Contexto del documento:
{context}

Pregunta del usuario:
{question}

Responde SOLO con el JSON, sin texto adicional:"""

# Prompt para decidir estrategia visual
STRATEGY_PROMPT = """Eres un experto en visualizacion de datos. Basandote en el tipo de datos,
decide la mejor forma de visualizarlos.

REGLAS:
- Comparar volumenes/cantidades -> "bar" (grafico de barras)
- Evolucion temporal/tendencias -> "line" (grafico de lineas)
- Distribucion/porcentajes de un todo -> "pie" (grafico circular)
- Datos tabulares complejos -> "table" (tabla formateada)
- Valor unico o datos insuficientes -> "none" (solo texto)

Datos extraidos:
{data}

Pregunta del usuario:
{question}

Responde SOLO con una palabra: bar, line, pie, table, o none"""

# Prompt para generar insight
INSIGHT_PROMPT = """Eres QuanT, un analista cuantitativo experto. Genera un insight claro y conciso
basado en los datos y la visualizacion.

INSTRUCCIONES:
- Comienza con el hallazgo principal (ej: "El presupuesto total es de...")
- Menciona comparaciones o tendencias si existen
- Destaca valores criticos en **negrita**
- Si hay anomalias o datos faltantes, mencionalo
- Se preciso: usa los numeros exactos del contexto

Tipo de grafico generado: {chart_type}
Datos analizados: {data}
Pregunta original: {question}

Genera el insight (2-4 oraciones):"""


def _parse_json_response(response: str) -> dict | None:
    """Parsea respuesta JSON del LLM, manejando posibles errores."""
    try:
        # Limpiar posibles marcadores de codigo
        clean = response.strip()
        if clean.startswith("```"):
            clean = re.sub(r"```(?:json)?\n?", "", clean)
            clean = clean.rstrip("`")
        return json.loads(clean)
    except json.JSONDecodeError:
        return None


async def extract_numerical_data(context: list[Document], question: str) -> dict:
    """Extrae y sanitiza datos numericos del contexto."""
    logger.node_enter("quant_extract", {"question": question})
    
    try:
        context_text = "\n\n---\n\n".join(doc.page_content for doc in context)
        if not context_text.strip():
            logger.node_exit("quant_extract", "No context available")
            return {"data_found": False, "data_type": "none", "categories": [], 
                    "values": [], "unit": "", "data_quality": "incomplete",
                    "notes": "Sin contexto disponible"}
        
        llm = get_llm(temperature=0.0)
        prompt = EXTRACTION_PROMPT.format(context=context_text[:6000], question=question)
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        
        data = _parse_json_response(response.content)
        if not data:
            logger.debug("quant_extract", "Failed to parse JSON, returning empty data")
            return {"data_found": False, "data_type": "none", "categories": [], 
                    "values": [], "unit": "", "data_quality": "incomplete",
                    "notes": "Error parsing data extraction response"}
        
        logger.node_exit("quant_extract", f"Found {len(data.get('values', []))} values, type: {data.get('data_type')}")
        return data
    except Exception as e:
        logger.error("quant_extract", e)
        return {"data_found": False, "data_type": "none", "categories": [], 
                "values": [], "unit": "", "data_quality": "incomplete",
                "notes": f"Error: {str(e)}"}


async def select_chart_strategy(data: dict, question: str) -> ChartType:
    """Decide el tipo de visualizacion optimo."""
    logger.node_enter("quant_strategy", {"data_type": data.get("data_type")})
    
    # Si no hay datos, no hay grafico
    if not data.get("data_found") or not data.get("values"):
        logger.node_exit("quant_strategy", "none (no data)")
        return "none"
    
    try:
        llm = get_llm(temperature=0.0)
        prompt = STRATEGY_PROMPT.format(data=json.dumps(data, ensure_ascii=False), question=question)
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        
        chart_type = response.content.strip().lower()
        valid_types: list[ChartType] = ["bar", "line", "pie", "table", "none"]
        
        if chart_type not in valid_types:
            # Fallback basado en tipo de datos
            data_type = data.get("data_type", "")
            if data_type == "comparison":
                chart_type = "bar"
            elif data_type == "timeline":
                chart_type = "line"
            elif data_type == "distribution":
                chart_type = "pie"
            else:
                chart_type = "bar"  # Default
        
        logger.node_exit("quant_strategy", chart_type)
        return chart_type
    except Exception as e:
        logger.error("quant_strategy", e)
        return "none"


def generate_chart(data: dict, chart_type: ChartType, max_retries: int = 2) -> str | None:
    """Genera grafico y retorna base64. Incluye loop de auto-correccion."""
    if chart_type == "none" or chart_type == "table":
        return None
    
    logger.node_enter("quant_chart", {"chart_type": chart_type})
    
    categories = data.get("categories", [])
    values = data.get("values", [])
    unit = data.get("unit", "")
    
    # Validar datos minimos
    if not categories or not values or len(categories) != len(values):
        logger.debug("quant_chart", "Invalid data dimensions, skipping chart")
        return None
    
    # Convertir valores a numeros
    try:
        numeric_values = [float(str(v).replace(",", "").replace(".", "").replace(" ", "")) 
                         if isinstance(v, str) else float(v) for v in values]
    except (ValueError, TypeError):
        logger.debug("quant_chart", "Could not convert values to numeric")
        return None
    
    for attempt in range(max_retries):
        try:
            plt.figure(figsize=(10, 6))
            plt.style.use('seaborn-v0_8-darkgrid')
            
            if chart_type == "bar":
                colors = plt.cm.viridis(np.linspace(0.3, 0.9, len(categories)))
                bars = plt.bar(categories, numeric_values, color=colors, edgecolor='white', linewidth=1.2)
                plt.ylabel(unit if unit else "Valor")
                # Agregar valores sobre las barras
                for bar, val in zip(bars, numeric_values):
                    plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(numeric_values)*0.01,
                            f'{val:,.0f}', ha='center', va='bottom', fontsize=9)
                            
            elif chart_type == "line":
                plt.plot(categories, numeric_values, marker='o', linewidth=2, markersize=8, 
                        color='#2E86AB', markerfacecolor='white', markeredgewidth=2)
                plt.ylabel(unit if unit else "Valor")
                plt.fill_between(categories, numeric_values, alpha=0.1, color='#2E86AB')
                
            elif chart_type == "pie":
                colors = plt.cm.Set3(np.linspace(0, 1, len(categories)))
                plt.pie(numeric_values, labels=categories, autopct='%1.1f%%', 
                       colors=colors, explode=[0.02]*len(categories),
                       shadow=True, startangle=90)
                plt.axis('equal')
            
            plt.title(f"Analisis: {unit}" if unit else "Analisis Cuantitativo", fontsize=12, fontweight='bold')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            # Convertir a base64
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
            plt.close()
            
            logger.node_exit("quant_chart", f"Generated {chart_type} chart, {len(image_base64)} bytes")
            return image_base64
            
        except Exception as e:
            logger.debug("quant_chart", f"Attempt {attempt + 1} failed: {e}")
            plt.close('all')
            if attempt == max_retries - 1:
                logger.error("quant_chart", e)
                return None
    
    return None


async def generate_insight(chart_type: ChartType, data: dict, question: str) -> str:
    """Interpreta los datos y genera insight textual."""
    logger.node_enter("quant_insight", {"chart_type": chart_type})
    
    try:
        llm = get_llm(temperature=0.1)
        prompt = INSIGHT_PROMPT.format(
            chart_type=chart_type if chart_type != "none" else "sin grafico (solo texto)",
            data=json.dumps(data, ensure_ascii=False),
            question=question
        )
        
        response = await llm.ainvoke([
            SystemMessage(content="Eres QuanT, un analista cuantitativo preciso y conciso."),
            HumanMessage(content=prompt)
        ])
        
        insight = response.content.strip()
        logger.node_exit("quant_insight", f"{len(insight)} chars")
        return insight
    except Exception as e:
        logger.error("quant_insight", e)
        # Fallback: generar insight basico
        if data.get("data_found") and data.get("values"):
            values = data["values"]
            categories = data.get("categories", [])
            unit = data.get("unit", "")
            if len(values) == 1:
                return f"El valor encontrado es **{values[0]} {unit}**."
            return f"Se encontraron {len(values)} valores: {', '.join(str(v) for v in values)} ({unit})."
        return "No se encontraron datos numericos relevantes para analizar."


async def quant_analyze(
    question: str,
    context: list[Document]
) -> tuple[str | None, str, str, str]:
    """
    Pipeline completo de QuanT.
    
    Returns:
        tuple: (chart_base64, chart_type, insights, data_quality)
    """
    logger.node_enter("quant_analyze", {"question": question})
    
    try:
        # 1. Extraer datos numericos
        data = await extract_numerical_data(context, question)
        
        # 2. Seleccionar estrategia visual
        chart_type = await select_chart_strategy(data, question)
        
        # 3. Generar grafico (con retry)
        chart_base64 = generate_chart(data, chart_type) if chart_type not in ["none", "table"] else None
        
        # 4. Generar insight
        insights = await generate_insight(chart_type, data, question)
        
        data_quality = data.get("data_quality", "incomplete")
        
        logger.node_exit("quant_analyze", f"chart: {chart_type}, quality: {data_quality}")
        return chart_base64, chart_type, insights, data_quality
        
    except Exception as e:
        logger.error("quant_analyze", e)
        return None, "none", "Error al procesar analisis cuantitativo.", "incomplete"
