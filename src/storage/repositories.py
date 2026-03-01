"""Repositorios para acceso a datos."""

from datetime import date, time
from typing import Any

from src.models import Actualizacion, Ruta, Viaje
from src.storage.database import Database


class CirculacionRepository:
    """Repositorio para la tabla circulaciones."""

    def __init__(self, db: Database):
        self.db = db

    async def insertar_batch(self, viajes: list[Viaje]) -> int:
        """Inserta o actualiza múltiples viajes."""
        if not viajes:
            return 0

        query = """
            INSERT INTO circulaciones (
                trip_id, codigo_tren, fecha, route_id,
                hora_salida, hora_llegada, delay_segundos
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (trip_id) DO UPDATE SET
                delay_segundos = EXCLUDED.delay_segundos,
                updated_at = NOW()
        """

        valores = [
            (
                v.trip_id,
                v.codigo_tren,
                v.fecha,
                v.route_id,
                v.hora_salida,
                v.hora_llegada,
                v.delay_segundos,
            )
            for v in viajes
        ]

        async with self.db.conexion() as conn:
            await conn.executemany(query, valores)
        return len(valores)

    async def obtener_por_filtros(
        self,
        fecha_desde: date,
        fecha_hasta: date,
        hora_desde: time | None = None,
        hora_hasta: time | None = None,
        tipo_servicio: str | None = None,
        origen: str | None = None,
        destino: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Viaje]:
        """Obtiene viajes según filtros."""
        condiciones = ["c.fecha BETWEEN $1 AND $2"]
        params: list[Any] = [fecha_desde, fecha_hasta]
        idx = 3

        if hora_desde:
            condiciones.append(f"c.hora_salida >= ${idx}")
            params.append(hora_desde)
            idx += 1
        if hora_hasta:
            condiciones.append(f"c.hora_salida <= ${idx}")
            params.append(hora_hasta)
            idx += 1
        if tipo_servicio:
            condiciones.append(f"r.tipo_servicio = ${idx}")
            params.append(tipo_servicio)
            idx += 1

        query = f"""
            SELECT
                c.trip_id, c.codigo_tren, c.fecha, c.route_id,
                c.hora_salida, c.hora_llegada, c.delay_segundos,
                r.tipo_servicio
            FROM circulaciones c
            JOIN rutas r ON c.route_id = r.route_id
            WHERE {" AND ".join(condiciones)}
            ORDER BY c.trip_id
            LIMIT ${idx} OFFSET ${idx + 1}
        """
        params.extend([limit, offset])

        rows = await self.db.fetch(query, *params)
        return [self._row_to_viaje(r) for r in rows]

    async def obtener_ultimo_estado(self, trip_id: str) -> Viaje | None:
        """Obtiene el último estado de un tren."""
        query = "SELECT * FROM circulaciones WHERE trip_id = $1 LIMIT 1"
        row = await self.db.fetchrow(query, trip_id)
        return self._row_to_viaje(row) if row else None

    async def insertar_nuevos_viajes(self, viajes: list[Viaje]) -> int:
        """Inserta viajes nuevos (delay=0) sin afectar existentes."""
        if not viajes:
            return 0

        query = """
            INSERT INTO circulaciones (
                trip_id, codigo_tren, fecha, route_id,
                hora_salida, hora_llegada, delay_segundos
            ) VALUES ($1, $2, $3, $4, $5, $6, 0)
            ON CONFLICT (trip_id) DO NOTHING
        """

        valores = [
            (v.trip_id, v.codigo_tren, v.fecha, v.route_id, v.hora_salida, v.hora_llegada)
            for v in viajes
        ]

        async with self.db.conexion() as conn:
            await conn.executemany(query, valores)
        return len(valores)

    async def obtener_trip_ids_existentes(self) -> set[str]:
        """Obtiene todos los trip_ids que ya existen en BD."""
        query = "SELECT trip_id FROM circulaciones"
        rows = await self.db.fetch(query)
        return {row["trip_id"] for row in rows}

    async def actualizar_datos_estaticos_futuros(self, viajes: list[Viaje]) -> int:
        """Actualiza datos estáticos de viajes futuros (fecha >= hoy)."""
        if not viajes:
            return 0

        query = """
            UPDATE circulaciones SET
                codigo_tren = EXCLUDED.codigo_tren,
                hora_salida = EXCLUDED.hora_salida,
                hora_llegada = EXCLUDED.hora_llegada,
                updated_at = NOW()
            WHERE trip_id = $1 AND fecha >= CURRENT_DATE
        """

        valores = [(v.trip_id, v.codigo_tren, v.hora_salida, v.hora_llegada) for v in viajes]

        async with self.db.conexion() as conn:
            await conn.executemany(query, valores)
        return len(valores)

    async def actualizar_batch_delays(self, actualizaciones: list[Actualizacion]) -> int:
        """Actualiza delays de múltiples viajes desde GTFS-RT."""
        if not actualizaciones:
            return 0

        query = """
            UPDATE circulaciones SET
                delay_segundos = $1,
                updated_at = NOW()
            WHERE trip_id = $2
        """

        valores = [(a.delay_segundos, a.trip_id) for a in actualizaciones]

        async with self.db.conexion() as conn:
            await conn.executemany(query, valores)
        return len(valores)

    def _row_to_viaje(self, row: Any) -> Viaje:
        return Viaje(
            trip_id=row["trip_id"],
            codigo_tren=row["codigo_tren"],
            fecha=row["fecha"],
            route_id=row["route_id"],
            hora_salida=row["hora_salida"],
            hora_llegada=row["hora_llegada"],
            delay_segundos=row["delay_segundos"],
        )


class RutaRepository:
    """Repositorio para la tabla rutas."""

    def __init__(self, db: Database):
        self.db = db

    async def insertar_batch(self, rutas: list[Ruta]) -> int:
        """Inserta múltiples rutas."""
        if not rutas:
            return 0

        query = """
            INSERT INTO rutas (route_id, tipo_servicio, origen_nombre, destino_nombre)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (route_id) DO UPDATE SET
                tipo_servicio = EXCLUDED.tipo_servicio,
                origen_nombre = EXCLUDED.origen_nombre,
                destino_nombre = EXCLUDED.destino_nombre
        """

        valores = [(r.route_id, r.tipo_servicio, r.origen_nombre, r.destino_nombre) for r in rutas]

        async with self.db.conexion() as conn:
            await conn.executemany(query, valores)
        return len(valores)
