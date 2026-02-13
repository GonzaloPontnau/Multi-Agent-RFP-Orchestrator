"""Coleccion de routers de la API."""

from app.api.routes.chat import router as chat_router
from app.api.routes.documents import router as documents_router

__all__ = ["chat_router", "documents_router"]
