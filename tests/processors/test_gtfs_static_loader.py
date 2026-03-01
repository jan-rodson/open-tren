"""Tests para GtfsStaticLoader."""

from datetime import date, time
from pathlib import Path

import pytest

from src.processors.gtfs_static import GtfsStaticLoader


def test_validar_archivos_faltan_archivos(tmp_path: Path):
    """Test que lanza FileNotFoundError si faltan archivos GTFS."""
    gtfs_dir = tmp_path / "gtfs"
    gtfs_dir.mkdir()
    (gtfs_dir / "trips.txt").write_text("trip_id\n1\n")

    with pytest.raises(FileNotFoundError, match="Archivos GTFS faltantes"):
        GtfsStaticLoader(gtfs_dir)


def test_cargar_viajes_exitoso(gtfs_static_files: Path):
    """Test carga exitosa de viajes."""
    loader = GtfsStaticLoader(gtfs_static_files)
    viajes = loader.cargar_viajes()

    assert len(viajes) == 3
    assert viajes[0].trip_id == "T0019012026-02-19"
    assert viajes[0].codigo_tren == "T001901"
    assert viajes[0].fecha == date(2026, 2, 19)
    assert viajes[0].hora_salida == time(8, 0)
    assert viajes[0].hora_llegada == time(12, 0)
    assert viajes[0].delay_segundos == 0


def test_cargar_viajes_formato_hora_invalido(tmp_path: Path):
    """Test que lanza ValueError con formato de hora inválido."""
    gtfs_dir = tmp_path / "gtfs"
    gtfs_dir.mkdir()

    (gtfs_dir / "trips.txt").write_text("trip_id,service_id,route_id\nT120260219-2026-02-19,1,R1\n")
    (gtfs_dir / "stop_times.txt").write_text(
        "trip_id,stop_id,stop_sequence,arrival_time,departure_time\n"
        "T120260219-2026-02-19,MAD,1,invalid,08:00:00\n"
    )
    (gtfs_dir / "routes.txt").write_text("route_id,route_short_name\nR1,AVE\n")
    (gtfs_dir / "stops.txt").write_text("stop_id,stop_name,stop_lat,stop_lon\nMAD,M,40,3\n")

    loader = GtfsStaticLoader(gtfs_dir)

    with pytest.raises(ValueError, match="Formato de hora inválido"):
        loader.cargar_viajes()


def test_cargar_viajes_codigo_vacio(tmp_path: Path):
    """Test que maneja trip_id sin código antes de la fecha."""
    gtfs_dir = tmp_path / "gtfs"
    gtfs_dir.mkdir()

    (gtfs_dir / "trips.txt").write_text("trip_id,service_id,route_id\n2026-02-19,1,R1\n")
    (gtfs_dir / "stop_times.txt").write_text(
        "trip_id,stop_id,stop_sequence,arrival_time,departure_time\n"
        "2026-02-19,MAD,1,08:00:00,08:00:00\n"
    )
    (gtfs_dir / "routes.txt").write_text("route_id,route_short_name\nR1,AVE\n")
    (gtfs_dir / "stops.txt").write_text("stop_id,stop_name,stop_lat,stop_lon\nMAD,M,40,3\n")

    loader = GtfsStaticLoader(gtfs_dir)
    with pytest.raises(ValueError, match="no tiene formato esperado"):
        loader.cargar_viajes()


def test_cargar_viajes_fecha_invalida(tmp_path: Path):
    """Test que lanza ValueError con fecha inválida."""
    gtfs_dir = tmp_path / "gtfs"
    gtfs_dir.mkdir()

    (gtfs_dir / "trips.txt").write_text("trip_id,service_id,route_id\nT0019012026-02-30,1,R1\n")
    (gtfs_dir / "stop_times.txt").write_text(
        "trip_id,stop_id,stop_sequence,arrival_time,departure_time\n"
        "T0019012026-02-30,MAD,1,08:00:00,08:00:00\n"
    )
    (gtfs_dir / "routes.txt").write_text("route_id,route_short_name\nR1,AVE\n")
    (gtfs_dir / "stops.txt").write_text("stop_id,stop_name,stop_lat,stop_lon\nMAD,M,40,3\n")

    loader = GtfsStaticLoader(gtfs_dir)
    with pytest.raises(ValueError, match="fecha inválida"):
        loader.cargar_viajes()


def test_cargar_paradas_exitoso(gtfs_static_files: Path):
    """Test carga exitosa de paradas."""
    loader = GtfsStaticLoader(gtfs_static_files)
    paradas = loader.cargar_paradas()

    assert len(paradas) == 3
    assert paradas[0].stop_id == "MAD"
    assert paradas[0].stop_nombre == "Madrid Atocha"
    assert paradas[0].stop_lat == 40.398
    assert paradas[0].stop_lon == -3.693


def test_cargar_paradas_campos_faltantes(tmp_path: Path):
    """Test que ignora paradas con campos obligatorios faltantes."""
    gtfs_dir = tmp_path / "gtfs"
    gtfs_dir.mkdir()

    (gtfs_dir / "stops.txt").write_text(
        "stop_id,stop_name,stop_lat,stop_lon\nMAD,Madrid,40,3\nBCN,,41,2\n"
    )
    (gtfs_dir / "trips.txt").write_text("trip_id,service_id,route_id\nT1,1,R1\n")
    (gtfs_dir / "routes.txt").write_text("route_id,route_short_name\nR1,AVE\n")
    (gtfs_dir / "stop_times.txt").write_text(
        "trip_id,stop_id,stop_sequence,arrival_time\nT1,MAD,1,08:00:00\n"
    )

    loader = GtfsStaticLoader(gtfs_dir)
    paradas = loader.cargar_paradas()

    assert len(paradas) == 1


def test_cargar_rutas_exitoso(gtfs_static_files: Path):
    """Test carga exitosa de rutas."""
    loader = GtfsStaticLoader(gtfs_static_files)
    rutas = loader.cargar_rutas()

    assert len(rutas) == 2

    ruta_r1 = next(r for r in rutas if r.route_id == "R1")
    assert ruta_r1.tipo_servicio == "AVE"
    assert ruta_r1.paradas == ["MAD", "BCN", "ZAZ"]

    ruta_r2 = next(r for r in rutas if r.route_id == "R2")
    assert ruta_r2.tipo_servicio == "AVE"
    assert ruta_r2.paradas == ["MAD", "ZAZ", "BCN"]


def test_cargar_rutas_route_sin_paradas(tmp_path: Path):
    """Test que maneja routes sin paradas asociadas."""
    gtfs_dir = tmp_path / "gtfs"
    gtfs_dir.mkdir()

    (gtfs_dir / "trips.txt").write_text("trip_id,service_id,route_id\nT1,1,R1\n")
    (gtfs_dir / "stop_times.txt").write_text(
        "trip_id,stop_id,stop_sequence,arrival_time\nT1,MAD,1,08:00:00\n"
    )
    (gtfs_dir / "routes.txt").write_text("route_id,route_short_name\nR1,AVE\n")
    (gtfs_dir / "stops.txt").write_text("stop_id,stop_name,stop_lat,stop_lon\nMAD,M,40,3\n")

    loader = GtfsStaticLoader(gtfs_dir)
    rutas = loader.cargar_rutas()

    assert len(rutas) == 1
    assert rutas[0].paradas == ["MAD"]


def test_extraer_codigo_y_fecha_formato_completo(gtfs_static_files: Path):
    """Test parsing de trip_id con código de 5 dígitos."""
    loader = GtfsStaticLoader(gtfs_static_files)
    codigo, fecha = loader._extraer_codigo_y_fecha("T0019012026-02-19")

    assert codigo == "T001901"
    assert fecha == date(2026, 2, 19)


def test_extraer_codigo_y_fecha_codigo_corto(gtfs_static_files: Path):
    """Test parsing de trip_id con código corto."""
    loader = GtfsStaticLoader(gtfs_static_files)
    codigo, fecha = loader._extraer_codigo_y_fecha("T56012026-02-19")

    assert codigo == "T5601"
    assert fecha == date(2026, 2, 19)


def test_extraer_codigo_y_fecha_formato_invalido(gtfs_static_files: Path):
    """Test que lanza ValueError con formato inválido."""
    loader = GtfsStaticLoader(gtfs_static_files)

    with pytest.raises(ValueError, match="no tiene formato esperado"):
        loader._extraer_codigo_y_fecha("invalid_trip_id")


def test_parsear_hora_gtfs_formato_h(gtfs_static_files: Path):
    """Test parsing de hora con formato H:MM:SS."""
    loader = GtfsStaticLoader(gtfs_static_files)
    hora = loader._parsear_hora_gtfs("8:30:00")

    assert hora == time(8, 30)


def test_parsear_hora_gtfs_formato_hh(gtfs_static_files: Path):
    """Test parsing de hora con formato HH:MM:SS."""
    loader = GtfsStaticLoader(gtfs_static_files)
    hora = loader._parsear_hora_gtfs("13:26:00")

    assert hora == time(13, 26)


def test_parsear_hora_gtfs_formato_invalido(gtfs_static_files: Path):
    """Test que lanza ValueError con formato inválido."""
    loader = GtfsStaticLoader(gtfs_static_files)

    with pytest.raises(ValueError, match="Formato de hora inválido"):
        loader._parsear_hora_gtfs("invalid")
