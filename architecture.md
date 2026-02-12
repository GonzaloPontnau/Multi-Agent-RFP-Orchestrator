# TenderCortex - Architecture Blueprint

## 1. Vision General

Sistema multi-agente para automatizar el analisis de licitaciones publicas. Utiliza **LangGraph** como orquestador de estados para coordinar ingesta de documentos, RAG (Retrieval-Augmented Generation), enrutamiento inteligente a subagentes especializados, y auditoria de calidad con refinamiento iterativo.

## 2. Stack Tecnologico

| Componente | Tecnologia | Notas |
|------------|------------|-------|
| **Orquestacion** | LangGraph | State Machine con subagentes |
| **LLM** | Groq API (Llama 3.3 70B) | Alta velocidad, bajo costo |
| **Embeddings** | HuggingFace Inference API | Cloud-based (ahorra RAM) |
| **Vector DB** | Qdrant (In-Memory) | Efimero por diseno, zero-maintenance |
| **Backend** | FastAPI (Async) | Pydantic V2 |
| **Frontend** | React + Vite + TypeScript | TailwindCSS |
| **Ingesta** | Docling | Extraccion de PDF |

## 3. Estructura del Proyecto

```
/TenderCortex
├── backend/
│   ├── app/
│   │   ├── agents/               # LangGraph: orquestacion multi-agente
│   │   │   ├── rfp_graph.py      # Grafo principal (StateGraph)
│   │   │   ├── agent_factory.py  # Factory pattern para agentes
│   │   │   ├── risk_sentinel.py  # Auditor de compliance y riesgo
│   │   │   ├── quant.py          # Analista cuantitativo
│   │   │   ├── base/             # Clase base Agent (OOP)
│   │   │   ├── specialists/      # 6 subagentes por dominio
│   │   │   └── prompts/          # Templates de prompts
│   │   ├── api/                  # Endpoints REST
│   │   ├── core/                 # Config, logging, excepciones
│   │   ├── schemas/              # Modelos Pydantic (request/response)
│   │   └── services/             # RAG, LLM, embeddings, vector store
│   │
│   ├── skills/                   # 8 skills del producto
│   │   ├── compliance_audit_validator/
│   │   ├── context_retriever/
│   │   ├── financial_table_parser/
│   │   ├── gantt_timeline_extractor/
│   │   ├── knowledge_graph_builder/
│   │   ├── rfp_document_loader/
│   │   ├── risk_score_calculator/
│   │   └── tech_stack_mapper/
│   │
│   └── tests/
│       ├── unit/                 # Tests unitarios
│       └── integration/          # Tests de integracion
│
└── frontend/
    └── src/
        ├── components/           # ChatInput, ChatMessage, Sidebar
        ├── hooks/                # useRFP (estado de la aplicacion)
        └── types.ts              # TypeScript definitions
```

## 4. Flujo del Agente (LangGraph StateGraph)

```
[START] → [Retrieve (k=10)] → [Grade Documents] → [Router]
                                                      │
                                              (Clasifica dominio)
                                                      │
                ┌──────┬──────┬──────┬──────┬──────┬──────┐
                │      │      │      │      │      │      │
             legal  tech  financial timeline reqs  general quant
                │      │      │      │      │      │      │
                └──────┴──────┴──────┴──────┴──────┴──────┘
                                    │
                              [Specialist]
                                    │
                            [Risk Sentinel]
                                    │
                             (Pasa auditoria?)
                              /            \
                            NO              SI
                           /                 \
                 [Refine Answer]            [END]
                        │
                  (max 2 intentos)
                        │
                 [Risk Sentinel] ←──┘
```

### Nodos del Grafo

| Nodo | Funcion |
|------|---------|
| **Retrieve** | Busca k=10 chunks relevantes del vector store |
| **Grade Documents** | LLM evalua relevancia de cada chunk |
| **Router** | Clasifica la pregunta en un dominio especializado |
| **Specialist** | Genera respuesta con el subagente del dominio |
| **Risk Sentinel** | Auditoria de calidad y compliance |
| **Refine** | Mejora respuestas rechazadas (max 2 iteraciones) |
| **QuanT** | Analisis cuantitativo cuando se detectan datos numericos |

### Dominios de Subagentes

| Dominio | Especialidad |
|---------|-------------|
| **legal** | Normativa, jurisdiccion, propiedad intelectual, sanciones |
| **technical** | Arquitectura, stack, integraciones, APIs, SLAs |
| **financial** | Presupuesto, pagos, garantias, ajustes de precios |
| **timeline** | Cronograma, fechas, plazos, fases, hitos |
| **requirements** | Requisitos de participacion, experiencia, personal |
| **general** | Consultas multi-dominio o no categorizables |
| **quantitative** | Analisis numerico, comparaciones, visualizaciones |

## 5. Skills del Producto

Cada skill sigue un patron consistente: `SKILL.md` + `definition.py` (Pydantic) + `impl.py`.

| Skill | Tipo | Funcion |
|-------|------|---------|
| **rfp_document_loader** | Ingesta | Carga y chunking de PDFs (nativo + OCR) |
| **context_retriever** | RAG | Recuperacion con MMR y filtrado por metadata |
| **compliance_audit_validator** | Auditoria | Verificacion de requisitos (COMPLIANT / NON_COMPLIANT / PARTIAL) |
| **risk_score_calculator** | Scoring | Viabilidad 0-100 con kill switch para riesgos criticos |
| **financial_table_parser** | Extraccion | Tablas financieras de PDF (monedas, celdas fusionadas) |
| **gantt_timeline_extractor** | Extraccion | Fechas ISO 8601, dependencias, hitos |
| **knowledge_graph_builder** | Analisis | Grafos de dependencias con deteccion de ciclos |
| **tech_stack_mapper** | Analisis | Normalizacion de tecnologias (200+ mappings canonicos) |

## 6. API Response

Cada respuesta incluye metadata de trazabilidad del pipeline completo:

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

## 7. Arquitectura de Despliegue

```
[Browser] → [Vercel: React/Vite] → [Render: FastAPI] → [Groq + HuggingFace + Qdrant]
```

| Capa | Servicio | Notas |
|------|----------|-------|
| **Frontend** | Vercel | React + Vite, deploy automatico |
| **Backend** | Render (Free Tier) | FastAPI, ~50s cold start |
| **Vector DB** | Qdrant In-Memory | Efimero: Privacy by Design |
| **LLM** | Groq API | Llama 3.3 70B |
| **Embeddings** | HuggingFace API | Cloud-based |

Todos los subagentes corren en el mismo proceso. Son nodos del grafo LangGraph con prompts especializados, no microservicios independientes.
