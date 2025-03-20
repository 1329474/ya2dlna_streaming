import logging


from yandex_music import ClientAsync

logger = logging.getLogger(__name__)


class YandexMusicAPI:
    """Класс для работы с API Яндекс.Музыки"""

    _client: ClientAsync

    def __init__(self, client: ClientAsync):
        self._client = client

    async def get_file_info(
        self,
        track_id: int,
        quality: str = None,
        codecs: str = None,
    ):
        """Получение информации о треке"""
        track = await self._client.tracks(track_id)
        if not track:
            return None

        # Получаем информацию для скачивания с прямыми ссылками
        download_info = await track[0].get_download_info_async(
            get_direct_links=True
        )
        logger.info(f"🔍 Получены ссылки для скачивания: {download_info}")
        if not download_info:
            return None

        # Выбираем нужное качество, если указано
        if quality:
            quality = int(quality)  # преобразуем строку в число
            logger.info(f"🔍 Ищем ссылку на {quality} качество")
            for info in download_info:
                logger.info(
                    f"🔍 Проверяем ссылку: {info.codec} {info.bitrate_in_kbps}"
                )
                if info.codec == codecs and info.bitrate_in_kbps == quality:
                    logger.info(
                        f"🔍 Найдена ссылка на {quality} "
                        f"качество: {info.direct_link}"
                    )
                    return info.direct_link
        logger.info(
            f"🔍 Возвращаем ссылку на максимальное качество: "
            f"{download_info[-1].direct_link}"
        )
        return download_info[-1].direct_link
