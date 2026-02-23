from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, computed_field, field_validator


class Ruta(BaseModel):
    """Ruta con su secuencia de paradas en orden."""

    route_id: str
    tipo_servicio: str
    paradas: list[str]  # stop_id en orden

    @computed_field
    @property
    def origen_id(self) -> str:
        """ID de la primera parada de la ruta."""
        return self.paradas[0] if self.paradas else ""

    @computed_field
    @property
    def destino_id(self) -> str:
        """ID de la última parada de la ruta."""
        return self.paradas[-1] if self.paradas else ""


class Viaje(BaseModel):
    """Estado de una circulación con datos estáticos y dinámicos."""

    trip_id: str
    codigo_tren: str
    fecha: date
    route_id: str

    # Horarios específicos del viaje
    hora_salida: time
    hora_llegada: time

    # Delay (dinámico, desde GTFS-RT)
    delay_segundos: int

    @computed_field
    @property
    def tiempo_trayecto_minutos(self) -> int:
        """Calcula tiempo de trayecto en minutos."""
        delta = datetime.combine(date.min, self.hora_llegada) - datetime.combine(
            date.min, self.hora_salida
        )
        minutos = int(delta.total_seconds() / 60)
        if minutos < 0:
            minutos += 24 * 60
        return minutos

    @computed_field
    @property
    def delay_minutos(self) -> int:
        """Retraso en minutos."""
        return self.delay_segundos // 60

    @computed_field
    @property
    def delay_pct_trayecto(self) -> Decimal:
        """Porcentaje de retraso sobre el tiempo de trayecto."""
        if self.tiempo_trayecto_minutos <= 0:
            return Decimal("0")
        return Decimal(self.delay_minutos) / Decimal(self.tiempo_trayecto_minutos) * 100


class Parada(BaseModel):
    """Estación o parada ferroviaria."""

    stop_id: str
    stop_nombre: str
    stop_lat: float
    stop_lon: float

    @field_validator("stop_lat")
    @classmethod
    def validate_lat(cls, v: float) -> float:
        """Valida que la latitud esté en el rango [-90, 90]."""
        if not -90 <= v <= 90:
            raise ValueError("latitud debe estar entre -90 y 90")
        return v

    @field_validator("stop_lon")
    @classmethod
    def validate_lon(cls, v: float) -> float:
        """Valida que la longitud esté en el rango [-180, 180]."""
        if not -180 <= v <= 180:
            raise ValueError("longitud debe estar entre -180 y 180")
        return v


class Actualizacion(BaseModel):
    """Actualización de tiempo real de GTFS-RT."""

    trip_id: str
    delay_segundos: int
    schedule_relationship: str
