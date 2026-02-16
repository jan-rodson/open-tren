"""Script para actualizar el GTFS estático de Renfe."""

import asyncio
import logging
import zipfile
from datetime import datetime
from pathlib import Path

from src.config import DEFAULT_USER_AGENT, GTFS_DIR
from src.fetchers import FetcherError, GtfsStaticFetcher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def save_gtfs(content: bytes, timestamp: datetime, output_dir: Path = GTFS_DIR) -> Path:
    """Guarda y extrae el GTFS estático."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Guardar con timestamp en el nombre
    zip_path = output_dir / f"google_transit_{timestamp.strftime('%Y%m%d_%H%M%S')}.zip"
    zip_path.write_bytes(content)

    # Extraer
    extract_dir = output_dir / "renfe_av_ld_md"
    extract_dir.mkdir(exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_dir)

    # Crear symlink al último (absoluto para portabilidad)
    latest_link = output_dir / "latest.zip"
    if latest_link.exists() or latest_link.is_symlink():
        latest_link.unlink()
    latest_link.symlink_to(zip_path)

    return extract_dir


async def main() -> None:
    """Función principal."""
    try:
        async with GtfsStaticFetcher(user_agent=DEFAULT_USER_AGENT) as fetcher:
            result = await fetcher.fetch()
            extract_dir = save_gtfs(result.data, result.timestamp)
            logger.info("GTFS actualizado: %s", extract_dir)
    except FetcherError as e:
        logger.error("Error al actualizar GTFS: %s", e)
        raise


if __name__ == "__main__":
    asyncio.run(main())
