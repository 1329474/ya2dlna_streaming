import asyncio
import tempfile
import os
import shutil
from logging import getLogger

from fastapi.responses import FileResponse

from core.config.settings import settings
from ruark_audio_system.ruark_r5_controller import RuarkR5Controller

logger = getLogger(__name__)


class StreamHandler:
    """Класс для управления потоковой передачей через временный mp3-файл."""

    def __init__(self, ruark_controls: RuarkR5Controller):
        self._ruark_controls = ruark_controls
        self._ruark_lock = asyncio.Lock()
        self._temp_dir = tempfile.mkdtemp(prefix="ruark_stream_")
        self._current_file_path: str | None = None

    async def execute_with_lock(self, func, *args, **kwargs):
        async with self._ruark_lock:
            for attempt in range(3):
                try:
                    logger.debug(f"Выполняем {func.__name__} с аргументами {args}, {kwargs}")
                    await func(*args, **kwargs)
                    logger.debug(f"✅ {func.__name__} выполнено успешно")
                    return
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка при {func.__name__}, попытка {attempt + 1}: {e}")
                    await asyncio.sleep(1)

    async def stop_stream(self):
        logger.info("⏹ Останавливаем текущий трек и удаляем файл...")
        await self.execute_with_lock(self._ruark_controls.stop)
        if self._current_file_path and os.path.exists(self._current_file_path):
            try:
                os.remove(self._current_file_path)
                logger.info(f"🗑 Удалён временный файл: {self._current_file_path}")
            except Exception as e:
                logger.warning(f"⚠️ Не удалось удалить файл: {e}")
        self._current_file_path = None

    async def start_ffmpeg_to_file(self, yandex_url: str):
        """Скачивает и перекодирует трек в mp3-файл."""
        await self.stop_stream()

        temp_file_path = os.path.join(self._temp_dir, "track.mp3")
        logger.info(f"🎧 Качаем и кодируем трек в {temp_file_path}")

        process = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", yandex_url,
            "-acodec", "libmp3lame", "-b:a", "320k",
            temp_file_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await process.communicate()

        if process.returncode != 0:
            logger.error(f"❌ Ошибка ffmpeg: {stderr.decode()}")
            raise Exception("Ошибка перекодировки ffmpeg")

        logger.info(f"✅ Трек перекодирован: {temp_file_path}")
        self._current_file_path = temp_file_path

    async def stream_audio(self):
        """Отдаёт закодированный файл в ответе FastAPI."""
        if not self._current_file_path:
            raise Exception("Поток не запущен")

        logger.info(f"📡 Отдаём файл: {self._current_file_path}")
        return FileResponse(self._current_file_path, media_type="audio/mpeg")

    async def play_stream(self, yandex_url: str):
        """Запускает воспроизведение локального mp3-файла на Ruark."""
        await self.stop_stream()
        await self.start_ffmpeg_to_file(yandex_url)

        track_url = (
            f"http://{settings.local_server_host}:{settings.local_server_port_dlna}/live_stream.mp3"
        )
        logger.info(f"📡 Поток доступен по URL: {track_url}")

        await self.execute_with_lock(self._ruark_controls.set_av_transport_uri, track_url)
        await self.execute_with_lock(self._ruark_controls.play)

    def cleanup(self):
        """Удаление временной директории при завершении приложения."""
        if os.path.exists(self._temp_dir):
            shutil.rmtree(self._temp_dir)
            logger.info(f"🧹 Удалена временная директория: {self._temp_dir}")
