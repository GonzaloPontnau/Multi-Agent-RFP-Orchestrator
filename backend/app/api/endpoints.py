import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, status

from app.agents import rfp_app
from app.core.logging import AgentLogger, get_logger
from app.schemas import (
    AgentMetadata,
    IngestResponse,
    QuantAnalysis,
    QueryRequest,
    QueryResponse,
    RiskAssessment,
)
from app.services import get_rag_service

logger = get_logger(__name__)
agent_logger = AgentLogger("pipeline")
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


@router.get("/documents")
async def get_documents():
    """Obtiene lista de documentos indexados para sincronizar con el frontend."""
    try:
        rag = get_rag_service()
        documents = await rag.get_indexed_documents()
        return {"status": "success", "documents": documents}
    except Exception as e:
        logger.error(f"Error obteniendo documentos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/chat", response_model=QueryResponse)
async def chat(request: QueryRequest):
    """Procesa una pregunta usando el grafo de agentes con subagentes especializados."""
    
    try:
        # Log inicio del pipeline
        agent_logger.pipeline_start(request.question)
        
        result = await rfp_app.ainvoke({
            "question": request.question,
            "context": [],
            "filtered_context": [],
            "domain": "",
            "answer": "",
            "audit_result": "",
            "revision_count": 0,
            # Campos para QuanT
            "quant_chart": None,
            "quant_chart_type": None,
            "quant_insights": None,
            "quant_data_quality": None,
            # Campos para Risk Sentinel
            "risk_level": None,
            "compliance_status": None,
            "risk_issues": [],
            "gate_passed": None,
            # Flag para no-documentos
            "no_documents": None,
        })

        # Log resumen del pipeline completo
        agent_logger.pipeline_end(result)

        # Extraer documentos y fuentes
        context_docs = result.get("context", [])
        filtered_docs = result.get("filtered_context") or context_docs
        sources = list({
            doc.metadata.get("source", "")
            for doc in filtered_docs
            if doc.metadata.get("source")
        })

        # Construir QuantAnalysis si existe
        quant_analysis = None
        if result.get("quant_chart") or result.get("quant_insights"):
            quant_analysis = QuantAnalysis(
                chart_base64=result.get("quant_chart"),
                chart_type=result.get("quant_chart_type"),
                insights=result.get("quant_insights", ""),
                data_quality=result.get("quant_data_quality", "incomplete"),
            )

        # Construir RiskAssessment si existe
        risk_assessment = None
        if result.get("risk_level"):
            risk_assessment = RiskAssessment(
                risk_level=result.get("risk_level", "medium"),
                compliance_status=result.get("compliance_status", "pending"),
                issues=result.get("risk_issues", []),
                gate_passed=result.get("gate_passed", True),
            )

        # Construir metadata del flujo de agentes
        domain = result.get("domain", "general")
        specialist_name = "quant" if domain == "quantitative" else f"specialist_{domain}"
        
        metadata = AgentMetadata(
            domain=domain,
            specialist_used=specialist_name,
            documents_retrieved=len(context_docs),
            documents_filtered=len(filtered_docs),
            revision_count=result.get("revision_count", 0),
            audit_result=result.get("audit_result", "N/A"),
            quant_analysis=quant_analysis,
            risk_assessment=risk_assessment,
        )

        return QueryResponse(
            answer=result["answer"],
            sources=sources,
            agent_metadata=metadata,
        )

    except Exception as e:
        logger.error(f"[CHAT] Error procesando consulta: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error procesando pregunta: {str(e)}",
        )
