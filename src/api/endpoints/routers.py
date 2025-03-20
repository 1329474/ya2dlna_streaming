from fastapi import APIRouter

from api.endpoints.api_service import router

main_router = APIRouter()

main_router.include_router(router)
