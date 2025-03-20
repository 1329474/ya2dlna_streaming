import ipaddress
from logging import getLogger
from time import sleep

from zeroconf import (ServiceBrowser, ServiceListener, ServiceStateChange,
                      Zeroconf)

logger = getLogger(__name__)


class DeviceFinder(ServiceListener):
    """Класс для поиска устройств Yandex Station в сети."""

    def __init__(self):
        self.device = {}
        self.zeroconf = Zeroconf()

    def find_devices(self):
        """Поиск устройств Yandex Station в сети."""
        self.browser = ServiceBrowser(
            zc=self.zeroconf,
            type_="_yandexio._tcp.local.",
            handlers=[self._handler_device]
        )
        sleep(1)

    def _handler_device(
            self,
            zeroconf: Zeroconf,
            service_type: str,
            name: str,
            state_change: ServiceStateChange
    ) -> None:
        """Обработчик событий для устройств Yandex Station."""
        try:
            info = zeroconf.get_service_info(service_type, name)
            properties = {
                a.decode(): v.decode() for a, v in info.properties.items()
            }
            logger.info(f"Properties: {properties}")

            self.device = {
                "device_id": properties["deviceId"],
                "platform": properties["platform"],
                "host": str(ipaddress.ip_address(info.addresses[0])),
                "port": info.port,
            }
            logger.info(f"Найдены устройства: {self.device}")

        except Exception as e:
            logger.error(f"Error: {e}")

    def close(self):
        """Закрытие zeroconf."""
        self.zeroconf.close()
