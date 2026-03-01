"""Script para procesar GTFS estático de Renfe (descargar o desde snapshot) e insertar en BD."""

import argparse
import asyncio
import logging
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path

from src.config import DEFAULT_USER_AGENT, GTFS_DIR
from src.fetchers import FetcherError, GtfsStaticFetcher
from src.processors.gtfs_static import GtfsStaticLoader
from src.storage.database import Database
from src.storage.repositories import CirculacionRepository, RutaRepository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def save_gtfs(content: bytes, timestamp: datetime, output_dir: Path = GTFS_DIR) -> Path:
    """Guarda y extrae el GTFS estático."""
    output_dir.mkdir(parents=True, exist_ok=True)

    zip_path = output_dir / f"google_transit_{timestamp.strftime('%Y%m%d_%H%M%S')}.zip"
    zip_path.write_bytes(content)

    extract_dir = output_dir / "renfe_av_ld_md"
    extract_dir.mkdir(exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_dir)

    logger.info("GTFS extraído en: %s", extract_dir)

    return extract_dir


def extract_gtfs_from_snapshot(zip_path: Path, output_dir: Path = GTFS_DIR) -> Path:
    """Extrae GTFS desde un snapshot local."""
    if not zip_path.exists():
        raise FileNotFoundError(f"Snapshot no encontrado: {zip_path}")

    logger.info("Extrayendo GTFS desde snapshot: %s", zip_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    extract_dir = output_dir / "renfe_av_ld_md"
    extract_dir.mkdir(exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_dir)

    logger.info("GTFS extraído en: %s", extract_dir)
    return extract_dir


async def cargar_gtfs_incremental(
    gtfs_dir: Path,
    db: Database,
    fecha_inicio: date | None = None,
    dias_futuros: int = 7,
) -> tuple[int, int]:
    """Carga incremental de viajes desde GTFS estático.

    Estrategia:
    1. Cargar todos los viajes del GTFS
    2. Filtrar por rango de fechas [fecha_inicio, fecha_inicio+dias_futuros]
    3. Identificar qué NO existen en BD → INSERT
    4. Identificar qué existen pero son futuros → UPDATE datos estáticos
    5. Preservar delays de viajes existentes
    """
    if fecha_inicio is None:
        fecha_inicio = date.today()

    loader = GtfsStaticLoader(gtfs_dir)

    rutas = loader.cargar_rutas()
    viajes = loader.cargar_viajes()

    logger.info(
        "Cargados %d rutas, %d viajes del GTFS",
        len(rutas),
        len(viajes),
    )

    fecha_fin = fecha_inicio + timedelta(days=dias_futuros)
    viajes_futuros = [v for v in viajes if fecha_inicio <= v.fecha <= fecha_fin]
    logger.info("Viajes en rango [%s, %s]: %d", fecha_inicio, fecha_fin, len(viajes_futuros))

    repo_circulaciones = CirculacionRepository(db)
    repo_rutas = RutaRepository(db)

    existentes = await repo_circulaciones.obtener_trip_ids_existentes()
    logger.info("Existen %d viajes en BD", len(existentes))

    nuevos = [v for v in viajes_futuros if v.trip_id not in existentes]
    existentes_futuros = [
        v for v in viajes_futuros if v.trip_id in existentes and v.fecha >= fecha_inicio
    ]

    logger.info("Viajes nuevos a insertar: %d", len(nuevos))
    logger.info("Viajes existentes futuros a actualizar: %d", len(existentes_futuros))

    count_rutas = await repo_rutas.insertar_batch(rutas)
    logger.info("Actualizadas %d rutas", count_rutas)

    insertados = await repo_circulaciones.insertar_nuevos_viajes(nuevos)
    logger.info("Insertados %d viajes nuevos en BD", insertados)

    actualizados = await repo_circulaciones.actualizar_datos_estaticos_futuros(existentes_futuros)
    logger.info("Actualizados %d viajes futuros en BD", actualizados)

    return count_rutas, insertados + actualizados


async def cargar_gtfs_completo(
    gtfs_dir: Path,
    db: Database | None = None,
) -> tuple[int, int]:
    """Carga todos los datos GTFS en BD (modo compatibilidad).

    Este método carga TODOS los viajes del GTFS, no solo los futuros.
    Útil para carga inicial o cuando se quiere regenerar todo.
    """
    loader = GtfsStaticLoader(gtfs_dir)

    rutas = loader.cargar_rutas()
    viajes = loader.cargar_viajes()

    logger.info("Cargados %d rutas, %d viajes", len(rutas), len(viajes))

    if db is None:
        logger.info("Modo --no-insert: sin inserción en BD")
        return len(rutas), len(viajes)

    repo_circulaciones = CirculacionRepository(db)
    existentes = await repo_circulaciones.obtener_trip_ids_existentes()
    logger.info("Existen %d viajes en BD, filtrando viajes nuevos...", len(existentes))

    viajes_nuevos = [v for v in viajes if v.trip_id not in existentes]
    logger.info("Viajes nuevos a insertar: %d", len(viajes_nuevos))

    repo_rutas = RutaRepository(db)

    count_rutas = await repo_rutas.insertar_batch(rutas)
    count_viajes = await repo_circulaciones.insertar_nuevos_viajes(viajes_nuevos)

    logger.info(
        "Insertadas %d rutas, %d viajes en BD",
        count_rutas,
        count_viajes,
    )
    return count_rutas, count_viajes


async def main() -> None:
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="Procesa GTFS estático de Renfe (API o snapshot) e inserta en BD"
    )
    parser.add_argument(
        "--snapshot",
        type=str,
        help="Path a ZIP local en vez de descargar de API",
    )
    parser.add_argument(
        "--no-insert",
        action="store_true",
        help="Solo descargar/procesar, sin insertar en BD",
    )
    parser.add_argument(
        "--gtfs-dir",
        type=str,
        default=None,
        help="Directorio GTFS (default: GTFS_DIR de config)",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["incremental", "completo"],
        default="incremental",
        help="Modo de carga: incremental (solo viajes futuros) o completo (todos)",
    )
    parser.add_argument(
        "--dias-futuros",
        type=int,
        default=7,
        help="Número de días futuros a cargar en modo incremental (default: 7)",
    )
    args = parser.parse_args()

    gtfs_dir = Path(args.gtfs_dir) if args.gtfs_dir else GTFS_DIR

    if args.snapshot:
        snapshot_path = Path(args.snapshot)
        extract_dir = extract_gtfs_from_snapshot(snapshot_path, gtfs_dir)
    else:
        try:
            async with GtfsStaticFetcher(user_agent=DEFAULT_USER_AGENT) as fetcher:
                result = await fetcher.fetch()
                logger.info("GTFS descargado de API: %s bytes", len(result.data))
                extract_dir = save_gtfs(result.data, result.timestamp, gtfs_dir)
        except FetcherError as e:
            logger.error("Error al descargar GTFS: %s", e)
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
        if args.mode == "incremental":
            if not db:
                raise ValueError("Database connection required for incremental mode")
            count_rutas, count_viajes = await cargar_gtfs_incremental(
                extract_dir, db, dias_futuros=args.dias_futuros
            )
        else:
            count_rutas, count_viajes = await cargar_gtfs_completo(extract_dir, db)

        logger.info(
            "Completado: %d rutas, %d viajes",
            count_rutas,
            count_viajes,
        )
    finally:
        if db:
            await db.desconectar()


if __name__ == "__main__":
    asyncio.run(main())
