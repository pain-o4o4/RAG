from fastapi import APIRouter
from app.routers.v1.auth import router as auth_router
from app.routers.v1.documents import router as documents_router
from app.routers.v1.chat import router as chat_router

api_router = APIRouter()

# Đăng ký các router con vào api_router
api_router.include_router(auth_router)
api_router.include_router(documents_router)
api_router.include_router(chat_router)
