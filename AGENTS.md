# AGENTS.md - TenderCortex Development Constitution

> **Propósito**: Este archivo es la guía operativa para cualquier agente de IA de desarrollo (Claude, Cursor, Copilot, Gemini) que trabaje en este repositorio. Define convenciones, patrones y reglas que deben seguirse estrictamente.

---

## 1. Project Overview

**TenderCortex** es un sistema multi-agente de inteligencia artificial para automatizar el análisis y respuesta a licitaciones públicas.

### Stack Tecnológico Principal

| Capa | Tecnología | Notas |
|------|------------|-------|
| **Orquestación** | LangGraph | State machines con subagentes especializados |
| **LLM** | Groq API (`openai/gpt-oss-120b`) | Alta velocidad, bajo costo |
| **Embeddings** | HuggingFace Inference API | Cloud-based (ahorra RAM) |
| **Vector DB** | Qdrant (In-Memory) | Efímero por diseño, zero-maintenance |
| **Backend** | FastAPI (Python 3.11+) | Async, Pydantic V2 |
| **Frontend** | React + TypeScript + Vite | TailwindCSS para estilos |
| **Ingesta** | Docling | Extracción de PDF |

### Arquitectura de Despliegue

```
[Browser] → [Vercel: React/Vite] → [Render: FastAPI] → [Groq + HuggingFace + Qdrant]
```

- **Frontend**: Vercel (https://multi-agent-rfp-orchestrator.vercel.app)
- **Backend**: Render Free Tier (~50s cold start)
- **Vector Store**: In-memory (datos efímeros por sesión)

---

## 2. Setup & Validation Commands

### Backend (Python)

```bash
cd backend

# Crear entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar tests (SIEMPRE antes de confirmar cambios)
pytest -v

# Ejecutar servidor de desarrollo
uvicorn app.main:app --reload --port 8000
```

### Frontend (TypeScript)

```bash
cd frontend

# Instalar dependencias
npm install

# Servidor de desarrollo
npm run dev

# Validar build de producción
npm run build

# Linting
npm run lint
```

### Validación Pre-Commit

> [!IMPORTANT]
> **Antes de cualquier commit**, ejecutar:
> ```bash
> cd backend && pytest -v
> cd frontend && npm run build
> ```

---

## 3. Code Style & Conventions

### Python (Backend)

#### Typing y Schemas

```python
# ✅ CORRECTO: Pydantic V2 con Field descriptions
from pydantic import BaseModel, Field

class QueryRequest(BaseModel):
    """Request para consultas al sistema."""
    
    question: str = Field(
        ...,
        min_length=3,
        description="Pregunta del usuario sobre el documento."
    )
    max_results: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Número máximo de resultados a retornar."
    )

# ❌ INCORRECTO: Sin types ni descriptions
def process(data):
    return data["question"]
```

#### Async y FastAPI

```python
# ✅ CORRECTO: Async con type hints
from fastapi import APIRouter

router = APIRouter()

@router.post("/chat", response_model=QueryResponse)
async def chat_endpoint(request: QueryRequest) -> QueryResponse:
    """Procesa una consulta del usuario."""
    result = await rag_service.query(request.question)
    return QueryResponse(answer=result)

# ❌ INCORRECTO: Sync sin types
@router.post("/chat")
def chat(data):
    return {"answer": process(data)}
```

#### Logging

```python
# ✅ CORRECTO: Usar AgentLogger
from app.core.logging import AgentLogger

logger = AgentLogger(__name__)
logger.log_routing("retrieve", "grade_documents", "10 docs found")

# ❌ INCORRECTO: Nunca usar print()
print("Processing...")  # NO!
```

#### Docstrings

```python
# ✅ CORRECTO: Docstrings en español (proyecto bilingüe)
def retrieve_documents(query: str, k: int = 10) -> list[Document]:
    """Recupera documentos relevantes del vector store.
    
    Args:
        query: Texto de búsqueda.
        k: Número de documentos a recuperar.
    
    Returns:
        Lista de documentos ordenados por relevancia.
    
    Raises:
        VectorStoreError: Si el store no está disponible.
    """
    ...
```

### TypeScript (Frontend)

#### Components

```typescript
// ✅ CORRECTO: Functional components con types explícitos
interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
  sources?: string[];
  agentMetadata?: AgentMetadata;
}

export function ChatMessage({ role, content, sources, agentMetadata }: ChatMessageProps) {
  return (
    <div className={`flex gap-4 ${role === "user" ? "flex-row-reverse" : ""}`}>
      {/* ... */}
    </div>
  );
}

// ❌ INCORRECTO: any types, class components
export class ChatMessage extends React.Component<any> { ... }
```

#### Hooks

```typescript
// ✅ CORRECTO: Custom hooks con return type
export function useRFP(): UseRFPReturn {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const askQuestion = async (question: string): Promise<QueryResponse | null> => {
    // ...
  };
  
  return { loading, error, askQuestion };
}
```

#### Estilos

```typescript
// ✅ CORRECTO: TailwindCSS con clases utilitarias
<div className="bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
  <h1 className="text-2xl font-bold text-orange-500">TenderCortex</h1>
</div>

// ❌ INCORRECTO: Inline styles, CSS modules
<div style={{ backgroundColor: "black" }}>...</div>
```

---

## 4. Project Anatomy

```
/TenderCortex
├── AGENTS.md              # ← ESTE ARCHIVO (guía para IAs de desarrollo)
├── ARCHITECTURE.md        # Documentación técnica detallada
├── README.md              # Documentación para usuarios
│
├── backend/
│   ├── app/
│   │   ├── agents/        # 🧠 LangGraph: flujos y subagentes
│   │   │   ├── rfp_graph.py       # Grafo principal (StateGraph)
│   │   │   ├── subagents.py       # Subagentes especializados (legacy)
│   │   │   ├── base_agent.py      # Clase base Agent (OOP)
│   │   │   └── agent_factory.py   # Factory para crear agentes
│   │   │
│   │   ├── api/           # 🌐 Endpoints REST (FastAPI routers)
│   │   │   └── chat.py
│   │   │
│   │   ├── core/          # ⚙️ Configuración y utilidades
│   │   │   ├── config.py          # Settings (Pydantic BaseSettings)
│   │   │   └── logging.py         # AgentLogger
│   │   │
│   │   ├── schemas/       # 📊 Modelos Pydantic para API
│   │   │   └── chat.py
│   │   │
│   │   ├── services/      # 🔧 Servicios de negocio
│   │   │   ├── rag_service.py     # Retrieval-Augmented Generation
│   │   │   ├── llm_service.py     # Wrapper para Groq
│   │   │   └── embeddings.py      # HuggingFace embeddings
│   │   │
│   │   └── main.py        # 🚀 Entry point de la aplicación
│   │
│   ├── skills/            # 🎯 Skills del PRODUCTO (NO de desarrollo)
│   │   ├── compliance-audit-validator/
│   │   │   ├── SKILL.md           # Documentación para agentes LLM
│   │   │   ├── definition.py      # Modelos Pydantic
│   │   │   └── impl.py            # Implementación
│   │   └── ...
│   │
│   ├── tests/             # 🧪 Tests
│   │   ├── conftest.py            # Fixtures compartidas
│   │   └── unit/
│   │
│   ├── requirements.txt
│   ├── pytest.ini
│   └── Dockerfile
│
└── frontend/
    ├── src/
    │   ├── components/    # 🎨 Componentes React
    │   │   ├── ChatInput.tsx
    │   │   ├── ChatMessage.tsx
    │   │   └── Sidebar.tsx
    │   │
    │   ├── hooks/         # 🪝 Custom hooks
    │   │   └── useRFP.ts
    │   │
    │   ├── types.ts       # 📐 TypeScript definitions
    │   └── App.tsx        # 📱 Componente raíz
    │
    ├── package.json
    ├── vite.config.ts
    └── vercel.json
```

---

## 5. Agent Architecture (LangGraph)

### Flujo Principal

```
[START] → [retrieve] → [grade_documents] → [router] → [specialist_*] → [risk_sentinel/auditor] → [END]
                                              │                                │
                                              │                                ↓
                                              │                         (si falla)
                                              │                         [refine] ←──┘
                                              │
                                              └→ [quant] (si dominio = quantitative)
```

### Estado del Agente (TypedDict)

```python
class AgentState(TypedDict):
    question: str                    # Pregunta del usuario
    context: list[Document]          # Documentos recuperados
    filtered_context: list[Document] # Documentos post-grading
    domain: str                      # Dominio clasificado
    answer: str                      # Respuesta generada
    audit_result: str                # pass/fail
    revision_count: int              # Iteraciones de refinamiento
    
    # QuanT (análisis cuantitativo)
    quant_chart: str | None
    quant_insights: str | None
    
    # Risk Sentinel (compliance)
    risk_level: str | None
    compliance_status: str | None
    risk_issues: list[str]
    gate_passed: bool | None
```

### Dominios de Subagentes

| Dominio | Palabras Clave | Especialización |
|---------|----------------|-----------------|
| `legal` | contrato, cláusula, jurisdicción | Normativa y compliance |
| `financial` | presupuesto, pago, garantía | Análisis financiero |
| `technical` | arquitectura, API, integración | Requisitos técnicos |
| `timeline` | fecha, plazo, cronograma | Gestión temporal |
| `requirements` | requisitos, experiencia, personal | Elegibilidad |
| `quantitative` | comparar, porcentaje, gráfico | Análisis de datos |
| `general` | (fallback) | Consultas generales |

### Crear un Nuevo Subagente

```python
# backend/app/agents/your_agent.py
from app.agents.base_agent import BaseAgent

class YourNewAgent(BaseAgent):
    """Agente especializado en [DOMINIO]."""
    
    domain = "your_domain"
    
    def _get_system_prompt(self) -> str:
        return """Eres un experto en [DOMINIO]...
        
        REGLAS:
        1. Responde SOLO basándote en el contexto proporcionado
        2. Si no hay información, indica que no está disponible
        3. Cita las fuentes cuando sea posible
        """
    
    def _format_context(self, docs: list[Document]) -> str:
        # Formateo específico del dominio
        return "\n\n".join(doc.page_content for doc in docs)
```

---

## 6. Skills Development Guidelines

> [!NOTE]
> Las skills en `backend/skills/` son para el **producto TenderCortex** (los agentes LLM que procesan licitaciones), NO para el desarrollo del proyecto.

### Estructura de una Skill

```
backend/skills/my-skill/
├── SKILL.md           # Documentación con YAML frontmatter
├── definition.py      # Modelos Pydantic (input/output)
├── impl.py            # Implementación
├── __init__.py        # Exports
└── tests/             # Tests específicos (opcional)
```

### SKILL.md Template

```markdown
---
name: my-skill-name
description: |
  Use this skill when [CONDICIÓN ESPECÍFICA].
  Do NOT use for [ANTI-PATRONES].
  This skill consumes [RECURSOS] per invocation.
---

# My Skill Name

## Propósito
[Descripción detallada]

## Cuándo Usar
- [Caso de uso 1]
- [Caso de uso 2]

## Cuándo NO Usar
- [Anti-patrón 1]
- [Anti-patrón 2]

## Entrada
| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `param1` | `str` | ✅ | [Descripción] |

## Salida
[Descripción de la respuesta estructurada]

## Ejemplos (Few-Shot)
[Mínimo 2-3 ejemplos de invocación]
```

### definition.py Patterns

```python
from enum import Enum
from pydantic import BaseModel, Field, field_validator

class MySkillStatus(str, Enum):
    """Estados posibles del resultado."""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"

class MySkillInput(BaseModel):
    """Input schema con validación."""
    
    query: str = Field(
        ...,
        min_length=10,
        description="Texto a procesar. Mínimo 10 caracteres."
    )
    mode: str = Field(
        default="standard",
        description="Modo de operación: 'standard' o 'detailed'."
    )
    
    @field_validator("query")
    @classmethod
    def normalize_query(cls, v: str) -> str:
        return v.strip().lower()

class MySkillOutput(BaseModel):
    """Output estructurado."""
    
    status: MySkillStatus
    result: str
    confidence: float = Field(ge=0.0, le=1.0)
```

---

## 7. API & Schema Patterns

### Response con Trazabilidad

Todas las respuestas del API deben incluir `agent_metadata`:

```python
class AgentMetadata(BaseModel):
    """Metadata de trazabilidad del pipeline."""
    
    domain: str = Field(description="Dominio del subagente usado")
    specialist_used: str = Field(description="Nombre del especialista")
    documents_retrieved: int
    documents_filtered: int
    revision_count: int
    audit_result: Literal["pass", "fail"]

class QueryResponse(BaseModel):
    answer: str
    sources: list[str]
    agent_metadata: AgentMetadata
```

### Error Handling

```python
# Excepciones tipadas
class TenderCortexError(Exception):
    """Base exception para el proyecto."""
    pass

class DocumentNotFoundError(TenderCortexError):
    """No se encontraron documentos."""
    pass

class LLMServiceError(TenderCortexError):
    """Error de comunicación con Groq/HuggingFace."""
    pass

# En endpoints
@router.post("/chat")
async def chat(request: QueryRequest) -> QueryResponse:
    try:
        result = await process(request)
        return result
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail="No documents loaded")
    except LLMServiceError as e:
        raise HTTPException(status_code=503, detail=str(e))
```

---

## 8. Testing Standards

### Configuración (pytest.ini)

```ini
[pytest]
testpaths = tests
python_files = test_*.py
asyncio_mode = auto
addopts = -v --tb=short

markers =
    slow: marks tests as slow
    integration: marks tests as integration tests
```

### Estructura de Tests

```python
# tests/unit/test_my_feature.py
import pytest
from app.services.my_service import MyService

class TestMyService:
    """Tests para MyService."""
    
    @pytest.fixture
    def service(self):
        """Fixture para crear instancia del servicio."""
        return MyService()
    
    async def test_process_valid_input(self, service):
        """Verifica procesamiento de input válido."""
        result = await service.process("valid query")
        assert result.status == "success"
    
    async def test_process_empty_raises(self, service):
        """Verifica que input vacío lanza excepción."""
        with pytest.raises(ValueError):
            await service.process("")
    
    @pytest.mark.slow
    async def test_process_large_document(self, service):
        """Test con documento grande (marcado como slow)."""
        ...
    
    @pytest.mark.integration
    async def test_with_real_llm(self, service):
        """Test de integración con Groq API real."""
        ...
```

### Fixtures Compartidas (conftest.py)

```python
# tests/conftest.py
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_llm():
    """Mock del servicio LLM."""
    mock = AsyncMock()
    mock.generate.return_value = "Mocked response"
    return mock

@pytest.fixture
def sample_documents():
    """Documentos de prueba."""
    return [
        Document(page_content="Contenido 1", metadata={"source": "test.pdf"}),
        Document(page_content="Contenido 2", metadata={"source": "test.pdf"}),
    ]
```

---

## 9. Boundaries & Prohibitions

### ❌ NUNCA Hacer

| Prohibición | Razón |
|-------------|-------|
| Commitear `.env` o API keys | Seguridad - keys en variables de entorno |
| Modificar `dist/`, `node_modules/`, `__pycache__/` | Archivos generados |
| Usar `print()` en backend | Usar `AgentLogger` para trazabilidad |
| Crear dependencias circulares | Rompe imports, dificulta testing |
| Usar `any` en TypeScript | Pierde type safety |
| Hardcodear URLs de API | Usar variables de entorno |
| Ignorar errores silenciosamente | Siempre loggear o propagar |
| Modificar `AGENTS.md` sin revisión | Guía operativa del proyecto |

### ✅ SIEMPRE Hacer

| Regla | Ejemplo |
|-------|---------|
| Ejecutar tests antes de confirmar | `pytest -v` (backend), `npm run build` (frontend) |
| Type hints en todas las funciones | `def process(query: str) -> Result:` |
| Descripciones en campos Pydantic | `Field(..., description="...")` |
| Manejar errores explícitamente | `try/except` con logging |
| Documentar funciones públicas | Docstrings con Args, Returns, Raises |
| Usar async para I/O | `async def`, `await` |

### Archivos Intocables

```plaintext
# NO MODIFICAR sin revisión explícita
backend/.env                    # Credenciales
backend/app/core/config.py      # Solo agregar, no cambiar existentes
frontend/.env                   # URLs de API
.gitignore                      # Configuración de Git
```

---

## 10. Deployment Notes

### Arquitectura de Producción

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│     Vercel      │     │     Render      │     │   Qdrant        │
│   (Frontend)    │────▶│   (Backend)     │────▶│  (In-Memory)    │
│   React + Vite  │     │   FastAPI       │     │  Ephemeral      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                    ┌──────────┼──────────┐
                    ▼          ▼          ▼
              ┌─────────┐ ┌─────────┐ ┌─────────┐
              │  Groq   │ │HuggingFace│ │ Docling │
              │  (LLM)  │ │(Embeddings)│ │  (PDF)  │
              └─────────┘ └─────────┘ └─────────┘
```

### Variables de Entorno Requeridas

**Backend (Render):**
```plaintext
GROQ_API_KEY=gsk_...
GROQ_MODEL=openai/gpt-oss-120b
HUGGINGFACE_API_KEY=hf_...
APP_ENV=production
LOG_LEVEL=INFO
```

**Frontend (Vercel):**
```plaintext
VITE_API_URL=https://multi-agent-rfp-orchestrator-backend.onrender.com
```

### Consideraciones de Free Tier

- **Render**: Cold starts de ~50 segundos. Primera request después de inactividad será lenta.
- **Qdrant In-Memory**: Datos se pierden al reiniciar. Es intencional (Privacy by Design).
- **Groq API**: Rate limits. Modelo por defecto actual: `openai/gpt-oss-120b` (ajustable con `GROQ_MODEL`).

---

## Appendix: Quick Reference Card

```
┌─────────────────────────────────────────────────────────────────┐
│                    TENDERCORTEX CHEAT SHEET                     │
├─────────────────────────────────────────────────────────────────┤
│ SETUP                                                           │
│   Backend:  cd backend && pip install -r requirements.txt      │
│   Frontend: cd frontend && npm install                          │
│                                                                 │
│ DEV SERVERS                                                     │
│   Backend:  uvicorn app.main:app --reload --port 8000          │
│   Frontend: npm run dev                                         │
│                                                                 │
│ VALIDATE                                                        │
│   Backend:  pytest -v                                           │
│   Frontend: npm run build                                       │
│                                                                 │
│ KEY FILES                                                       │
│   Grafo LangGraph:    backend/app/agents/rfp_graph.py          │
│   Config:             backend/app/core/config.py               │
│   API Entry:          backend/app/main.py                      │
│   Frontend Entry:     frontend/src/App.tsx                     │
│                                                                 │
│ CONVENTIONS                                                     │
│   Python:  async, Pydantic V2, AgentLogger, type hints         │
│   TS:      Functional components, no any, TailwindCSS          │
│                                                                 │
│ PROHIBITIONS                                                    │
│   ❌ print()  ❌ .env commit  ❌ any type  ❌ circular imports  │
└─────────────────────────────────────────────────────────────────┘
```

---

*Last updated: 2026-02-04*
*Version: 1.0.0*
