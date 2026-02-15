"""Tests para el módulo storage."""

import json
from datetime import UTC, datetime

from src.storage import save_snapshot


def test_save_snapshot_creates_directory(tmp_path):
    """Test que save_snapshot crea la estructura de directorios correcta."""
    timestamp = datetime(2025, 2, 10, 14, 30, 45, tzinfo=UTC)
    data = {"test": "value"}

    save_snapshot(data, timestamp, "tiempo_real", tmp_path)

    # Verifica estructura de directorios: base_path/tiempo_real/2025-02-10/
    expected_dir = tmp_path / "tiempo_real" / "2025-02-10"
    assert expected_dir.exists()
    assert expected_dir.is_dir()


def test_save_snapshot_file_content(tmp_path):
    """Test que save_snapshot escribe el contenido JSON correcto."""
    timestamp = datetime(2025, 2, 10, 14, 30, 45, tzinfo=UTC)
    data = {"test": "value", "number": 42}

    result = save_snapshot(data, timestamp, "avisos", tmp_path)

    # Verifica que el archivo existe y contiene el JSON correcto
    assert result.exists()
    content = result.read_text()
    assert json.loads(content) == data


def test_save_snapshot_filename_format(tmp_path):
    """Test que el nombre del archivo tiene el formato correcto."""
    timestamp = datetime(2025, 2, 10, 14, 30, 45, tzinfo=UTC)
    data = {"test": "value"}

    result = save_snapshot(data, timestamp, "tiempo_real", tmp_path)

    # Formato esperado: HH-MM-SS.json
    assert result.name == "14-30-45.json"


def test_save_snapshot_returns_path(tmp_path):
    """Test que save_snapshot devuelve el Path correcto."""
    timestamp = datetime(2025, 2, 10, 14, 30, 45, tzinfo=UTC)
    data = {"test": "value"}

    result = save_snapshot(data, timestamp, "tiempo_real", tmp_path)

    expected = tmp_path / "tiempo_real" / "2025-02-10" / "14-30-45.json"
    assert result == expected


def test_save_snapshot_with_list_data(tmp_path):
    """Test que save_snapshot funciona con listas."""
    timestamp = datetime(2025, 2, 10, 14, 30, 45, tzinfo=UTC)
    data = [{"id": 1}, {"id": 2}]

    result = save_snapshot(data, timestamp, "avisos", tmp_path)

    content = result.read_text()
    assert json.loads(content) == data


def test_save_snapshot_unicode(tmp_path):
    """Test que save_snapshot maneja caracteres unicode correctamente."""
    timestamp = datetime(2025, 2, 10, 14, 30, 45, tzinfo=UTC)
    data = {"mensaje": "Incidencia en línea Madrid-Barcelona: ñ, á, é, í, ó, ú"}

    result = save_snapshot(data, timestamp, "avisos", tmp_path)

    content = result.read_text()
    assert "Madrid-Barcelona" in content
    assert "ñ" in content
