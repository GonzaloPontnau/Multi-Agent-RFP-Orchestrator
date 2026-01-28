# RFP Multi-Agent Orchestrator - Architecture Blueprint

## 1. Vision General ✅
Sistema de automatizacion de respuestas a licitaciones (RFP) basado en arquitectura multi-agente con **subagentes especializados por dominio**. Utiliza un orquestador de estados (LangGraph) para coordinar la ingesta de documentos, recuperacion de informacion (RAG) y generacion de respuestas con enrutamiento inteligente.

## 2. Stack Tecnologico ✅
| Componente | Tecnologia | Notas |
|------------|------------|-------|
| **LLM Inference** | Groq API (Llama 3.3 70B) | Alta velocidad, bajo costo ✅ |
| **Orquestacion** | LangGraph | State Machines con subagentes ✅ |
| **Vector Database** | Pinecone (Serverless) | Free Tier ✅ |
| **Embeddings** | HuggingFace `all-MiniLM-L6-v2` | Local ✅ |
| **Backend** | FastAPI (Async) | Pydantic V2 ✅ |
| **Ingesta** | Docling | Extraccion de PDF ✅ |
| **Frontend** | React + Vite + TypeScript | TailwindCSS ✅ |

## 3. Estructura de Directorios (Monorepo) ✅
```
/rfp-orchestrator
├── /backend
│   ├── /app
│   │   ├── /core           # Config, Logging (AgentLogger), Settings
│   │   ├── /schemas        # Pydantic: QueryRequest, QueryResponse, AgentMetadata
│   │   ├── /services       # RAG, Embeddings, LLM Factory
│   │   ├── /agents
│   │   │   ├── rfp_graph.py    # Grafo principal LangGraph
│   │   │   └── subagents.py    # Router + 6 subagentes especializados
│   │   ├── /api            # Endpoints REST
│   │   └── main.py
│   ├── requirements.txt
│   └── .env
├── /frontend
│   ├── /src
│   │   ├── /components     # ChatMessage (con AgentMetadata badge)
│   │   ├── /hooks          # useRFP
│   │   ├── types.ts        # AgentMetadata, AgentDomain
│   │   └── App.tsx
│   └── package.json
└── README.md
```

## 4. Flujo del Agente Multi-Agent (LangGraph) ✅

```
State: {
    question: str,
    context: List[Doc],
    filtered_context: List[Doc],
    domain: str,          # Dominio clasificado (legal, technical, financial, etc.)
    answer: str,
    audit_result: str,
    revision_count: int
}
```

```
[START] --> [Retrieve (k=10)] --> [Grade_Documents] --> [Router]
                                                            |
                                                    (Clasifica dominio)
                                                            |
                    +-------+-------+-------+-------+-------+
                    |       |       |       |       |       |
                 legal  technical financial timeline requirements general
                    |       |       |       |       |       |
                    +-------+-------+-------+-------+-------+
                                        |
                                  [Specialist]
                                  (Subagente especializado)
                                        |
                                  [Auditor_Check]
                                        |
                                 (Pasa Calidad?)
                                  /            \
                                NO              SI
                               /                 \
                     [Refine_Answer]            [END]
                            |
                            v
                     (max 2 revisiones)
                            |
                     [Auditor_Check] <--+
```

### Descripcion de Nodos:
- **Retrieve**: Busca k=10 chunks del vector store ✅
- **Grade_Documents**: LLM evalua relevancia de cada chunk para la pregunta ✅
- **Router**: Clasifica la pregunta en un dominio especializado ✅
- **Specialist**: Genera respuesta usando el subagente del dominio apropiado ✅
- **Auditor_Check**: Verifica calidad considerando el dominio especializado ✅
- **Refine_Answer**: Mejora respuestas insuficientes con contexto del dominio (max 2 intentos) ✅

### Dominios de Subagentes Especializados ✅
| Dominio | Especialidad | Estado |
|---------|-------------|--------|
| **legal** | Normativa, jurisdiccion, propiedad intelectual, confidencialidad, sanciones | ✅ |
| **technical** | Arquitectura, stack tecnologico, integraciones, APIs, SLAs tecnicos | ✅ |
| **financial** | Presupuesto, pagos, garantias, financiamiento, ajustes de precios | ✅ |
| **timeline** | Cronograma, fechas, plazos, fases, hitos temporales | ✅ |
| **requirements** | Requisitos de participacion, experiencia, personal clave, capacidades | ✅ |
| **general** | Preguntas que abarcan multiples dominios o no encajan en categorias especificas | ✅ |

## 5. API Response con Metadata de Agentes ✅

Cada respuesta del endpoint `/api/chat` incluye metadata de trazabilidad:

```json
{
  "answer": "El presupuesto total es...",
  "sources": ["LICITACION.pdf"],
  "agent_metadata": {
    "domain": "financial",
    "specialist_used": "specialist_financial",
    "documents_retrieved": 10,
    "documents_filtered": 4,
    "revision_count": 0,
    "audit_result": "pass"
  }
}
```

## 6. Sistema de Logging y Trazabilidad ✅

El pipeline genera logs detallados de cada paso:

```
╔══ PIPELINE START ═════════════════════════════════════════════════
║ Question: Cual es el presupuesto total?
║ Flow: START → retrieve → grade_documents → router → specialist → auditor → END
═════════════════════════════════════════════════════════════════════
◆ ROUTING: START → retrieve | Reason: Initial node
◆ ROUTING: retrieve → grade_documents | Reason: Passing 10 docs
◆ SPECIALIST SELECTED: specialist_financial
◆ ROUTING: router → specialist_financial | Reason: Question classified as FINANCIAL
◆ ROUTING: auditor → END | Reason: Quality PASSED
╚══ PIPELINE COMPLETE ══════════════════════════════════════════════
   ◆ Domain Selected: FINANCIAL
   ◆ Specialist Used: specialist_financial
   ◆ Documents: 10 retrieved → 4 filtered
   ◆ Revisions: 0 | Audit: pass
```

## 7. Arquitectura de Despliegue ✅

```
                    [Cliente Browser]
                          │
                          ▼
                    [Frontend React]
                    (Vite Dev Server)
                          │
                          ▼ HTTP POST /api/chat
                    [FastAPI Backend]
                    (Puerto 8000)
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
     [Pinecone]      [Groq API]     [HuggingFace]
    (Vector DB)    (LLM Inference)  (Embeddings)
```

**Nota:** Todos los subagentes corren en el mismo proceso/puerto. No requieren puertos separados ya que son nodos del grafo LangGraph con prompts especializados, no microservicios independientes.

## 8. Subagentes Avanzados (Roadmap - Pendiente)

### 8.1 QuanT - Analista Cuantitativo

**Rol:** Cerebro matematico y visual. Garantiza que ningun numero sea una alucinacion y que los datos cuenten una historia visual.

**Mentalidad:**
> "No soy un escritor, soy un calculador. No adivino tendencias, las computo. Si los datos estan sucios, los limpio antes de usarlos. Mi salida es siempre evidencia visual o numerica verificada."

**Proceso Cognitivo:**
1. **Ingesta y Saneamiento:** Recibe datos desordenados (tablas de PDF, JSONs crudos). Detecta anomalias (nulos, formatos incorrectos) y estandariza.
2. **Seleccion de Estrategia Visual:**
   - Comparar volumenes -> Grafico de Barras
   - Evolucion temporal -> Grafico de Linea
   - Distribucion de presupuesto -> Grafico de Torta/Treemap
3. **Razonamiento de Codigo:** Formula algoritmo logico para transformar `Datos A` en `Grafico B`.
4. **Auto-Correccion (Loop):** Si el calculo da error o el grafico sale vacio, ajusta logica (ej. escala de ejes) y reintenta sin intervenir al usuario.
5. **Interpretacion:** Lee su propio grafico y genera un "Insight" (ej. "Notese la caida del 20% en Q3").

**Input:** Datos crudos + Intencion del usuario ("Comparame costos")
**Output:** Objeto de Imagen (Archivo) + Breve resumen analitico

**Integracion:** Nodo opcional activado cuando el router detecta necesidad de analisis cuantitativo/visual.

---

### 8.2 Risk Sentinel - Auditor de Gates

**Rol:** Oficial de cumplimiento (Compliance). Unico agente con permiso para decir "NO".

**Mentalidad:**
> "Confio, pero verifico. Mi trabajo es encontrar inconsistencias. No me importa lo bien que suene la propuesta; si no cumple la norma, la bloqueo. Soy pesimista por diseno."

**Proceso Cognitivo:**
1. **Desglose de Reglas:**
   - Reglas "Duras" (Binarias): Tiene firma? SI/NO
   - Reglas "Blandas" (Semanticas): Es el plan de mitigacion suficiente?
2. **Verificacion Cruzada (Fact-Checking):**
   - Toma afirmacion del borrador (ej. "Tenemos certificacion ISO 27001")
   - Busca en Base de Conocimiento la evidencia (certificado real)
   - Logica: Si encuentra certificado pero vencio en 2024 -> **ALERTA ROJA**
3. **Evaluacion de Gates:**
   - Identifica fase actual del proyecto (ej. Gate 2)
   - Comprueba requisitos minimos para esa fase
4. **Semaforo de Riesgo:**
   - Asigna puntaje de riesgo
   - Si riesgo es Alto, bloquea generacion de documento final hasta aprobacion humana

**Input:** Borrador del documento o respuesta propuesta + Estado del Proyecto
**Output:** Reporte de Auditoria (Aprobado / Rechazado con lista de problemas)

**Integracion:** Evolucion del nodo `auditor` actual con capacidades de compliance y verificacion cruzada.

---

### Flujo con Subagentes Avanzados (Futuro)

```
[Usuario] --> "Prepara respuesta financiera para Proyecto X"
      |
      v
[Orquestador] --> Identifica tarea compleja
      |
      +---> [QuanT] --> Busca excels, calcula margenes, genera grafico de flujo de caja
      |
      +---> [Specialist_Financial] --> Redacta texto con formato corporativo
      |
      v
[Risk Sentinel] --> Lee borrador, detecta margen 8% < politica 10%
      |
      v
[RECHAZO] --> "No puedo generar documento. Margen (8%) bajo politica corporativa (10%). Desea solicitar excepcion?"
```

**Diferencia Arquitectonica:**
- **Antes:** El agente *busca* informacion y la entrega
- **Con mejoras:**
  - **QuanT** *crea* nueva informacion (calculos/graficos)
  - **Risk Sentinel** *juzga* la informacion (auditoria avanzada)
