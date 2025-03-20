import asyncio
from logging import getLogger

from fastapi import APIRouter

from core.dependencies.main_di_container import MainDIContainer
from main_stream_service.main_stream_manager import MainStreamManager

logger = getLogger(__name__)

router = APIRouter()

di_container = MainDIContainer().get_container()

main_stream_manager = di_container.get(MainStreamManager)


@router.post("/stream_on")
async def stream_on():
    """API-команда для запуска стрима"""
    asyncio.create_task(main_stream_manager.start())
    return {"status": "stream_on"}


@router.post("/shutdown")
async def shutdown():
    """API-команда для остановки стрима"""
    await main_stream_manager.stop()
    return {"status": "main_service stopped"}
