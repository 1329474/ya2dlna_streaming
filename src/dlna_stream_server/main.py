from logging import getLogger

import uvicorn
from fastapi import FastAPI

from core.config.settings import settings
from core.logging.setup import setup_logging  # noqa: F401
from dlna_stream_server.endpoints.routers import main_router

logger = getLogger(__name__)

app = FastAPI()

app.include_router(main_router)


def main():
    logger.info("▶️ Запуск dlna стримингового сервера...")
    uvicorn.run(
        app,
        host=settings.local_server_host,
        port=settings.local_server_port_dlna,
    )


if __name__ == "__main__":
    main()
