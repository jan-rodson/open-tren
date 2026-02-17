import os
from datetime import date, time
from typing import Optional

import pandas as pd
import psycopg2
from dotenv import load_dotenv

load_dotenv()


def get_db_connection():
    """Crea conexión a la base de datos PostgreSQL."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "opentren"),
        user=os.getenv("DB_USER", "opentren"),
        password=os.getenv("DB_PASSWORD", "opentren"),
    )


def get_fechas_disponibles() -> list[date]:
    """Obtiene las fechas disponibles en la base de datos."""
    query = "SELECT DISTINCT fecha FROM circulaciones ORDER BY fecha DESC"
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            return [row[0] for row in cur.fetchall()]


def get_origenes() -> list[str]:
    """Obtiene lista de orígenes únicos."""
    query = "SELECT DISTINCT origen_nombre FROM rutas WHERE origen_nombre IS NOT NULL ORDER BY origen_nombre"
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            return [row[0] for row in cur.fetchall()]


def get_destinos() -> list[str]:
    """Obtiene lista de destinos únicos."""
    query = "SELECT DISTINCT destino_nombre FROM rutas WHERE destino_nombre IS NOT NULL ORDER BY destino_nombre"
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            return [row[0] for row in cur.fetchall()]


def get_tipos_servicio() -> list[str]:
    """Obtiene lista de tipos de servicio."""
    query = "SELECT DISTINCT tipo_servicio FROM rutas ORDER BY tipo_servicio"
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            return [row[0] for row in cur.fetchall()]


def get_circulaciones(
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None,
    hora_inicio: Optional[time] = None,
    hora_fin: Optional[time] = None,
    tipo_servicio: Optional[str] = None,
    origen: Optional[str] = None,
    destino: Optional[str] = None,
) -> pd.DataFrame:
    """Obtiene circulaciones con filtros opcionales."""
    query = """
        SELECT DISTINCT ON (c.route_id, c.hora_salida)
            c.trip_id,
            c.codigo_tren,
            c.fecha,
            c.hora_salida,
            c.hora_llegada,
            c.delay_segundos,
            r.origen_nombre,
            r.destino_nombre,
            r.tipo_servicio
        FROM circulaciones c
        JOIN rutas r ON c.route_id = r.route_id
        WHERE 1=1
    """
    params = []

    if fecha_inicio:
        query += " AND c.fecha >= %s"
        params.append(fecha_inicio)

    if fecha_fin:
        query += " AND c.fecha <= %s"
        params.append(fecha_fin)

    if hora_inicio:
        query += " AND c.hora_salida >= %s"
        params.append(hora_inicio)

    if hora_fin:
        query += " AND c.hora_salida <= %s"
        params.append(hora_fin)

    if tipo_servicio:
        query += " AND r.tipo_servicio = %s"
        params.append(tipo_servicio)

    if origen:
        query += " AND r.origen_nombre = %s"
        params.append(origen)

    if destino:
        query += " AND r.destino_nombre = %s"
        params.append(destino)

    query += " ORDER BY c.route_id, c.hora_salida, c.delay_segundos DESC"

    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=params)


def get_estadisticas_rutas(
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None,
    hora_inicio: Optional[time] = None,
    hora_fin: Optional[time] = None,
    tipo_servicio: Optional[str] = None,
    origen: Optional[str] = None,
    destino: Optional[str] = None,
) -> pd.DataFrame:
    """Obtiene estadísticas agregadas por ruta para el scatter plot."""
    query = """
        SELECT
            r.route_id,
            r.origen_nombre,
            r.destino_nombre,
            r.tipo_servicio,
            COUNT(*) as total_trenes,
            COUNT(*) FILTER (WHERE c.delay_segundos > 0) as trenes_con_retraso,
            AVG(c.delay_segundos::float) / 60 as retraso_medio_minutos,
            AVG(
                CASE
                    WHEN (EXTRACT(EPOCH FROM (c.hora_llegada - c.hora_salida)) / 60) > 0
                    THEN (c.delay_segundos::float / 60) / (EXTRACT(EPOCH FROM (c.hora_llegada - c.hora_salida)) / 60) * 100
                    ELSE 0
                END
            ) as retraso_medio_pct
        FROM circulaciones c
        JOIN rutas r ON c.route_id = r.route_id
        WHERE 1=1
    """
    params = []

    if fecha_inicio:
        query += " AND c.fecha >= %s"
        params.append(fecha_inicio)

    if fecha_fin:
        query += " AND c.fecha <= %s"
        params.append(fecha_fin)

    if hora_inicio:
        query += " AND c.hora_salida >= %s"
        params.append(hora_inicio)

    if hora_fin:
        query += " AND c.hora_salida <= %s"
        params.append(hora_fin)

    if tipo_servicio:
        query += " AND r.tipo_servicio = %s"
        params.append(tipo_servicio)

    if origen:
        query += " AND r.origen_nombre = %s"
        params.append(origen)

    if destino:
        query += " AND r.destino_nombre = %s"
        params.append(destino)

    query += " GROUP BY r.route_id, r.origen_nombre, r.destino_nombre, r.tipo_servicio"

    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=params)
