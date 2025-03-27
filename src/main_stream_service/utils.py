import logging

logger = logging.getLogger(__name__)


async def parse_time_to_seconds(time_str: str) -> int:
    """Преобразует строку времени в секунды: '00:03:08' -> 188"""
    try:
        h, m, s = map(int, time_str.split(":"))
        return h * 3600 + m * 60 + s
    except Exception as e:
        logger.warning(f"⚠️ Не удалось распарсить время '{time_str}': {e}")
        return 0
