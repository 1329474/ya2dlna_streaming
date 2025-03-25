import asyncio
import json
import logging
import ssl
import time
import uuid
from collections import deque

import aiohttp
from injector import inject

from core.authorization.yandex_tokens import get_device_token
from yandex_station.mdns_device_finder import DeviceFinder

logger = logging.getLogger(__name__)


class YandexStationClient:
    """Класс для управления Yandex Station через WebSocket."""

    @inject
    def __init__(
        self,
        device_finder: DeviceFinder,
        device_token: str = None,
        buffer_size: int = 10,
    ):
        self.device_finder = device_finder
        self.device_token = device_token
        self.queue = deque(maxlen=buffer_size)  # Очередь для сообщений станции
        self.waiters: dict[str, asyncio.Future] = {}
        self.lock = asyncio.Lock()
        self.session: aiohttp.ClientSession = None
        self.websocket: aiohttp.ClientWebSocketResponse = None
        self.command_queue = asyncio.Queue()
        self.authenticated = False
        self.device_token = None
        self.running = True
        self.reconnect_required = False
        self.tasks = []  # Хранение фоновых задач

        self.device_finder.find_devices()  # Поиск устройств Yandex в сети
        self.device_id = self.device_finder.device["device_id"]
        self.platform = self.device_finder.device["platform"]
        self.uri = (
            f"wss://{self.device_finder.device['host']}:"
            f"{self.device_finder.device['port']}"
        )

    async def connect(self):
        """Подключение к WebSocket станции."""
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        while True:
            self.reconnect_required = False
            self.running = True

            try:
                if not self.device_token:
                    self.device_token = await get_device_token(
                        self.device_id, self.platform
                    )

                if self.websocket is not None and not self.websocket.closed:
                    logger.warning(
                        "⚠️ Обнаружено старое WebSocket-соединение, закрываем."
                    )
                    await self.close()

                if self.session:
                    logger.info(
                        "🔄 Обнаружена существующая HTTP-сессия, закрываем..."
                    )
                    await self.session.close()
                    self.session = None

                async with aiohttp.ClientSession() as session:
                    self.session = session
                    logger.info(f"🔄 Подключение к станции: {self.uri}")
                    self.websocket = await session.ws_connect(
                        self.uri,
                        ssl=ssl_context,
                        timeout=aiohttp.ClientWSTimeout(ws_close=10),
                    )
                    logger.info(
                        "✅ Подключение к WebSocket станции установлено"
                    )

                    await self._cancel_tasks()
                    stream_status_task = asyncio.create_task(
                        self.stream_station_messages()
                    )
                    command_producer_task = asyncio.create_task(
                        self.command_producer_handler()
                    )
                    keep_alive_ws_task = asyncio.create_task(
                        self.keep_alive_ws_connection()
                    )

                    self.tasks = [
                        stream_status_task,
                        command_producer_task,
                        keep_alive_ws_task,
                    ]

                    auth_success = await self.authenticate()
                    if not auth_success:
                        logger.warning(
                            "❌ Ошибка авторизации! Требуется новый токен."
                        )
                        await self.refresh_token()
                        continue  # Попробуем снова

                    results = await asyncio.gather(
                        *self.tasks, return_exceptions=True
                    )
                    for i, result in enumerate(results):
                        if isinstance(result, Exception):
                            logger.error(
                                f"Задача {i} завершилась с ошибкой: {result}"
                            )

            except aiohttp.ClientError as e:
                logger.error(f"❌ WebSocket ошибка: {e}")

            finally:
                await self._cancel_tasks()

                if not self.running and not self.reconnect_required:
                    logger.info(
                        "🛑 WebSocket-клиент завершает работу — "
                        "переподключение не требуется"
                    )
                    break

                logger.info("🔄 Переподключение через 5 секунд...")
                await asyncio.sleep(5)

    async def keep_alive_ws_connection(self):
        """Поддерживает соединение с WebSocket."""
        while self.running:
            try:
                response = await self.send_command({"command": "ping"})
                if response.get("error") == "Timeout":
                    logger.warning(
                        "❌ Ping timeout. Инициируем переподключение."
                    )
                    self.reconnect_required = True
                    self.running = False
                    await self._cancel_tasks()
            except Exception as e:
                logger.error(f"❌ Ошибка при отправке пинга: {e}")
            await asyncio.sleep(10)

    async def authenticate(self) -> bool:
        """Отправляет пинг и ожидает ответа для подтверждения авторизации."""
        try:
            response = await self.send_command({"command": "ping"})

            if response.get("requestId"):
                logger.info(
                    f"🔑 Авторизация успешна: {response.get('requestId')}"
                )

            if response.get("error") == "Timeout":
                raise asyncio.TimeoutError("Timeout")

            self.authenticated = True
            return True

        except asyncio.TimeoutError:
            logger.warning(
                "❌ WebSocket не ответил на ping! Вероятно, ошибка авторизации."
            )
            return False
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке авторизации: {e}")
            return False

    async def refresh_token(self):
        """Запрашивает новый токен и перезапускает WebSocket."""
        logger.info("🔄 Запрос нового токена...")
        # Здесь вызываем функцию обновления токена
        self.device_token = await get_device_token(
            self.device_id, self.platform
        )
        logger.info("✅ Новый токен получен. Переподключение...")
        await asyncio.sleep(1)

    async def stream_station_messages(self):
        """Постоянный поток сообщений от станции."""
        async for message in self.websocket:
            data = json.loads(message.data)
            self.queue.append(data)

            # Если это ответ на команду, передаём в `Future`
            request_id = data.get("requestId", None)
            if request_id and request_id in self.waiters:
                self.waiters[request_id].set_result(data)
                del self.waiters[request_id]

    async def command_producer_handler(self):
        """Обрабатывает команды из очереди и отправляет их на станцию."""
        while self.running:
            command = await self.command_queue.get()

            #  Блокировка гарантирует,
            #  что команды отправляются последовательно
            async with self.lock:
                if not self.websocket or self.websocket.closed:
                    logger.warning("❌ WebSocket закрыт, команда удалена")
                    continue  # Пропускаем команду, не отправляя её

            await self.websocket.send_json(command)
            logger.info(f"✅ Команда отправлена на станцию: {command}")

    async def send_command(self, command: dict) -> dict:
        """Отправляет команды в очередь для отправки на станцию
        и ожидает именованный uuid ответ от станции на команду.
        """
        request_id = str(uuid.uuid4())
        future = asyncio.get_event_loop().create_future()
        self.waiters[request_id] = future

        command_payload = {
            "conversationToken": self.device_token,
            "id": request_id,
            "payload": command,
            "sentTime": int(round(time.time() * 1000)),
        }

        await self.command_queue.put(command_payload)
        logger.info(f"✅ Команда {request_id} добавлена в очередь")

        try:
            response = await asyncio.wait_for(future, timeout=10)
            logger.info(f"✅ Ответ на команду {request_id} получен")
            return response
        except asyncio.TimeoutError:
            logger.error(
                f"❌ Timeout при ожидании ответа на команду {request_id}"
            )
            return {"error": "Timeout"}
        finally:
            self.waiters.pop(request_id, None)  # Чистим Future после обработки

    async def get_latest_message(self):
        """Возвращает самое последнее сообщение из очереди или None,
        если очередь пуста.
        """
        return self.queue[-1] if self.queue else None

    async def _cancel_tasks(self):
        """Отмена всех активных задач, чтобы избежать зависших WebSocket."""

        if not self.tasks:
            logger.info("🛑 Нет активных фоновых задач для отмены")
            return

        logger.info("🛑 Отмена всех фоновых задач...")
        tasks_to_cancel = [task for task in self.tasks if not task.done()]

        for task in tasks_to_cancel:
            task.cancel()

        await asyncio.gather(*tasks_to_cancel, return_exceptions=True)

        self.tasks.clear()
        logger.info("✅ Все фоновые задачи успешно отменены")

    async def close(self):
        """Закрытие WebSocket-соединения и фоновых задач."""
        self.running = False

        # Очищаем очередь команд, чтобы не отправлять их в закрытый WebSocket
        while not self.command_queue.empty():
            self.command_queue.get_nowait()
            self.command_queue.task_done()

        # Отмена всех фоновых задач
        await self._cancel_tasks()

        if self.websocket:
            try:
                logger.info("🔄 Закрытие WebSocket-соединения...")
                await self.websocket.close()
                logger.info("✅ WebSocket-соединение закрыто")
            except Exception as e:
                logger.error(f"❌ Ошибка при закрытии WebSocket: {e}")
            finally:
                self.websocket = None

        if self.session:
            try:
                logger.info("🔄 Закрытие HTTP-сессии...")
                await self.session.close()
                logger.info("✅ HTTP-сессия закрыта")
            except Exception as e:
                logger.error(f"❌ Ошибка при закрытии HTTP-сессии: {e}")
            finally:
                self.session = None
