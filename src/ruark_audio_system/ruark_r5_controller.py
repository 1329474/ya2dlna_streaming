import asyncio
import re
import urllib.parse
from logging import getLogger
from typing import Any, Dict, List, Literal, Optional

import aiohttp
import upnpclient

from core.config.settings import settings

SESSION_ID_REGEX = re.compile(r"<sessionId>(.*?)</sessionId>")
POWER_STATUS_REGEX = re.compile(r"<value><u8>(.*?)</u8></value>")

logger = getLogger(__name__)

PlayModeType = Literal["NORMAL", "SHUFFLE", "REPEAT_ALL"]
SeekUnitType = Literal["REL_TIME", "ABS_TIME", "ABS_COUNT", "TRACK_NR"]


class RuarkR5Controller:
    """Класс для управления устройством Ruark R5"""

    _session_id: str

    def __init__(self, device_name: str = "Ruark R5") -> None:
        """Инициализация и поиск устройства Ruark R5 в сети"""
        self.device: Optional[upnpclient.Device] = self.find_device(
            device_name
        )
        if not self.device:
            logger.warning(f"⚠ Устройство '{device_name}' не найдено в сети!")
            return

        self.ip = self.get_device_ip()
        logger.info(f"IP-адрес устройства: {self.ip}")

        # Проверка всех доступных сервисов
        self.services: Dict[str, Any] = {
            service.service_type: service for service in self.device.services
        }

        self.av_transport: Any = self.services.get(
            "urn:schemas-upnp-org:service:AVTransport:1"
        )
        self.connection_manager: Any = self.services.get(
            "urn:schemas-upnp-org:service:ConnectionManager:1"
        )
        self.rendering_control: Any = self.services.get(
            "urn:schemas-upnp-org:service:RenderingControl:1"
        )

        logger.info(
            f"✅ Успешно подключено к {self.device.friendly_name} "
            f"({self.device.location})"
        )
        self.print_available_services()

    def find_device(self, device_name: str) -> Optional[upnpclient.Device]:
        """Находит устройство по имени"""
        logger.info(f"Начинаем поиск устройства: {device_name}")
        try:
            devices = upnpclient.discover()
            logger.info(f"Найдено {len(devices)} устройств")
            logger.info(f"Устройства: {devices}")
            for device in devices:
                try:
                    logger.info(
                        f"Проверяем устройство: {device.friendly_name}"
                    )
                    if device_name in device.friendly_name:
                        logger.info(
                            "Найдено подходящее устройство: "
                            f"{device.friendly_name}"
                        )
                        return device
                except Exception as e:
                    logger.error(
                        "Ошибка при обработке устройства "
                        f"{device}: {str(e)}"
                    )
                    continue
            logger.info(f"Не найдено устройств с именем: {device_name}")
            return None
        except Exception as e:
            logger.error(f"Error during device discovery: {str(e)}")
            return None

    def get_device_ip(self) -> Optional[str]:
        """Получает IP-адрес устройства"""
        if self.device:
            parsed_url = urllib.parse.urlparse(self.device.location)
            return parsed_url.hostname
        return None

    def print_available_services(self):
        """Выводит список всех поддерживаемых сервисов"""
        logger.info("\n📡 Доступные UPnP сервисы:")
        for service in self.services:
            logger.info(f" - {service}")

    #  ConnectionManager
    async def get_protocol_info(self, connection_manager) -> Dict[str, str]:
        """Получение списка поддерживаемых форматов"""
        return await asyncio.to_thread(self.connection_manager.GetProtocolInfo)

    async def get_current_connection_ids(self) -> List[str]:
        """Получение списка активных соединений"""
        return (await asyncio.to_thread(
            self.connection_manager.GetCurrentConnectionIDs
        ))["ConnectionIDs"]

    async def get_current_connection_info(
        self, connection_id: int
    ) -> Dict[str, Any]:
        """Получение информации о соединении"""
        return await asyncio.to_thread(
            self.connection_manager.GetCurrentConnectionInfo,
            ConnectionID=connection_id
        )

    #   AVTransport
    async def set_av_transport_uri(
        self, uri: str, metadata: str = ""
    ) -> None:
        """Установка нового потока"""
        await asyncio.to_thread(
            self.av_transport.SetAVTransportURI,
            InstanceID=0,
            CurrentURI=uri,
            CurrentURIMetaData=metadata
        )
        logger.info(f"🎵 Поток установлен: {uri}")

    async def play(self) -> None:
        """Запуск воспроизведения"""
        await asyncio.to_thread(
            self.av_transport.Play, InstanceID=0, Speed="1"
        )
        logger.info("▶ Воспроизведение запущено")

    async def pause(self) -> None:
        """Приостановка воспроизведения"""
        await asyncio.to_thread(self.av_transport.Pause, InstanceID=0)
        logger.info("⏸ Воспроизведение приостановлено")

    async def stop(self) -> None:
        """Остановка воспроизведения"""
        playing = await self.is_playing()
        if playing:
            await asyncio.to_thread(self.av_transport.Stop, InstanceID=0)
            logger.info("⏹ Воспроизведение остановлено")

    async def next_track(self) -> None:
        """Переключение на следующий трек"""
        await asyncio.to_thread(self.av_transport.Next, InstanceID=0)
        logger.info("⏭ Следующий трек")

    async def previous_track(self) -> None:
        """Переключение на предыдущий трек"""
        await asyncio.to_thread(self.av_transport.Previous, InstanceID=0)
        logger.info("⏮ Предыдущий трек")

    async def seek(self, target: str, unit: SeekUnitType = "REL_TIME") -> None:
        """Перемотка на указанное время (например, '00:01:30')"""
        await asyncio.to_thread(
            self.av_transport.Seek,
            InstanceID=0,
            Unit=unit,
            Target=target
        )
        logger.info(f"⏩ Перемотка на {target}")

    async def get_media_info(self) -> Dict[str, Any]:
        """Получение информации о текущем медиафайле"""
        return await asyncio.to_thread(
            self.av_transport.GetMediaInfo, InstanceID=0
        )

    async def get_position_info(self) -> Dict[str, Any]:
        """Получение информации о текущей позиции воспроизведения"""
        return await asyncio.to_thread(
            self.av_transport.GetPositionInfo, InstanceID=0
        )

    async def get_transport_info(self) -> Dict[str, Any]:
        """Получение информации о состоянии транспорта"""
        return await asyncio.to_thread(
            self.av_transport.GetTransportInfo,
            InstanceID=0
        )

    async def get_transport_settings(self) -> Dict[str, Any]:
        """Получение настроек воспроизведения"""
        return await asyncio.to_thread(
            self.av_transport.GetTransportSettings,
            InstanceID=0
        )

    async def get_current_rel_time(self) -> str:
        """Получение текущего времени в секундах"""
        position_info = await self.get_position_info()
        rel_time = position_info.get("RelTime")
        return rel_time

    async def is_playing(self) -> bool:
        """Проверка, воспроизводится ли что-либо"""
        ruark_state = await self.get_transport_info()
        play_state = ruark_state.get("CurrentTransportState")
        if play_state == "PLAYING":
            return True
        return False

    async def set_play_mode(self, mode: PlayModeType) -> None:
        """Установка режима воспроизведения"""
        await asyncio.to_thread(
            self.av_transport.SetPlayMode,
            InstanceID=0,
            NewPlayMode=mode
        )
        logger.info(f"🔄 Установлен режим воспроизведения: {mode}")

    #   RenderingControl
    async def get_volume(self) -> int:
        """Получение текущего уровня громкости"""
        result = await asyncio.to_thread(
            self.rendering_control.GetVolume,
            InstanceID=0,
            Channel="Master"
        )
        return result["CurrentVolume"]

    async def set_volume(self, volume: int) -> None:
        """Установка громкости (0-100)"""
        await asyncio.to_thread(
            self.rendering_control.SetVolume,
            InstanceID=0,
            Channel="Master",
            DesiredVolume=volume
        )
        logger.info(f"🔊 Громкость установлена на {volume}")

    async def get_mute(self) -> bool:
        """Получение состояния mute"""
        result = await asyncio.to_thread(
            self.rendering_control.GetMute,
            InstanceID=0,
            Channel="Master"
        )
        return bool(result["CurrentMute"])

    async def set_mute(self, mute: bool) -> None:
        """Отключение/включение звука"""
        await asyncio.to_thread(
            self.rendering_control.SetMute,
            InstanceID=0,
            Channel="Master",
            DesiredMute=int(mute)
        )
        logger.info("🔇 Звук отключен" if mute else "🔊 Звук включен")

    async def fade_out_ruark(
            self,
            start_volume: int,
            min_volume: int = 2,
            step: int = 6,
            delay: float = 0.1
    ):
        """Плавное уменьшение громкости Ruark в несколько шагов"""
        volume = start_volume - start_volume % 2

        logger.info(
            f"🔉 Плавное снижение громкости Ruark: "
            f"{volume} ➝ {min_volume} шагом {step}")

        try:
            for v in range(volume, min_volume - 1, -step):
                logger.info(f"  ➤ Устанавливаем громкость: {v}")
                await self.set_volume(v)
                await asyncio.sleep(delay)

            logger.info("✅ Плавное снижение громкости Ruark завершено")

        except Exception as e:
            logger.error(f"❌ Ошибка при снижении громкости Ruark: {e}")

    async def list_presets(self) -> str:
        """Получение списка пресетов"""
        result = await asyncio.to_thread(
            self.rendering_control.ListPresets,
            InstanceID=0
        )
        return result["CurrentPresetNameList"]

    async def select_preset(self, preset_name: str) -> None:
        """Выбор пресета"""
        await asyncio.to_thread(
            self.rendering_control.SelectPreset,
            InstanceID=0,
            PresetName=preset_name
        )
        logger.info(f"🎛 Выбран пресет: {preset_name}")

    async def get_session_id(self) -> str:
        """Получение session_id"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"http://{self.ip}/fsapi/CREATE_SESSION/"
                    f"?pin={settings.ruark_pin}"
                ) as response:
                    content = await response.text()
                    self._session_id = (
                        SESSION_ID_REGEX.search(content).group(1)
                    )
                    return self._session_id
        except Exception as e:
            logger.error(f"Ошибка при получении session_id: {e}")
            return ""

    async def get_power_status(self) -> str:
        """Получение статуса питания"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"http://{self.ip}/fsapi/GET/"
                    f"netRemote.sys.power?pin={settings.ruark_pin}"
                    f"&sid={self._session_id}"
                ) as response:
                    content = await response.text()
                    status = POWER_STATUS_REGEX.search(content).group(1)
                    logger.info(f"🔌 Статус питания: {status}")
                    return status
        except Exception as e:
            logger.error(f"Ошибка при получении статуса питания: {e}")
            return ""

    async def turn_power_on(self) -> str:
        """Включение питания"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"http://{self.ip}/fsapi/SET/"
                    f"netRemote.sys.power?pin={settings.ruark_pin}"
                    f"&sid={self._session_id}&value=1"
                ) as response:
                    if response.status == 200:
                        status = await self.get_power_status()
                        if status == "1":
                            logger.info("🔌 Питание включено")
                            return True
        except Exception as e:
            logger.error(f"Ошибка при включении питания: {e}")
            return False

    async def turn_power_off(self) -> str:
        """Выключение питания"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"http://{self.ip}/fsapi/SET/"
                    f"netRemote.sys.power?pin={settings.ruark_pin}"
                    f"&sid={self._session_id}&value=0"
                ) as response:
                    if response.status == 200:
                        status = await self.get_power_status()
                        if status == "0":
                            logger.info("🔌 Питание выключено")
                            return True

        except Exception as e:
            logger.error(f"Ошибка при выключении питания: {e}")
            return False

    async def print_status(self) -> None:
        """Вывод текущего состояния устройства"""
        logger.info("🎶 Текущее состояние Ruark R5:")
        volume = await self.get_volume()
        mute = await self.get_mute()
        media_info = await self.get_media_info()
        position_info = await self.get_position_info()
        transport_info = await self.get_transport_info()

        logger.info(f"🔊 Громкость: {volume}")
        logger.info(f"🔇 Mute: {mute}")
        logger.info(f"📀 Медиа: {media_info}")
        logger.info(f"⏱ Позиция: {position_info}")
        logger.info(f"🚀 Транспорт: {transport_info}")
