from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.categories import router as categories_router
from app.api.routes.ebooks import router as ebooks_router
from app.api.routes.health import router as health_router
from app.api.routes.uploads import router as uploads_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(ebooks_router)
api_router.include_router(categories_router)
api_router.include_router(uploads_router)
