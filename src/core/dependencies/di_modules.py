from injector import Module, provider, singleton
from yandex_music import ClientAsync

from core.config.settings import settings
from dlna_stream_server.handlers.stream_handler import StreamHandler
from main_stream_service.main_stream_manager import MainStreamManager
from main_stream_service.yandex_music_api import YandexMusicAPI
from ruark_audio_system.ruark_r5_controller import RuarkR5Controller
from yandex_station.mdns_device_finder import DeviceFinder
from yandex_station.station_controls import YandexStationControls
from yandex_station.station_ws_control import YandexStationClient


class MainStreamManagerModule(Module):
    """Класс для управления зависимостями MainStreamManager"""
    @singleton
    @provider
    def provide_main_stream_manager(
        self,
        station_ws_client: YandexStationClient,
        station_controls: YandexStationControls,
        ruark_controls: RuarkR5Controller,
        yandex_music_api: YandexMusicAPI
    ) -> MainStreamManager:
        return MainStreamManager(
            station_ws_client=station_ws_client,
            station_controls=station_controls,
            ruark_controls=ruark_controls,
            yandex_music_api=yandex_music_api
        )


class DeviceFinderModule(Module):
    """Класс для управления зависимостями DeviceFinder"""
    @singleton
    @provider
    def provide_device_finder(self) -> DeviceFinder:
        return DeviceFinder()


class YandexStationClientModule(Module):
    """Класс для управления зависимостями Yandex Station Client"""
    @singleton
    @provider
    def provide_yandex_station_client(self) -> YandexStationClient:
        return YandexStationClient(device_finder=DeviceFinder())


class YandexStationControlsModule(Module):
    """Класс для управления зависимостями Yandex Station Controls"""
    @singleton
    @provider
    def provide_yandex_station_controls(
        self, ws_client: YandexStationClient
    ) -> YandexStationControls:
        return YandexStationControls(ws_client)


class YandexMusicAPIModule(Module):
    """Класс для управления зависимостями Yandex Music API"""
    @singleton
    @provider
    def provide_yandex_music_api(self) -> YandexMusicAPI:
        client = ClientAsync(settings.ya_music_token)
        return YandexMusicAPI(client=client)


class RuarkR5ControllerModule(Module):
    """Класс для управления зависимостями RuarkR5Controller"""
    @singleton
    @provider
    def provide_ruark_r5_controller(self) -> RuarkR5Controller:
        return RuarkR5Controller()


class StreamHandlerModule(Module):
    """Класс для управления зависимостями StreamHandler"""
    @singleton
    @provider
    def provide_stream_handler(
        self, ruark_controls: RuarkR5Controller
    ) -> StreamHandler:
        return StreamHandler(ruark_controls)
