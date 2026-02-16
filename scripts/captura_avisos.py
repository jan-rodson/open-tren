"""Script para capturar avisos e incidencias de Renfe."""

import asyncio
import logging

from src.config import DEFAULT_USER_AGENT, RAW_DATA_DIR
from src.fetchers import AvisosFetcher, FetcherError
from src.storage import save_snapshot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Función principal."""
    try:
        async with AvisosFetcher(user_agent=DEFAULT_USER_AGENT) as fetcher:
            result = await fetcher.fetch()
            file_path = save_snapshot(result.data, result.timestamp, "avisos", RAW_DATA_DIR)
            logger.info("Avisos guardados: %s", file_path)
    except FetcherError as e:
        logger.error("Error al capturar avisos: %s", e)
        raise


if __name__ == "__main__":
    asyncio.run(main())
