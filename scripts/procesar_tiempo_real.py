"""Script para procesar GTFS-RT de Renfe (descargar o desde snapshot) e insertar en BD."""

import argparse
import asyncio
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.config import DEFAULT_USER_AGENT, RAW_DATA_DIR
from src.fetchers import FetcherError, GtfsRtFetcher
from src.models import Actualizacion
from src.processors.gtfs_rt import GtfsRtLoader
from src.storage import save_snapshot
from src.storage.database import Database
from src.storage.repositories import CirculacionRepository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def _procesar_dict(rt_data: dict[str, Any]) -> list[Actualizacion]:
    """Procesa dict directamente (para datos de API sin guardar en disco).

    Args:
        rt_data: Diccionario con el feed GTFS-RT.

    Returns:
        Lista de Actualizacion con los delays de cada viaje.
    """
    entidades = rt_data.get("entity", [])
    actualizaciones: list[Actualizacion] = []

    for entidad in entidades:
        trip_update = entidad.get("tripUpdate")
        if not trip_update:
            continue

        trip = trip_update.get("trip", {})
        if not trip:
            continue

        trip_id = trip.get("tripId")
        if not trip_id:
            continue

        delay = trip_update.get("delay", 0)
        schedule_relationship = trip.get("scheduleRelationship", "SCHEDULED")

        actualizaciones.append(
            Actualizacion(
                trip_id=trip_id,
                delay_segundos=delay,
                schedule_relationship=schedule_relationship,
            )
        )

    logger.info(f"Procesadas {len(actualizaciones)} actualizaciones de {len(entidades)} entidades")
    return actualizaciones


async def procesar_y_cargar(
    rt_data: dict[str, Any] | None = None,
    rt_path: Path | None = None,
    db: Database | None = None,
) -> int:
    """Procesa datos RT y actualiza delays en BD."""
    if rt_path:
        parser = GtfsRtLoader(rt_path)
        trip_updates = parser.cargar_actualizaciones()
    elif rt_data:
        trip_updates = _procesar_dict(rt_data)
    else:
        raise ValueError("Debe proporcionar rt_data o rt_path")

    logger.info("Parseadas %d actualizaciones de GTFS-RT", len(trip_updates))

    if db is None:
        logger.info("Modo --no-insert: sin inserción en BD")
        return len(trip_updates)

    repo_circulaciones = CirculacionRepository(db)
    count = await repo_circulaciones.actualizar_batch_delays(trip_updates)
    logger.info("Actualizados %d delays en BD", count)
    return count


async def main() -> None:
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="Procesa GTFS-RT de Renfe (API o snapshot) e inserta en BD"
    )
    parser.add_argument(
        "--snapshot",
        type=str,
        help="Path a JSON local en vez de descargar de API",
    )
    parser.add_argument(
        "--no-insert",
        action="store_true",
        help="Solo descargar/procesar, sin insertar en BD",
    )
    args = parser.parse_args()

    snapshot_path: Path | None = None

    if args.snapshot:
        snapshot_path = Path(args.snapshot)
        if not snapshot_path.exists():
            raise FileNotFoundError(f"Snapshot no encontrado: {snapshot_path}")

        logger.info("Leyendo snapshot: %s", snapshot_path)
        with open(snapshot_path) as f:
            rt_data = json.load(f)
        timestamp_captura = datetime.fromtimestamp(snapshot_path.stat().st_mtime, tz=UTC)
    else:
        try:
            async with GtfsRtFetcher(user_agent=DEFAULT_USER_AGENT) as fetcher:
                result = await fetcher.fetch()
                logger.info("GTFS-RT descargado de API: %s bytes", len(result.data))
                rt_data = result.data
                timestamp_captura = result.timestamp
                save_snapshot(rt_data, timestamp_captura, "tiempo_real", RAW_DATA_DIR)
                logger.info("Snapshot guardado en: data/raw/tiempo_real/")
        except FetcherError as e:
            logger.error("Error al descargar GTFS-RT: %s", e)
            raise

    db: Database | None = None
    if not args.no_insert:
        db = Database()
        if not db.database_url:
            logger.error("ERROR: DATABASE_URL no configurada")
            logger.error("Exporta: export DATABASE_URL='postgresql://...'")
            return

        await db.conectar()

    try:
        count = await procesar_y_cargar(rt_data=rt_data, rt_path=snapshot_path, db=db)
        logger.info("Completado: %d actualizaciones", count)
    finally:
        if db:
            await db.desconectar()


if __name__ == "__main__":
    asyncio.run(main())
