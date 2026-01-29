
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
| **Vector DB** | Qdrant (In-Memory) | Zero-maintenance vector storage for ephemeral deployments. |
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

## Strategic Value for Enterprise Leaders

The goal of this project is to demonstrate my ability to create these **Multi-Agent systems** at the corporate and enterprise levels. This system is not just software; it's a scalable and autonomous workforce designed to boost your team's productivity.

### Why Integrate Multi-Agent Systems?

*   **Operational Agility**: Reduce RFP response cycles from weeks to hours. Our agents work in parallel—parsing, retrieving, and drafting—allowing your human experts to focus purely on high-value strategy and review.
*   **Risk Mitigation**: The dedicated **Risk Sentinel** and **Legal Auditor** agents ensure every proposal adheres strictly to your corporate compliance and risk frameworks, eliminating costly oversight errors.
*   **Cost Efficiency**: Deploy a 24/7 digital workforce that scales instantly with demand, dramatically lowering the operational overhead of pre-sales and technical writing.
*   **Data-Driven Decisions**: Transform your historical repository of tenders into an active knowledge asset, ensuring consistency and leveraging past successes for future wins.