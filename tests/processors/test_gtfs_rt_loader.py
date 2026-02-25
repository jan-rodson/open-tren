"""Tests para GtfsRtLoader."""

import json
from pathlib import Path

import pytest

from src.processors.gtfs_rt import GtfsRtLoader


def test_cargar_vacio(tmp_path: Path):
    """Test parseo de JSON vacío."""
    data = {"entity": []}
    file_path = tmp_path / "gtfs_rt.json"
    file_path.write_text(json.dumps(data), encoding="utf-8")

    parser = GtfsRtLoader(file_path)
    result = parser.cargar_actualizaciones()
    assert result == []


def test_cargar_con_actualizaciones(tmp_path: Path):
    """Test parseo con actualizaciones."""
    data = {
        "entity": [
            {
                "id": "TUUPDATE_1700012026-02-16",
                "tripUpdate": {
                    "trip": {
                        "tripId": "1700012026-02-16",
                        "scheduleRelationship": "SCHEDULED",
                    },
                    "delay": 60,
                },
            }
        ]
    }
    file_path = tmp_path / "gtfs_rt.json"
    file_path.write_text(json.dumps(data), encoding="utf-8")

    parser = GtfsRtLoader(file_path)
    result = parser.cargar_actualizaciones()
    assert len(result) == 1
    assert result[0].trip_id == "1700012026-02-16"
    assert result[0].delay_segundos == 60
    assert result[0].schedule_relationship == "SCHEDULED"


def test_cargar_multiple_actualizaciones(tmp_path: Path):
    """Test parseo con múltiples actualizaciones."""
    data = {
        "entity": [
            {
                "id": "1",
                "tripUpdate": {
                    "trip": {"tripId": "0019012026-02-19"},
                    "delay": 300,
                },
            },
            {
                "id": "2",
                "tripUpdate": {
                    "trip": {"tripId": "0019022026-02-19"},
                    "delay": -60,
                },
            },
        ]
    }
    file_path = tmp_path / "gtfs_rt.json"
    file_path.write_text(json.dumps(data), encoding="utf-8")

    parser = GtfsRtLoader(file_path)
    result = parser.cargar_actualizaciones()
    assert len(result) == 2
    assert result[0].delay_segundos == 300
    assert result[1].delay_segundos == -60


def test_cargar_sin_trip_update(tmp_path: Path):
    """Test que ignora entidades sin tripUpdate."""
    data = {
        "entity": [
            {"id": "1", "tripUpdate": None},
            {"id": "2"},
        ]
    }
    file_path = tmp_path / "gtfs_rt.json"
    file_path.write_text(json.dumps(data), encoding="utf-8")

    parser = GtfsRtLoader(file_path)
    result = parser.cargar_actualizaciones()
    assert result == []


def test_archivo_no_existe(tmp_path: Path):
    """Test que lanza error si el archivo no existe."""
    file_path = tmp_path / "no_existe.json"

    with pytest.raises(FileNotFoundError, match="Archivo GTFS-RT no encontrado"):
        GtfsRtLoader(file_path)


def test_json_invalido(tmp_path: Path):
    """Test que maneja JSON malformado."""
    file_path = tmp_path / "gtfs_rt.json"
    file_path.write_text("{invalid json}", encoding="utf-8")

    parser = GtfsRtLoader(file_path)

    with pytest.raises(json.JSONDecodeError):
        parser.cargar_actualizaciones()


def test_delay_none(tmp_path: Path):
    """Test que ignora entidades con delay=None."""
    data = {
        "entity": [
            {
                "tripUpdate": {
                    "trip": {"tripId": "0019012026-02-19"},
                    "delay": None,
                }
            }
        ]
    }
    file_path = tmp_path / "gtfs_rt.json"
    file_path.write_text(json.dumps(data), encoding="utf-8")

    parser = GtfsRtLoader(file_path)
    result = parser.cargar_actualizaciones()

    assert len(result) == 0


def test_schedule_relationship_distintos(tmp_path: Path):
    """Test con diferentes scheduleRelationship."""
    data = {
        "entity": [
            {
                "id": "1",
                "tripUpdate": {
                    "trip": {
                        "tripId": "0019012026-02-19",
                        "scheduleRelationship": "ADDED",
                    },
                    "delay": 60,
                },
            },
            {
                "id": "2",
                "tripUpdate": {
                    "trip": {
                        "tripId": "0019022026-02-19",
                        "scheduleRelationship": "CANCELED",
                    },
                    "delay": 0,
                },
            },
        ]
    }
    file_path = tmp_path / "gtfs_rt.json"
    file_path.write_text(json.dumps(data), encoding="utf-8")

    parser = GtfsRtLoader(file_path)
    result = parser.cargar_actualizaciones()

    assert len(result) == 2
    assert result[0].schedule_relationship == "ADDED"
    assert result[1].schedule_relationship == "CANCELED"


def test_entidad_campos_faltantes_permitidos(tmp_path: Path):
    """Test que ignora entidades sin tripUpdate."""
    data = {
        "entity": [
            {"id": "1", "vehicle": {"id": "v1"}},
            {"id": "2", "alert": {"cause": "WEATHER"}},
        ]
    }
    file_path = tmp_path / "gtfs_rt.json"
    file_path.write_text(json.dumps(data), encoding="utf-8")

    parser = GtfsRtLoader(file_path)
    result = parser.cargar_actualizaciones()

    assert result == []


def test_trip_id_vacio(tmp_path: Path):
    """Test que ignora entidades con tripId vacío."""
    data = {
        "entity": [
            {
                "tripUpdate": {
                    "trip": {"tripId": ""},
                    "delay": 60,
                }
            }
        ]
    }
    file_path = tmp_path / "gtfs_rt.json"
    file_path.write_text(json.dumps(data), encoding="utf-8")

    parser = GtfsRtLoader(file_path)
    result = parser.cargar_actualizaciones()

    assert len(result) == 0
