# RFP Multi-Agent Orchestrator - Architecture Blueprint

## 1. Visión General
Sistema de automatización de respuestas a licitaciones (RFP) basado en arquitectura multi-agente. Utiliza un orquestador de estados (LangGraph) para coordinar la ingesta de documentos, recuperación de información (RAG) y generación de respuestas, asegurando consistencia y calidad.

## 2. Stack Tecnológico "Senior"
* **LLM Inference:** Ollama (Llama 3 ejecutándose localmente) - Privacidad y Costo Cero.
* **Orquestación:** LangGraph (State Machines en lugar de cadenas lineales).
* **Vector Database:** Pinecone (Serverless Free Tier).
* **Embeddings:** HuggingFace `all-MiniLM-L6-v2` (Local).
* **Backend:** FastAPI (Async, Pydantic V2 para validación estricta).
* **Ingesta:** Docling o PyPDF + RecursiveCharacterTextSplitter.
* **Frontend:** React + Vite + TypeScript + TailwindCSS (Clean Architecture).

## 3. Estructura de Directorios (Monorepo)
/rfp-orchestrator
├── /backend
│   ├── /app
│   │   ├── /core           # Configuración (Env vars, Logging, Security)
│   │   ├── /schemas        # Modelos Pydantic (Request/Response)
│   │   ├── /services       # Lógica de negocio (Ingesta, Pinecone, LLM Factory)
│   │   ├── /agents         # Grafos de LangGraph (Nodos y Aristas)
│   │   ├── /api            # Endpoints (Routes)
│   │   └── main.py         # Entrypoint
│   ├── requirements.txt
│   └── .env
├── /frontend
│   ├── /src
│   │   ├── /components     # UI Components (Atomic Design)
│   │   ├── /hooks          # Custom Hooks (useChat, useUpload)
│   │   ├── /services       # API Clients (Axios/Fetch)
│   │   └── App.tsx
│   └── package.json
└── README.md

## 4. Flujo del Agente (LangGraph)
State: { question: str, context: List[Doc], draft: str, critique: str, revisions: int }

[START] --> [Node: Retrieve] --> [Node: Grade_Documents]
                                      |
                               (Docs Relevantes?)
                                      |
                                   [Node: Generate Answer] --> [Node: Auditor_Check]
                                                                    |
                                                             (Pasa Calidad?)
                                                            /              \
                                                          NO               SI
                                                         /                  \
                                            [Node: Refine_Answer]        [END]