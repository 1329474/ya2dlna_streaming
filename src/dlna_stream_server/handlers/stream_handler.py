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
                    logger.debug(
                        f"Выполняем {func.__name__} с аргументами "
                        f"{args}, {kwargs}"
                    )
                    await func(*args, **kwargs)
                    logger.debug(f"✅ {func.__name__} выполнено успешно")
                    return
                except Exception as e:
                    logger.warning(
                        f"⚠️ Ошибка при {func.__name__}, "
                        f"попытка {attempt + 1}: {e}"
                    )
                    await asyncio.sleep(1)

    async def stop_ffmpeg(self):
        """Останавливает текущий процесс FFmpeg, если он запущен."""
        if self._ffmpeg_process:
            logger.info("⏹ Останавливаем текущий поток FFmpeg...")

            try:
                self._ffmpeg_process.terminate()
                logger.debug("📤 SIGTERM отправлен FFmpeg")

                try:
                    await asyncio.wait_for(
                        self._ffmpeg_process.wait(),
                        timeout=5
                    )
                    logger.info(
                        f"✅ FFmpeg завершился, код: "
                        f"{self._ffmpeg_process.returncode}, "
                        f"PID: {self._ffmpeg_process.pid}"
                    )
                except asyncio.TimeoutError:
                    logger.warning(
                        "⚠️ FFmpeg не завершился вовремя, "
                        "принудительное завершение."
                    )
                    self._ffmpeg_process.kill()
                    logger.debug("💀 Отправили kill()")

                    try:
                        await asyncio.wait_for(
                            self._ffmpeg_process.wait(),
                            timeout=5
                        )
                        logger.info(
                            f"✅ FFmpeg принудительно завершён, код: "
                            f"{self._ffmpeg_process.returncode}"
                        )
                    except asyncio.TimeoutError:
                        logger.error(
                            "❌ FFmpeg не завершился даже после kill() — "
                            "залипший процесс!"
                        )

            except ProcessLookupError:
                logger.warning("⚠️ FFmpeg уже завершился (ProcessLookupError)")
            except Exception as e:
                logger.exception(f"❌ Ошибка при остановке FFmpeg: {e}")
            finally:
                self._ffmpeg_process = None

    async def start_ffmpeg_stream(self, yandex_url: str):
        """Запускает потоковую передачу через FFmpeg."""
        await self.stop_ffmpeg()  # Останавливаем старый процесс

        logger.info(f"🎥 Запуск потоковой передачи с {yandex_url}")

        self._ffmpeg_process = await asyncio.create_subprocess_exec(
            "ffmpeg", "-re",  # Читаем файл с реальной скоростью
            "-i", yandex_url,  # Прямая передача ссылки
            "-acodec", "libmp3lame", "-b:a", "320k", "-f", "mp3", "pipe:1",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        logger.info(f"🎥 Запущен процесс FFmpeg с PID: {self._ffmpeg_process.pid}")

    async def stream_audio(self):
        if not self._ffmpeg_process:
            raise HTTPException(status_code=404, detail="Поток не запущен")

        async def generate():
            try:
                while True:
                    chunk = await self._ffmpeg_process.stdout.read(4096)
                    if not chunk:
                        break
                    yield chunk
            except asyncio.CancelledError:
                logger.info("🔌 Клиент отключился от стрима")
                await self.stop_ffmpeg()
                raise
            except Exception as e:
                logger.warning(f"⚠️ Ошибка в генераторе потока: {e}")

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
