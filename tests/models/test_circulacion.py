"""Tests para modelos de Circulacion."""

from datetime import date, time

import pytest
from pydantic import ValidationError

from src.models import Actualizacion, Parada, Ruta, Viaje


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
    """Test de computed fields origen_id y destino_id en Ruta."""
    ruta = Ruta(
        route_id="1700037606GL023",
        tipo_servicio="ALVIA",
        paradas=["17000", "18000", "35001", "37606"],
    )
    assert ruta.origen_id == "17000"
    assert ruta.destino_id == "37606"


def test_ruta_vacia():
    """Test de ruta sin paradas."""
    ruta = Ruta(
        route_id="test",
        tipo_servicio="TEST",
        paradas=[],
    )
    assert ruta.origen_id == ""
    assert ruta.destino_id == ""


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


def test_parada_creacion():
    """Test de creación básica de Parada."""
    parada = Parada(
        stop_id="17000",
        stop_nombre="Madrid",
        stop_lat=40.4168,
        stop_lon=-3.7038,
    )
    assert parada.stop_id == "17000"
    assert parada.stop_nombre == "Madrid"
    assert -90 <= parada.stop_lat <= 90
    assert -180 <= parada.stop_lon <= 180


def test_parada_coordenadas_fuera_rango():
    """Test de validación de coordenadas fuera de rango."""
    with pytest.raises(ValidationError):
        Parada(
            stop_id="17000",
            stop_nombre="Madrid",
            stop_lat=91,
            stop_lon=-3.7038,
        )


def test_parada_valores_extremos():
    """Test de validación de coordenadas en límites válidos."""
    parada = Parada(
        stop_id="17000",
        stop_nombre="Madrid",
        stop_lat=-90,
        stop_lon=-180,
    )
    assert parada.stop_lat == -90
    assert parada.stop_lon == -180


def test_ruta_una_parada():
    """Test de ruta con una sola parada (origen == destino)."""
    ruta = Ruta(
        route_id="test",
        tipo_servicio="TEST",
        paradas=["17000"],
    )
    assert ruta.origen_id == "17000"
    assert ruta.destino_id == "17000"


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
