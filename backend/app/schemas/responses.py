from pydantic import BaseModel, Field

from app.schemas.metadata import AgentMetadata


class QueryResponse(BaseModel):
    answer: str
    sources: list[str] = Field(default_factory=list)
    agent_metadata: AgentMetadata = Field(description="Metadata del flujo de agentes para trazabilidad")


class IngestResponse(BaseModel):
    status: str
    filename: str
    chunks_processed: int
