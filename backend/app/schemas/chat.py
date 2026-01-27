from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


class QueryResponse(BaseModel):
    answer: str
    sources: list[str] = Field(default_factory=list)


class IngestResponse(BaseModel):
    status: str
    filename: str
    chunks_processed: int
