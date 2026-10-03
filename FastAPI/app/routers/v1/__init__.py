from app.routers.v1.auth import router as auth_router
from app.routers.v1.documents import router as documents_router
from app.routers.v1.chat import router as chat_router

__all__ = [
    "auth_router",
    "documents_router",
    "chat_router",
]
