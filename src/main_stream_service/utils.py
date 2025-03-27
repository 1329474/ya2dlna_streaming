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


async def parse_seconds_to_time(seconds: int | float) -> str:
    """Преобразует секунды в строку времени: 188 -> '00:03:08'"""
    try:
        if seconds is None or not isinstance(seconds, (int, float)) or seconds < 0:
            raise ValueError(f"Некорректное значение секунд: {seconds}")
        seconds = int(seconds)
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}"
    except Exception as e:
        logger.warning(f"⚠️ Не удалось распарсить секунды '{seconds}': {e}")
        return "00:00:00"
