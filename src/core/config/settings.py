from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфигурация приложения"""

    model_config = SettingsConfigDict(
        env_file=".env",
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
