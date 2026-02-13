from fastapi import APIRouter

from app.api.routes import chat_router, documents_router

router = APIRouter()
router.include_router(documents_router)
router.include_router(chat_router)

__all__ = ["router"]
