import asyncio
from logging import getLogger

from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from core.config.settings import settings
from ruark_audio_system.ruark_r5_controller import RuarkR5Controller

logger = getLogger(__name__)


class StreamHandler:
    """Класс для управления потоковой передачей и воспроизведением на Ruark."""
    def __init__(self, ruark_controls: RuarkR5Controller):
        self._ruark_lock = asyncio.Lock()
        self._ffmpeg_process: asyncio.subprocess.Process | None = None
        self._ruark_controls = ruark_controls

    async def execute_with_lock(self, func, *args, **kwargs):
        """Выполняет вызов UPnP-команды в Ruark с блокировкой."""
        async with self._ruark_lock:
            for attempt in range(3):
                try:
                    logger.debug(f"🔹 Выполняем {func.__name__} с аргументами {args}, {kwargs}")
                    await func(*args, **kwargs)
                    logger.debug(f"✅ {func.__name__} выполнено успешно")
                    return
                except Exception as e:
                    logger.warning(
                        f"⚠️ Ошибка при {func.__name__}, попытка {attempt + 1}: {e}")
                    await asyncio.sleep(1)

    async def stop_ffmpeg(self):
        """Останавливает текущий процесс FFmpeg, если он запущен."""
        if self._ffmpeg_process:
            logger.info("⏹ Останавливаем текущий поток FFmpeg...")
            try:
                self._ffmpeg_process.terminate()  # Попробуем мягкое завершение
                await self._ffmpeg_process.wait()
            except ProcessLookupError:
                logger.warning("⚠️ FFmpeg уже завершился")
            except asyncio.TimeoutError:
                logger.warning(
                    "⚠️ FFmpeg не завершился, принудительное завершение."
                )
                self._ffmpeg_process.kill()

            self._ffmpeg_process = None  # Очистка переменной

    async def start_ffmpeg_stream(self, yandex_url: str):
        """Запускает потоковую передачу через FFmpeg."""
        await self.stop_ffmpeg()  # Останавливаем старый процесс перед запуском нового

        logger.info(f"🎥 Запуск потоковой передачи с {yandex_url}")

        self._ffmpeg_process = await asyncio.create_subprocess_exec(
            "ffmpeg", "-re",  # 🔥 Читаем файл с реальной скоростью
            "-i", yandex_url,  # 🔗 Прямая передача ссылки
            "-acodec", "libmp3lame", "-b:a", "320k", "-f", "mp3", "pipe:1",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

    async def stream_audio(self):
        """Отправляет потоковые данные в ответ на HTTP-запрос."""
        if not self._ffmpeg_process:
            raise HTTPException(status_code=404, detail="Поток не запущен")

        async def generate():
            while True:
                chunk = await self._ffmpeg_process.stdout.read(4096)
                if not chunk:
                    break
                yield chunk

        return StreamingResponse(generate(), media_type="audio/mpeg")

    async def play_stream(self, yandex_url: str):
        """Запускает потоковую трансляцию и передает её на Ruark."""
        logger.info(f"🎶 Начинаем потоковое воспроизведение {yandex_url}")

        # Запускаем потоковую передачу
        await self.start_ffmpeg_stream(yandex_url)
        track_url = (
            f"http://{settings.local_server_host}:"
            f"{settings.local_server_port_dlna}/live_stream.mp3"
        )
        logger.info(f"📡 Поток доступен по URL: {track_url}")

        # Устанавливаем новый поток
        await self.execute_with_lock(
            self._ruark_controls.set_av_transport_uri,
            track_url
        )

        # Запускаем воспроизведение
        await self.execute_with_lock(
            self._ruark_controls.play
        )
