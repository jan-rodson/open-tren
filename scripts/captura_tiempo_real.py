"""Script para capturar datos de tiempo real de Renfe."""

import asyncio
import logging

from src.config import RAW_DATA_DIR
from src.fetchers import FetcherError, GtfsRtFetcher
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
        async with GtfsRtFetcher() as fetcher:
            result = await fetcher.fetch()
            file_path = save_snapshot(result.data, result.timestamp, "tiempo_real", RAW_DATA_DIR)
            logger.info("Snapshot guardado: %s", file_path)
    except FetcherError as e:
        logger.error("Error al capturar: %s", e)
        raise


if __name__ == "__main__":
    asyncio.run(main())
