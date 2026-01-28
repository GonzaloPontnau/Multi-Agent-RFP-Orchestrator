
<div align="center">
  <img src="frontend/public/logo.png" alt="Multi-Agent RFP Orchestrator Logo" width="200" />
  <h1>Multi-Agent RFP Orchestrator</h1>
  <p>
    <strong>Automated Tender Response System</strong><br>
    Intelligent document ingestion, information retrieval, and professional drafting using multi-agent architecture.
  </p>
</div>

---

## Overview

The **Multi-Agent RFP Orchestrator** is an advanced system designed to automate the process of responding to Requests for Proposals (RFPs). By leveraging a multi-agent architecture with specialized domain sub-agents, the system ingests tender documents (PDFs), retrieves relevant context using RAG (Retrieval-Augmented Generation), and synthesizes professional, compliant responses.

The core orchestration is handled by **LangGraph**, ensuring a robust state machine flow that includes quality auditing and iterative refinement of answers.

## Key Features

*   **Multi-Agent Architecture**: Clear separation of concerns with specialized agents for Legal, Financial, Technical, and Timeline domains.
*   **Intelligent Routing**: Automatically classifies inquiries to route them to the most appropriate domain specialist.
*   **RAG Pipeline**: Semantic search over ingested documents to ground answers in factual data.
*   **Quality Assurance**: Built-in auditor agent that validates responses against quality standards before delivery.
*   **Iterative Refinement**: Self-correction mechanism where the auditor can reject answers, triggering a refinement loop.
*   **Modern Stack**: Built with FastAPI, React, and leading AI orchestration tools.

## Architecture

The system operates on a state graph that coordinates the interaction between retrieval, reasoning, and generation.

```mermaid
graph TD
    START([Start]) --> Retrieve[Retrieve Context]
    Retrieve --> Grade[Grade Documents]
    Grade --> Router{Domain Router}
    
    Router -->|Legal| Legal[Specialist: Legal]
    Router -->|Technical| Tech[Specialist: Technical]
    Router -->|Financial| Fin[Specialist: Financial]
    Router -->|Timeline| Time[Specialist: Timeline]
    Router -->|Requirements| Reqs[Specialist: Requirements]
    Router -->|General| Gen[Specialist: General]
    
    Legal --> Auditor[Auditor Check]
    Tech --> Auditor
    Fin --> Auditor
    Time --> Auditor
    Reqs --> Auditor
    Gen --> Auditor
    
    Auditor -->|Pass| END([End])
    Auditor -->|Fail| Refine[Refine Answer]
    
    Refine --> Auditor
```

## Technology Stack

| Component | Technology | Description |
|-----------|------------|-------------|
| **Orchestration** | LangGraph | State machine management for multi-agent workflows. |
| **LLM Inference** | Groq API | Fast inference using Llama 3 models. |
| **Backend** | FastAPI | High-performance async Python framework. |
| **Frontend** | React + TypeScript | Modern, type-safe UI with TailwindCSS. |
| **Vector DB** | Pinecone | Serverless vector storage for embeddings. |
| **Ingestion** | Docling | PDF extraction and document processing. |

## Project Structure

```text
/rfp-orchestrator
├── backend
│   ├── app
│   │   ├── agents      # LangGraph flows and sub-agents
│   │   ├── core        # Configuration and logging
│   │   ├── services    # RAG, LLM, and Embeddings services
│   │   └── main.py     # Application entry point
│   └── requirements.txt
├── frontend
│   ├── src
│   │   ├── components  # UI Components
│   │   ├── hooks       # Custom React hooks
│   └── package.json
└── README.md
```

## Getting Started

### Prerequisites

*   Python 3.10+
*   Node.js 18+
*   API Keys for Groq and Pinecone

### Installation

1.  **Clone the repository**
    ```bash
    git clone https://github.com/your-username/Multi-Agent-RFP-Orchestrator.git
    cd Multi-Agent-RFP-Orchestrator
    ```

2.  **Backend Setup**
    ```bash
    cd backend
    pip install -r requirements.txt
    cp .env.example .env  # Configure your API keys
    uvicorn app.main:app --reload
    ```

3.  **Frontend Setup**
    ```bash
    cd frontend
    npm install
    npm run dev
    ```

## License

This project is proprietary. All rights reserved.
