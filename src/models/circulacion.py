from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, computed_field


class Ruta(BaseModel):
    """Ruta con origen y destino como texto."""

    route_id: str
    tipo_servicio: str
    origen_nombre: str
    destino_nombre: str


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


class Actualizacion(BaseModel):
    """Actualización de tiempo real de GTFS-RT."""

    trip_id: str
    delay_segundos: int
    schedule_relationship: str
