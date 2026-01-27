import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, status

from app.agents import rfp_app
from app.core.logging import get_logger
from app.schemas import IngestResponse, QueryRequest, QueryResponse
from app.services import get_rag_service

logger = get_logger(__name__)
router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(file: UploadFile):
    """Procesa un PDF y lo indexa en el vector store."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se permiten archivos PDF",
        )

    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp_path = Path(tmp.name)  # Asignar antes de cualquier operacion
            content = await file.read()
            tmp.write(content)

        rag = get_rag_service()
        chunks = await rag.ingest_document(tmp_path)
        
        logger.info(f"Documento '{file.filename}' procesado: {chunks} chunks")
        return IngestResponse(
            status="success",
            filename=file.filename,
            chunks_processed=chunks,
        )

    except Exception as e:
        logger.error(f"Error en ingesta: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error procesando documento: {str(e)}",
        )
    finally:
        if tmp_path:
            tmp_path.unlink(missing_ok=True)


@router.post("/chat", response_model=QueryResponse)
async def chat(request: QueryRequest):
    """Procesa una pregunta usando el grafo de agentes."""
    try:
        result = await rfp_app.ainvoke({
            "question": request.question,
            "context": [],
            "answer": "",
        })

        sources = list({
            doc.metadata.get("source", "")
            for doc in result.get("context", [])
            if doc.metadata.get("source")
        })

        return QueryResponse(answer=result["answer"], sources=sources)

    except Exception as e:
        logger.error(f"Error en chat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error procesando pregunta: {str(e)}",
        )
