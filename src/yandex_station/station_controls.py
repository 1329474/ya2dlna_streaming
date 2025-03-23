import asyncio
from logging import getLogger

from injector import inject

from yandex_station.constants import ALICE_ACTIVE_STATES
from yandex_station.models import Track
from yandex_station.station_ws_control import YandexStationClient

logger = getLogger(__name__)


class YandexStationControls:
    """Класс управления станцией через WebSocket"""

    _ws_client: YandexStationClient
    _volume: float
    _ws_task: asyncio.Task | None

    @inject
    def __init__(self, ws_client: YandexStationClient):
        self._ws_client = ws_client
        self._volume = 0
        self._ws_task = None

    async def start_ws_client(self):
        """Запуск WebSocket-клиента"""
        if self._ws_task and not self._ws_task.done():
            logger.warning("‼ WebSocket-клиент уже запущен")
            return

        logger.info("🔄 Запуск WebSocket-клиента")
        self._ws_task = asyncio.create_task(self._ws_client.connect())

    async def stop_ws_client(self):
        """Остановка WebSocket-клиента"""
        if not self._ws_task and not self._ws_client.running:
            logger.info("⚠️ WebSocket-клиент уже полностью остановлен")
            return

        logger.info("🔄 Остановка WebSocket-клиента")

        ws_task = self._ws_task
        self._ws_task = None
        await self._ws_client.close()
        if ws_task:
            ws_task.cancel()
            try:
                await ws_task
            except asyncio.CancelledError:
                logger.info("✅ WebSocket-клиент успешно остановлен")
            except Exception as e:
                logger.error(f"❌ Ошибка при остановке WebSocket-клиента: {e}")

    async def send_text(self, text: str):
        """Отправка текстового сообщения"""
        logger.info(f"🔊 Отправка текстового сообщения: {text}")
        try:
            await self._ws_client.send_command(
                {"command": "sendText", "text": text}
            )
        except Exception as e:
            logger.error(f"❌ Ошибка при отправке текстового сообщения: {e}")

    async def get_current_state(self):
        """Получение текущего состояния станции"""
        try:
            state = await self._ws_client.get_latest_message()
            # logger.info(f"🎵 Состояние станции: {state}")
            if state:
                return state.get("state", {})
            else:
                return None
        except Exception as e:
            logger.error(
                f"❌ Ошибка при получении текущего состояния станции: {e}"
            )

    async def get_alice_state(self):
        """Получение состояния Алиса"""
        try:
            state = await self._ws_client.get_latest_message()
            if state:
                return state.get("state", {}).get("aliceState", {})
        except Exception as e:
            logger.error(f"❌ Ошибка при получении состояния Алиса: {e}")
            return None

    async def get_player_status(self) -> bool:
        """Получение статуса плеера"""
        try:
            state = await self.get_current_state()
            play_status = state.get("playing", {})
            player_state = state.get("playerState", {})
            player_state["playing"] = play_status
            return player_state
        except Exception as e:
            logger.error(f"❌ Ошибка при получении статуса плеера: {e}")
            return False

    async def get_current_track(self) -> Track | None:
        """Получение текущего трека"""
        try:
            player_state = await self.get_player_status()
            # logger.info(f"🎵 Состояние плеера: {player_state}")
            if player_state:
                return Track(
                    id=player_state.get("id", 0),
                    title=player_state.get("title", ""),
                    artist=player_state.get("subtitle", ""),
                    duration=player_state.get("duration", 0),
                    progress=player_state.get("progress", 0),
                    playing=player_state.get("playing", False),
                )
            else:
                return None
        except Exception as e:
            logger.error(f"❌ Ошибка при получении текущего трека: {e}")

    async def get_volume(self):
        """Получение текущего уровня громкости"""
        try:
            state = await self._ws_client.get_latest_message()
            if state:
                logger.info(
                    f"🔊 Получение текущего уровня громкости Алиcы: {state.get('state', {}).get('volume', {})}"
                )
                return state.get("state", {}).get("volume", {})
        except Exception as e:
            logger.error(f"❌ Ошибка при получении громкости: {e}")
            return None

    async def set_default_volume(self):
        """Установка громкости по умолчанию"""
        logger.info("🔊 Установка громкости по умолчанию")
        try:
            self._volume = await self.get_volume()
            logger.info(f"Громкость по умолчанию: {self._volume}")
        except Exception as e:
            logger.error(f"❌ Ошибка при установке громкости по умолчанию: {e}")

    async def set_volume(self, volume: float):
        """Установка уровня громкости"""
        logger.info(f"🔊 Установка громкости на {volume}")
        try:
            await self._ws_client.send_command(
                {
                    "command": "setVolume",
                    "volume": volume,
                }
            )
        except Exception as e:
            logger.error(f"❌ Ошибка при установке громкости: {e}")

    async def mute(self):
        """Безопасное выключение звука — только если Алиса молчит"""
        state = await self.get_alice_state()
        if state not in ALICE_ACTIVE_STATES:
            await self._ws_client.send_command({"command": "setVolume", "volume": 0})
            logger.info("🔇 Станция замьючена безопасно")
        else:
            logger.info(f"🚫 Пропускаем mute — Алиса уже говорит ({state})")

    async def unmute(self):
        """Включение громкости"""
        logger.info("🔊 Включение громкости")
        try:
            await self._ws_client.send_command(
                {
                    "command": "setVolume",
                    "volume": self._volume,
                }
            )
        except Exception as e:
            logger.error(f"❌ Ошибка при включении громкости: {e}")
