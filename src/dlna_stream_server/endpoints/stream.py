import asyncio
from logging import getLogger

from fastapi import APIRouter, Response

from core.dependencies.main_di_container import MainDIContainer
from dlna_stream_server.handlers.stream_handler import StreamHandler

logger = getLogger(__name__)

router = APIRouter()

di_container = MainDIContainer().get_container()

stream_handler = di_container.get(StreamHandler)


@router.post("/set_stream")
async def set_stream(yandex_url: str):
    """Принимает URL трека и запускает потоковую передачу на Ruark."""
    logger.info(f"📥 Запуск нового потока с {yandex_url}")
    asyncio.create_task(stream_handler.play_stream(yandex_url))
    return {"message": "Стрим запущен", "stream_url": yandex_url}


@router.get("/live_stream.mp3")
async def serve_stream():
    """Раздает потоковый аудиофайл через HTTP."""
    return await stream_handler.stream_audio()


@router.head("/live_stream.mp3")
async def serve_head():
    """Обрабатывает HEAD-запрос для Ruark R5 с корректными заголовками."""
    headers = {
        "Content-Type": "audio/mpeg",
        "Accept-Ranges": "bytes",
        "Connection": "keep-alive",
    }
    return Response(headers=headers)


@router.post("/stop_stream")
async def stop_stream():
    """Останавливает потоковую передачу на Ruark."""
    logger.info("🛑 Остановка потоковой передачи...")
    await stream_handler.stop_ffmpeg()
    return {"message": "Потоковая передача остановлена"}
