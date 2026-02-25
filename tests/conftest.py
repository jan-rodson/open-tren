"""Configuración de pytest para tests asíncronos."""

from pathlib import Path

import pytest

pytest_plugins = ["pytest_asyncio"]


@pytest.fixture
def test_user_agent() -> str:
    """User agent para tests."""
    return "TestAgent/1.0"


@pytest.fixture
def sample_gtfs_rt_response() -> dict[str, object]:
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
def sample_avisos_response() -> list[object]:
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


@pytest.fixture
def gtfs_static_files(tmp_path: Path) -> Path:
    """Directorio temporal con archivos GTFS válidos."""
    gtfs_dir = tmp_path / "gtfs"
    gtfs_dir.mkdir()

    (gtfs_dir / "trips.txt").write_text(
        "trip_id,service_id,route_id\n"
        "T0019012026-02-19,1,R1\n"
        "T56012026-02-19,1,R2\n"
        "T0019022026-02-19,1,R1\n"
    )

    (gtfs_dir / "stops.txt").write_text(
        "stop_id,stop_name,stop_lat,stop_lon\n"
        "MAD,Madrid Atocha,40.398,-3.693\n"
        "BCN,Barcelona Sants,41.379,2.140\n"
        "ZAZ,Zaragoza Delicias,41.639,-0.900\n"
    )

    (gtfs_dir / "routes.txt").write_text("route_id,route_short_name\nR1,AVE\nR2,AVE\n")

    (gtfs_dir / "stop_times.txt").write_text(
        "trip_id,stop_id,stop_sequence,arrival_time,departure_time\n"
        "T0019012026-02-19,MAD,1,08:00:00,08:00:00\n"
        "T0019012026-02-19,BCN,2,10:30:00,10:35:00\n"
        "T0019012026-02-19,ZAZ,3,12:00:00,12:00:00\n"
        "T56012026-02-19,MAD,1,14:00:00,14:00:00\n"
        "T56012026-02-19,ZAZ,2,16:30:00,16:35:00\n"
        "T56012026-02-19,BCN,3,18:00:00,18:00:00\n"
        "T0019022026-02-19,MAD,1,20:00:00,20:00:00\n"
        "T0019022026-02-19,BCN,2,22:30:00,22:35:00\n"
        "T0019022026-02-19,ZAZ,3,00:00:00,00:00:00\n"
    )

    return gtfs_dir
