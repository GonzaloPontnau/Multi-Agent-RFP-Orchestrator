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

    original_filename = file.filename
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp_path = Path(tmp.name)
            content = await file.read()
            tmp.write(content)

        rag = get_rag_service()
        chunks = await rag.ingest_document(tmp_path, original_filename=original_filename)
        
        logger.info(f"Documento '{original_filename}' procesado: {chunks} chunks")
        return IngestResponse(
            status="success",
            filename=original_filename,
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


@router.delete("/index")
async def clear_index():
    """Elimina todos los vectores del índice de Pinecone."""
    try:
        rag = get_rag_service()
        success = await rag.clear_index()
        if success:
            return {"status": "success", "message": "Índice limpiado exitosamente"}
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error limpiando el índice",
        )
    except Exception as e:
        logger.error(f"Error en clear_index: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/index/stats")
async def get_index_stats():
    """Obtiene estadísticas del índice de Pinecone."""
    try:
        rag = get_rag_service()
        stats = await rag.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Error en get_stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/chat", response_model=QueryResponse)
async def chat(request: QueryRequest):
    """Procesa una pregunta usando el grafo de agentes."""
    logger.info(f"[CHAT] Nueva consulta: {request.question[:80]}...")
    
    try:
        result = await rfp_app.ainvoke({
            "question": request.question,
            "context": [],
            "filtered_context": [],
            "answer": "",
            "audit_result": "",
            "revision_count": 0,
        })

        # Usar filtered_context si existe, sino context
        docs = result.get("filtered_context") or result.get("context", [])
        sources = list({
            doc.metadata.get("source", "")
            for doc in docs
            if doc.metadata.get("source")
        })

        logger.info(
            f"[CHAT] Respuesta generada | "
            f"Docs: {len(docs)} | Sources: {sources} | "
            f"Revisiones: {result.get('revision_count', 0)} | "
            f"Audit: {result.get('audit_result', 'N/A')}"
        )

        return QueryResponse(answer=result["answer"], sources=sources)

    except Exception as e:
        logger.error(f"[CHAT] Error procesando consulta: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error procesando pregunta: {str(e)}",
        )
