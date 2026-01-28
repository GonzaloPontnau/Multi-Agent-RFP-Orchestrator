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

## 4. Flujo del Agente Multi-Agent (LangGraph) - IMPLEMENTADO

```
State: {
    question: str,
    context: List[Doc],
    filtered_context: List[Doc],
    answer: str,
    audit_result: str,
    revision_count: int
}
```

```
[START] --> [Retrieve (k=10)] --> [Grade_Documents]
                                        |
                                  (Filtra docs relevantes)
                                        |
                                  [Generate Answer] --> [Auditor_Check]
                                                              |
                                                       (Pasa Calidad?)
                                                       /            \
                                                     NO              SI
                                                    /                 \
                                          [Refine_Answer]           [END]
                                                 |
                                                 v
                                          (max 2 revisiones)
                                                 |
                                          [Auditor_Check] <--+
```

### Descripcion de Nodos:
- **Retrieve**: Busca k=10 chunks del vector store
- **Grade_Documents**: LLM evalua relevancia de cada chunk para la pregunta
- **Generate**: Genera respuesta con contexto filtrado
- **Auditor_Check**: Verifica calidad (responde la pregunta?, tiene datos concretos?)
- **Refine_Answer**: Mejora respuestas insuficientes (max 2 intentos)