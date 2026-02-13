"""Endpoints de gestion documental para el indice vectorial."""

import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, status

from app.api.routes.chat import invalidate_cache
from app.core.logging import get_logger
from app.schemas import IngestResponse
from app.services import get_rag_service

logger = get_logger(__name__)
router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(file: UploadFile) -> IngestResponse:
    """Procesa un PDF y lo indexa en el vector store."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Solo se permiten archivos PDF")

    original_filename = file.filename
    tmp_path: Path | None = None
    try:
        tmp_path = Path(tempfile.mktemp(suffix=".pdf"))
        with open(tmp_path, "wb") as tmp:
            while chunk := await file.read(1024 * 256):
                tmp.write(chunk)

        rag = get_rag_service()
        chunks = await rag.ingest_document(tmp_path, original_filename=original_filename)
        invalidate_cache()
        logger.info(f"Documento '{original_filename}' procesado: {chunks} chunks")
        return IngestResponse(status="success", filename=original_filename, chunks_processed=chunks)
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
async def clear_index() -> dict:
    """Elimina todos los vectores del vector store."""
    try:
        rag = get_rag_service()
        success = await rag.clear_index()
        if success:
            invalidate_cache()
            return {"status": "success", "message": "Indice limpiado exitosamente"}
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error limpiando el indice")
    except Exception as e:
        logger.error(f"Error en clear_index: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/index/stats")
async def get_index_stats() -> dict:
    """Obtiene estadisticas del vector store."""
    try:
        rag = get_rag_service()
        return await rag.get_stats()
    except Exception as e:
        logger.error(f"Error en get_stats: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/documents")
async def get_documents() -> dict:
    """Obtiene lista de documentos indexados para sincronizar con frontend."""
    try:
        rag = get_rag_service()
        documents = await rag.get_indexed_documents()
        return {"status": "success", "documents": documents}
    except Exception as e:
        logger.error(f"Error obteniendo documentos: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
