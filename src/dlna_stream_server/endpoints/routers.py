from fastapi import APIRouter

from dlna_stream_server.endpoints.stream import router

main_router = APIRouter()

main_router.include_router(router)
