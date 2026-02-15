"""Configuración de pytest para tests asíncronos."""

import pytest

pytest_plugins = ["pytest_asyncio"]


@pytest.fixture
def sample_gtfs_rt_response() -> dict:
    """Datos de ejemplo del feed GTFS-RT."""
    return {
        "header": {
            "gtfs_realtime_version": "2.0",
            "timestamp": "1739000000",
        },
        "entity": [
            {
                "id": "12345",
                "trip_update": {
                    "trip": {"trip_id": "AVE_3142"},
                    "stop_time_update": [{"stop_id": "MAD", "departure": {"time": "1739000100"}}],
                },
            }
        ],
    }


@pytest.fixture
def sample_avisos_response() -> list:
    """Datos de ejemplo del feed de avisos."""
    return [
        {
            "id": "aviso1",
            "type": "INCIDENCIA",
            "title": "Incidencia en línea Madrid-Barcelona",
            "description": "Obras en vía...",
            "affectedLines": ["Madrid-Barcelona"],
            "startDate": "2025-02-01",
            "endDate": "2025-02-15",
        }
    ]
