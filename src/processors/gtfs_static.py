import logging
import re
from datetime import date, time
from pathlib import Path

import polars as pl
from pydantic import ValidationError

from src.models import Ruta, Viaje

logger = logging.getLogger(__name__)

PATTERN_TRIP_ID = re.compile(r"^(.+)(\d{4})-(\d{2})-(\d{2})$")
PATTERN_HORA = re.compile(r"^(\d{1,2}):(\d{2}):(\d{2})$")


class GtfsStaticLoader:
    """Carga datos del GTFS estático."""

    def __init__(self, gtfs_dir: Path):
        self.gtfs_dir = gtfs_dir
        self.trips_path = gtfs_dir / "trips.txt"
        self.routes_path = gtfs_dir / "routes.txt"
        self.stop_times_path = gtfs_dir / "stop_times.txt"
        self.stops_path = gtfs_dir / "stops.txt"

        self._validar_archivos()

    def _validar_archivos(self) -> None:
        """Valida que existan los archivos GTFS necesarios."""
        archivos_requeridos = {
            "trips.txt": self.trips_path,
            "routes.txt": self.routes_path,
            "stop_times.txt": self.stop_times_path,
            "stops.txt": self.stops_path,
        }

        faltantes = [nombre for nombre, path in archivos_requeridos.items() if not path.exists()]
        if faltantes:
            raise FileNotFoundError(f"Archivos GTFS faltantes: {', '.join(faltantes)}")

    def cargar_viajes(self) -> list[Viaje]:
        """Carga todos los viajes del GTFS.

        Returns:
            Lista de Viaje con todos los viajes.
        """
        trips = pl.read_csv(self.trips_path)
        stop_times = pl.read_csv(self.stop_times_path)

        horarios_por_trip = stop_times.group_by("trip_id").agg(  # type: ignore[reportUnknownMemberType]
            [
                pl.col("arrival_time").first().alias("hora_salida"),
                pl.col("departure_time").last().alias("hora_llegada"),
            ]
        )

        viajes_df = trips.join(horarios_por_trip, on="trip_id", how="left")

        resultados: list[Viaje] = []
        for idx, row in enumerate(viajes_df.iter_rows(named=True), start=1):
            hora_salida = row.get("hora_salida")
            hora_llegada = row.get("hora_llegada")

            if hora_salida is None or hora_llegada is None:
                logger.warning(f"Fila {idx}: viaje sin horarios (sin stop_times), ignorado")
                continue

            codigo_tren, fecha_trip = self._extraer_codigo_y_fecha(row["trip_id"])

            hora_salida = self._parsear_hora_gtfs(hora_salida)
            hora_llegada = self._parsear_hora_gtfs(hora_llegada)

            try:
                resultados.append(
                    Viaje(
                        trip_id=row["trip_id"],
                        codigo_tren=codigo_tren,
                        fecha=fecha_trip,
                        route_id=row["route_id"],
                        hora_salida=hora_salida,
                        hora_llegada=hora_llegada,
                        delay_segundos=0,
                    )
                )
            except ValidationError as e:
                logger.error(f"Fila {idx}: {e}")

        logger.info(f"Cargados {len(resultados)} viajes desde {self.trips_path.name}")
        return resultados

    def cargar_rutas(self) -> list[Ruta]:
        """Carga rutas con origen y destino como texto.

        Returns:
            Lista de Ruta, una por route_id con origen y destino.
        """
        stop_times = pl.read_csv(self.stop_times_path)
        trips = pl.read_csv(self.trips_path)
        routes = pl.read_csv(self.routes_path)
        stops = pl.read_csv(self.stops_path)

        stop_times_ordered = stop_times.sort(["trip_id", "stop_sequence"])

        stop_times_con_ruta = stop_times_ordered.join(
            trips[["trip_id", "route_id"]], on="trip_id", how="left"
        )

        primer_y_ultima = stop_times_con_ruta.group_by("route_id").agg(
            [
                pl.col("stop_id").first().alias("primer_stop_id"),
                pl.col("stop_id").last().alias("ultimo_stop_id"),
            ]
        )

        rutas_con_stops = primer_y_ultima.join(
            routes[["route_id", "route_short_name"]], on="route_id", how="left"
        )

        stops_renamed = stops.rename({"stop_id": "stop_id", "stop_name": "stop_name"})

        rutas_con_nombres = rutas_con_stops.join(
            stops_renamed[["stop_id", "stop_name"]].unique(),
            left_on="primer_stop_id",
            right_on="stop_id",
            how="left",
        ).rename({"stop_name": "origen_nombre"})

        rutas_final = rutas_con_nombres.join(
            stops_renamed[["stop_id", "stop_name"]].unique(),
            left_on="ultimo_stop_id",
            right_on="stop_id",
            how="left",
        ).rename({"stop_name": "destino_nombre"})

        resultados: list[Ruta] = []
        for row in rutas_final.iter_rows(named=True):
            try:
                resultados.append(
                    Ruta(
                        route_id=row["route_id"],
                        tipo_servicio=row["route_short_name"],
                        origen_nombre=row["origen_nombre"],
                        destino_nombre=row["destino_nombre"],
                    )
                )
            except ValidationError as e:
                logger.error(f"Error creando ruta {row['route_id']}: {e}")

        logger.info(f"Cargadas {len(resultados)} rutas")
        return resultados

    def _extraer_codigo_y_fecha(self, trip_id: str) -> tuple[str, date]:
        """Extrae código del tren y fecha del trip_id.

        Formato esperado: [codigo]YYYY-MM-DD
        Ejemplos:
            - 0019012026-02-19 -> codigo="00190", fecha=2026-02-19
            - 56012026-02-19 -> codigo="560", fecha=2026-02-19

        Raises:
            ValueError: Si el trip_id no tiene el formato esperado.
        """
        match = PATTERN_TRIP_ID.match(trip_id)
        if not match:
            raise ValueError(f"trip_id '{trip_id}' no tiene formato esperado [codigo]YYYY-MM-DD")

        codigo = match.group(1)
        anio = int(match.group(2))
        mes = int(match.group(3))
        dia = int(match.group(4))

        try:
            fecha = date(anio, mes, dia)
        except ValueError:
            raise ValueError(
                f"trip_id '{trip_id}' con fecha inválida: {anio}-{mes:02d}-{dia:02d}"
            ) from None

        return codigo, fecha

    def _parsear_hora_gtfs(self, hora: str) -> time:
        """Parsea hora GTFS formato H:MM:SS o HH:MM:SS.

        El GTFS puede usar horas > 24 para indicar llegada al día siguiente.
        En ese caso, convertimos a una hora válida (sin día).

        Formatos aceptados:
            - "8:30:00" -> 08:30:00
            - "13:26:00" -> 13:26:00
            - "25:30:00" -> 01:30:00 (día siguiente)

        Raises:
            ValueError: Si el formato es inválido.
        """
        match = PATTERN_HORA.match(hora)
        if not match:
            raise ValueError(f"Formato de hora inválido: '{hora}' (esperado H:MM:SS // HH:MM:SS)")

        h = int(match.group(1))
        m = int(match.group(2))
        s = int(match.group(3))

        h = h % 24

        return time(h, m, s)
