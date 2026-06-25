from fastapi import APIRouter
from src.api.v1 import auth_handlers, category_handlers

api_router = APIRouter()

api_router.include_router(auth_handlers.router)
api_router.include_router(category_handlers.router)



