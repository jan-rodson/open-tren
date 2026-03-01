"""Tests para modelos de Circulacion."""

from datetime import date, time

from src.models import Actualizacion, Ruta, Viaje


def test_viaje_delay_minutos():
    """Test del computed field delay_minutos."""
    snapshot = Viaje(
        trip_id="0019012026-02-19",
        codigo_tren="00190",
        fecha=date(2026, 2, 19),
        route_id="123",
        hora_salida=time(8, 30),
        hora_llegada=time(11, 30),
        delay_segundos=900,
    )

    assert snapshot.delay_minutos == 15


def test_viaje_delay_pct_trayecto():
    """Test del computed field delay_pct_trayecto."""
    snapshot = Viaje(
        trip_id="0019012026-02-19",
        codigo_tren="00190",
        fecha=date(2026, 2, 19),
        route_id="123",
        hora_salida=time(8, 30),
        hora_llegada=time(11, 30),
        delay_segundos=900,
    )

    assert round(float(snapshot.delay_pct_trayecto), 2) == 8.33


def test_viaje_tiempo_trayecto_calculado():
    """Test de tiempo_trayecto_minutos como computed field."""
    viaje = Viaje(
        trip_id="test",
        codigo_tren="001",
        fecha=date(2026, 2, 23),
        route_id="123",
        hora_salida=time(8, 30),
        hora_llegada=time(11, 30),
        delay_segundos=0,
    )
    assert viaje.tiempo_trayecto_minutos == 180


def test_viaje_tiempo_trayecto_dia_siguiente():
    """Test de tiempo_trayecto_minutos con llegada día siguiente."""
    viaje = Viaje(
        trip_id="test",
        codigo_tren="001",
        fecha=date(2026, 2, 23),
        route_id="123",
        hora_salida=time(22, 30),
        hora_llegada=time(2, 30),
        delay_segundos=0,
    )
    assert viaje.tiempo_trayecto_minutos == 240


def test_ruta_origen_destino():
    """Test de Ruta con origen_nombre y destino_nombre."""
    ruta = Ruta(
        route_id="1700037606GL023",
        tipo_servicio="ALVIA",
        origen_nombre="Madrid Atocha",
        destino_nombre="Barcelona Sants",
    )
    assert ruta.origen_nombre == "Madrid Atocha"
    assert ruta.destino_nombre == "Barcelona Sants"


def test_actualizacion_creacion():
    """Test de creación básica de Actualizacion."""
    act = Actualizacion(
        trip_id="0019012026-02-19",
        delay_segundos=900,
        schedule_relationship="SCHEDULED",
    )
    assert act.trip_id == "0019012026-02-19"
    assert act.delay_segundos == 900
    assert act.schedule_relationship == "SCHEDULED"


def test_viaje_delay_pct_trayecto_sin_retraso():
    """Test de delay_pct_trayecto sin retraso."""
    viaje = Viaje(
        trip_id="test",
        codigo_tren="001",
        fecha=date(2026, 2, 23),
        route_id="123",
        hora_salida=time(8, 30),
        hora_llegada=time(11, 30),
        delay_segundos=0,
    )
    assert viaje.delay_pct_trayecto == 0


def test_viaje_delay_pct_trayecto_trayecto_cero():
    """Test de delay_pct_trayecto con hora_salida == hora_llegada."""
    viaje = Viaje(
        trip_id="test",
        codigo_tren="001",
        fecha=date(2026, 2, 23),
        route_id="123",
        hora_salida=time(10, 0),
        hora_llegada=time(10, 0),
        delay_segundos=300,
    )
    assert viaje.delay_pct_trayecto == 0


def test_viaje_delay_negativo():
    """Test de delay_segundos negativo (adelanto)."""
    viaje = Viaje(
        trip_id="test",
        codigo_tren="001",
        fecha=date(2026, 2, 23),
        route_id="123",
        hora_salida=time(8, 30),
        hora_llegada=time(11, 30),
        delay_segundos=-300,
    )
    assert viaje.delay_segundos == -300
    assert viaje.delay_minutos == -5


def test_viaje_serializacion_json():
    """Test de serialización/deserialización JSON."""
    viaje = Viaje(
        trip_id="test",
        codigo_tren="001",
        fecha=date(2026, 2, 23),
        route_id="123",
        hora_salida=time(8, 30),
        hora_llegada=time(11, 30),
        delay_segundos=300,
    )
    json_data = viaje.model_dump_json()
    viaje_restaurado = Viaje.model_validate_json(json_data)
    assert viaje_restaurado.trip_id == "test"
    assert viaje_restaurado.delay_segundos == 300


def test_actualizacion_delay_negativo():
    """Test de Actualizacion con delay negativo."""
    act = Actualizacion(
        trip_id="0019012026-02-19",
        delay_segundos=-300,
        schedule_relationship="SCHEDULED",
    )
    assert act.delay_segundos == -300
