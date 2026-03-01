"""Script para inicializar la base de datos Neon."""

import argparse
import asyncio
import logging
from pathlib import Path

from src.storage.database import Database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

SCHEMA_PATH = Path(__file__).parent.parent / "src" / "storage" / "schema.sql"


async def setup_database(database_url: str, recreate: bool = False) -> None:
    """Inicializa la base de datos con el schema."""
    db = Database(database_url)

    try:
        await db.conectar()
        logger.info("Conectado a la base de datos")

        schema_sql = SCHEMA_PATH.read_text()

        if recreate:
            logger.warning("Eliminando tablas existentes...")
            await db.ejecutar("DROP TABLE IF EXISTS circulaciones CASCADE")
            await db.ejecutar("DROP TABLE IF EXISTS rutas CASCADE")

        logger.info("Ejecutando schema.sql...")
        statements = [s.strip() for s in schema_sql.split(";") if s.strip()]

        for i, statement in enumerate(statements, 1):
            if statement:
                try:
                    await db.ejecutar(statement)
                    logger.debug(f"Statement {i} ejecutado")
                except Exception as e:
                    logger.error(f"Error en statement {i}: {e}")
                    raise

        logger.info("Schema creado correctamente")

    finally:
        await db.desconectar()
        logger.info("Desconectado de la base de datos")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inicializa la base de datos de Open Tren")
    parser.add_argument(
        "--database-url",
        type=str,
        help="URL de conexión a PostgreSQL (si no se usa DATABASE_URL)",
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Elimina las tablas existentes antes de crear el schema",
    )
    args = parser.parse_args()

    import os

    database_url = args.database_url or os.environ.get("DATABASE_URL")
    if not database_url:
        logger.error("Se requiere DATABASE_URL o --database-url")
        return

    asyncio.run(setup_database(database_url, recreate=args.recreate))


if __name__ == "__main__":
    main()
