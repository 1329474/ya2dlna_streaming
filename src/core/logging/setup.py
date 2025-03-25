import logging
import os
from logging.config import dictConfig

# Определяем путь к каталогу logs и создаем его, если он не существует
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)


def setup_logging():
    """Настройка логирования"""
    logging_config = {
        "version": 1,
        "disable_existing_loggers": True,
        "formatters": {
            "default": {
                "format": (
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            },
            "detailed": {
                "format": (
                    "%(asctime)s - %(name)s - %(levelname)s - "
                    "%(message)s\n%(exc_info)s"
                )
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "detailed",
                "level": "INFO"
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": os.path.join(LOG_DIR, "app.log"),
                "formatter": "detailed",
                "level": "INFO",
                "maxBytes": 5 * 1024 * 1024,
                "backupCount": 3
            }
        },
        "root": {
            "handlers": ["console", "file"],
            "level": "INFO"
        },
        "loggers": {
            "ruark_audio_system": {
                "handlers": ["console", "file"],
                "level": "DEBUG",
                "propagate": False
            }
        }
    }
    dictConfig(logging_config)


if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        1 / 0
    except Exception as e:
        logger.error(f"Ошибка в коде! {e}", exc_info=True)
