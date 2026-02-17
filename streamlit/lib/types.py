from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional

TipoServicio = Literal["AV", "LD", "MD"]


@dataclass
class Estacion:
    id: str
    nombre: str
    lat: float
    lon: float


@dataclass
class Circulacion:
    id: str
    tren: str
    origen_id: str
    origen_nombre: str
    destino_id: str
    destino_nombre: str
    hora_salida: datetime
    hora_llegada: datetime
    retraso_minutos: float
    tipo_servicio: TipoServicio


@dataclass
class Incidencia:
    id: str
    titulo: str
    descripcion: str
    fecha_inicio: datetime
    fecha_fin: Optional[datetime]
    tipo: str
    afectados: list[str]


@dataclass
class KPIs:
    trenes_en_circulacion: int
    tasa_puntualidad: float
    retraso_promedio: float
    total_circulaciones: int
