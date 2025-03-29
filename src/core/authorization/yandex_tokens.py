import logging

import aiohttp

from core.config.settings import settings

logger = logging.getLogger(__name__)


async def get_device_token(device_id: str, platform: str) -> str:
    url = "https://quasar.yandex.net/glagol/token"
    params = {"device_id": device_id, "platform": platform}

    headers = {
        "Authorization": f"OAuth {settings.ya_music_token}",
        "Content-Type": "application/json"
    }

    async with aiohttp.ClientSession() as session:

        try:
            async with session.get(
                url, headers=headers, params=params
            ) as response:
                response_data = await response.json()
                if (response_data.get("status") == "ok" and
                        "token" in response_data):
                    token = response_data["token"]
                    logger.info("✅ Токен успешно получен")
                    return token
                else:
                    logger.error(
                        f"❌ Ошибка получения токена: {response_data}"
                    )
                    return None
        except Exception as e:
            logger.error(f"❌ Ошибка получения токена: {e}")
            return None
