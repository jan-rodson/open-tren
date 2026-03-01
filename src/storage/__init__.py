"""Utilidades para almacenamiento de datos capturados."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src.storage.database import Database
from src.storage.repositories import (
    CirculacionRepository,
    RutaRepository,
)

__all__ = [
    "CirculacionRepository",
    "Database",
    "RutaRepository",
    "save_snapshot",
]


def save_snapshot(
    data: dict[str, Any] | list[Any],  # Any necesario para datos JSON arbitrarios
    timestamp: datetime,
    subdir: str,
    base_path: Path,
) -> Path:
    """Guarda snapshot con timestamp en estructura de directorios.

    Args:
        data: Datos a guardar (deben ser serializables a JSON).
        timestamp: Timestamp de captura.
        subdir: Subdirectorio (ej: "tiempo_real", "avisos").
        base_path: Directorio base para guardar.

    Returns:
        Path del archivo guardado.

    Raises:
        ValueError: Si los datos no son serializables a JSON.
    """
    dir_path = base_path / subdir / timestamp.strftime("%Y-%m-%d")
    dir_path.mkdir(parents=True, exist_ok=True)

    file_path = dir_path / f"{timestamp.strftime('%H-%M-%S')}.json"

    try:
        file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    except (TypeError, ValueError) as e:
        raise ValueError(f"Datos no serializables a JSON: {e}") from e

    return file_path
