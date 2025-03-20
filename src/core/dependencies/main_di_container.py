from injector import Injector, Module

from core.dependencies.di_modules import (DeviceFinderModule,
                                          MainStreamManagerModule,
                                          RuarkR5ControllerModule,
                                          StreamHandlerModule,
                                          YandexMusicAPIModule,
                                          YandexStationClientModule,
                                          YandexStationControlsModule)


class MainDIContainer:
    """Контейнер со всеми зависимостями (Singleton)"""

    _instance = None
    _container: Injector = None  # DI-контейнер

    BASE_MODULES = [
        YandexStationClientModule,
        YandexStationControlsModule,
        RuarkR5ControllerModule,
        YandexMusicAPIModule,
        MainStreamManagerModule,
        StreamHandlerModule,
        DeviceFinderModule
    ]

    def __new__(cls, additional_modules: list[Module] = None):
        """Гарантирует, что контейнер создаётся один раз"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)

            # Объединяем базовые и дополнительные модули
            modules = cls.BASE_MODULES.copy()
            if additional_modules:
                modules.extend(additional_modules)

            cls._instance._container = Injector(modules)  # ✅ Создаём контейнер

        return cls._instance

    def get_container(self) -> Injector:
        """Возвращает общий DI-контейнер"""
        return self._container
