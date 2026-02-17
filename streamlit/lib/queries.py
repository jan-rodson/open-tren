from typing import Optional


def query_circulaciones(
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    origen_id: Optional[str] = None,
    destino_id: Optional[str] = None,
    tipo_servicio: Optional[str] = None,
) -> str:
    where_clauses = []
    params = []

    if fecha_inicio:
        where_clauses.append("hora_salida >= %s")
        params.append(fecha_inicio)

    if fecha_fin:
        where_clauses.append("hora_llegada <= %s")
        params.append(fecha_fin)

    if origen_id:
        where_clauses.append("origen_id = %s")
        params.append(origen_id)

    if destino_id:
        where_clauses.append("destino_id = %s")
        params.append(destino_id)

    if tipo_servicio:
        where_clauses.append("tipo_servicio = %s")
        params.append(tipo_servicio)

    where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    return f"""
        SELECT
            id, tren, origen_id, origen_nombre, destino_id, destino_nombre,
            hora_salida, hora_llegada, retraso_minutos, tipo_servicio
        FROM circulaciones
        {where_clause}
        ORDER BY hora_salida
    """


def query_estaciones() -> str:
    return """
        SELECT id, nombre, lat, lon
        FROM estaciones
        ORDER BY nombre
    """


def query_incidencias() -> str:
    return """
        SELECT id, titulo, descripcion, fecha_inicio, fecha_fin, tipo
        FROM incidencias
        WHERE fecha_fin IS NULL OR fecha_fin > NOW()
        ORDER BY fecha_inicio DESC
    """


def query_kpis(fecha_inicio: Optional[str] = None, fecha_fin: Optional[str] = None) -> str:
    where_clause = ""
    if fecha_inicio and fecha_fin:
        where_clause = f"WHERE hora_salida BETWEEN '{fecha_inicio}' AND '{fecha_fin}'"

    return f"""
        SELECT
            COUNT(*) as total,
            COUNT(CASE WHEN retraso_minutos <= 5 THEN 1 END) as puntuales,
            AVG(retraso_minutos) as retraso_promedio
        FROM circulaciones
        {where_clause}
    """
