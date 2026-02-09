"""Modelos de datos para circulaciones e incidencias."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Circulacion(BaseModel):
    """Modelo para una circulación de tren."""

    timestamp_captura: datetime = Field(description="Timestamp de la captura del dato")
    codigo_tren: str = Field(description="Código del tren (ej: AVE 3142)")
    tipo_servicio: str = Field(description="Tipo de servicio (AVE, ALVIA, etc.)")
    linea: str = Field(description="Línea (ej: Madrid-Barcelona)")
    origen: str = Field(description="Estación de origen")
    destino: str = Field(description="Estación de destino")
    hora_salida_programada: str = Field(description="Hora de salida programada")
    hora_salida_real: Optional[str] = Field(default=None, description="Hora de salida real")
    hora_llegada_programada: str = Field(description="Hora de llegada programada")
    hora_llegada_estimada: Optional[str] = Field(
        default=None, description="Hora de llegada estimada"
    )
    retraso_minutos: int = Field(default=0, description="Retraso en minutos")
    estado: str = Field(description="Estado (PROGRAMADO, EN_RUTA, LLEGADO, CANCELADO)")
    parada_actual: Optional[str] = Field(default=None, description="Estación actual")


class Incidencia(BaseModel):
    """Modelo para una incidencia."""

    timestamp_captura: datetime = Field(description="Timestamp de la captura del dato")
    id_aviso: str = Field(description="ID del aviso")
    tipo: str = Field(description="Tipo de incidencia (OBRAS, INCIDENCIA, HUELGA, METEOROLOGIA)")
    titulo: str = Field(description="Título del aviso")
    descripcion: str = Field(description="Descripción detallada")
    lineas_afectadas: list[str] = Field(default_factory=list, description="Líneas afectadas")
    fecha_inicio: Optional[str] = Field(default=None, description="Fecha de inicio")
    fecha_fin: Optional[str] = Field(default=None, description="Fecha de fin")
    activo: bool = Field(default=True, description="Si la incidencia está activa")
