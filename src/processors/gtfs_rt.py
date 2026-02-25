import json
import logging
from pathlib import Path
from typing import Any

from src.models import Actualizacion

logger = logging.getLogger(__name__)


class GtfsRtLoader:
    """Parsea feed GTFS-RT de Renfe."""

    def __init__(self, gtfs_rt_path: Path):
        """Inicializa el parser.

        Args:
            gtfs_rt_path: Path al archivo GTFS-RT.
        """
        self.gtfs_rt_path = gtfs_rt_path
        self._validar_archivo()

    def _validar_archivo(self) -> None:
        """Valida que existe el archivo GTFS-RT."""
        if not self.gtfs_rt_path.exists():
            raise FileNotFoundError(f"Archivo GTFS-RT no encontrado: {self.gtfs_rt_path}")

    def cargar_actualizaciones(self) -> list[Actualizacion]:
        """Carga actualizaciones desde archivo GTFS-RT.

        Returns:
            Lista de Actualizacion con los delays de cada viaje.

        Raises:
            FileNotFoundError: Si el archivo no existe.
            ValueError: Si el formato del archivo es inválido.
        """
        with open(self.gtfs_rt_path, encoding="utf-8") as f:
            data = json.load(f)

        entidades = data.get("entity", [])
        actualizaciones: list[Actualizacion] = []

        for entidad in entidades:
            try:
                actualizacion = self._procesar_entidad(entidad)
                if actualizacion:
                    actualizaciones.append(actualizacion)
            except (KeyError, TypeError, ValueError) as e:
                logger.warning(f"Entidad inválida: {e}")
                continue

        logger.info(
            f"Parseadas {len(actualizaciones)} actualizaciones de {len(entidades)} entidades"
        )
        return actualizaciones

    def _procesar_entidad(self, entidad: dict[str, Any]) -> Actualizacion | None:
        """Procesa una entidad del feed GTFS-RT.

        Args:
            entidad: Diccionario con una entidad GTFS-RT.

        Returns:
            Actualizacion si la entidad es valida, None si no tiene tripUpdate.

        Raises:
            ValueError: Si la entidad tiene datos invalidos.
        """
        trip_update = entidad.get("tripUpdate")
        if not trip_update:
            return None

        trip = trip_update.get("trip", {})
        if not trip:
            raise ValueError("tripUpdate no contiene 'trip'")

        trip_id = trip.get("tripId")
        if not trip_id:
            raise ValueError("trip no contiene 'tripId'")

        delay = trip_update.get("delay", 0)
        if delay is None:
            return None

        schedule_relationship = trip.get("scheduleRelationship", "SCHEDULED")

        return Actualizacion(
            trip_id=trip_id,
            delay_segundos=delay,
            schedule_relationship=schedule_relationship,
        )
