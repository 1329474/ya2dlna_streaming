import sys
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфигурация приложения"""

    def resolve_env_path():
        """Определяет путь к файлу .env"""
        cwd_env = Path.cwd() / ".env"
        if cwd_env.exists():
            return cwd_env
        elif getattr(sys, "frozen", False):
            return Path(sys.executable).parent / ".env"
        else:
            return Path(__file__).resolve().parent / ".env"

    model_config = SettingsConfigDict(
        env_file=resolve_env_path(),
        env_prefix="APP_",
        extra="ignore",
    )

    # Yandex Music settings
    ya_music_token: str

    # API server settings
    local_server_host: str
    local_server_port_dlna: int
    local_server_port_api: int

    # Ruark R5 settings
    ruark_pin: str


settings = Settings()
