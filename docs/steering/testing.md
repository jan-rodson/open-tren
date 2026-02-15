# Steering: Testing

Guía para escribir tests en Open Tren.

## Framework

- **pytest**: Framework principal
- **pytest-asyncio**: Soporte para async/await
- **respx**: Mock de httpx

## Estructura de Tests

```
tests/
├── conftest.py          # Fixtures compartidos
├── fetchers/
│   ├── test_base.py
│   ├── test_gtfs_rt.py
│   ├── test_avisos.py
│   └── test_gtfs_static.py
└── storage/
    └── test_storage.py
```

## Fixtures

Definir en `conftest.py`:

```python
import pytest

@pytest.fixture
def sample_gtfs_rt_response() -> dict:
    """Ejemplo de respuesta GTFS-RT válida."""
    return {
        "header": {"gtfsRealtimeVersion": "2.0", "timestamp": "1234567890"},
        "entity": [{"id": "test", "tripUpdate": {"trip": {"tripId": "123"}, "delay": 300}}],
    }
```

## Patrones de Testing

### Test de fetcher exitoso

```python
@pytest.mark.asyncio
async def test_fetch_success(sample_gtfs_rt_response):
    """Test de fetch exitoso."""
    url = "https://gtfsrt.renfe.com/trip_updates_LD.json"

    with respx.mock:
        respx.get(url).mock(return_value=httpx.Response(200, json=sample_gtfs_rt_response))

        async with GtfsRtFetcher(url=url) as fetcher:
            result = await fetcher.fetch()
            assert result.data == sample_gtfs_rt_response
            assert result.status_code == 200
```

### Test de error HTTP y timeout

```python
@pytest.mark.asyncio
async def test_fetch_http_error_404():
    """Test de manejo de error 404."""
    url = "https://gtfsrt.renfe.com/trip_updates_LD.json"
    with respx.mock:
        respx.get(url).mock(return_value=httpx.Response(404))
        fetcher = GtfsRtFetcher(url=url)

        with pytest.raises(FetcherError) as exc_info:
            await fetcher.fetch()

        assert "404" in str(exc_info.value)

@pytest.mark.asyncio
async def test_fetch_timeout():
    """Test de manejo de timeout de conexión."""
    url = "https://gtfsrt.renfe.com/trip_updates_LD.json"
    with respx.mock:
        respx.get(url).mock(side_effect=httpx.ConnectTimeout("Timeout"))
        fetcher = GtfsRtFetcher(url=url, timeout=0.1)

        with pytest.raises(FetcherError) as exc_info:
            await fetcher.fetch()

        assert "Timeout" in str(exc_info.value)
```

### Test de reintentos

```python
@pytest.mark.asyncio
async def test_retry_on_failure_then_success():
    """Verifica que reintenta hasta conseguir éxito."""
    url = "https://gtfsrt.renfe.com/trip_updates_LD.json"
    call_count = 0

    def failing_then_success(_request):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise httpx.ConnectTimeout("Timeout")
        return httpx.Response(200, json={"header": {"version": "2.0"}, "entity": []})

    with respx.mock:
        respx.get(url).mock(side_effect=failing_then_success)
        fetcher = GtfsRtFetcher(url=url, max_retries=3)
        result = await fetcher.fetch()

        assert call_count == 3  # 2 fallos + 1 éxito
```

## Comandos

```bash
# Ejecutar todos los tests
uv run pytest tests/ -v

# Con cobertura
uv run pytest tests/ --cov=src

# Un test específico
uv run pytest tests/fetchers/test_gtfs_rt.py::test_fetch_success -v

# Tests fallidos únicamente
uv run pytest tests/ --lf
```

## Reglas

### Nomenclatura

- **Formato**: `test_<funcionalidad>_<escenario>`
- Ejemplos: `test_fetch_success`, `test_fetch_http_error_404`, `test_retry_on_timeout`
- Usar nombres descriptivos que expliquen qué se prueba

### Fixtures

- **Cuándo crear**: datos usados en ≥3 tests, objetos complejos, respuestas de API
- Definir en `conftest.py` para compartir entre tests
- Nombres claros: `sample_gtfs_rt_response`, `mock_fetcher_instance`
- No hardcodear datos directamente en tests

### Organización

- **1 test file por módulo**: `tests/fetchers/test_gtfs_rt.py`
- Agrupar tests relacionados con comentarios `#region` / `#endregion`
- Tests unitarios → 1 función/clase aislada
- Tests de integración → múltiples módulos interactuando
- Tests e2e → scripts completos (ej: `scripts/captura_tiempo_real.py`)

### Cobertura

- **Código nuevo**: mínimo 80%
- **Código modificado**: mínimo 60%
- Ejecutar `uv run pytest tests/ --cov=src` para verificar

### Edge Cases

- Validar inputs límites (valores máximos/minimos)
- Testear null/empty inputs cuando aplique
- Simular datos corruptos o malformados
- Testear condiciones de contorno (boundary conditions)

### Mocks

- **Usar respx** para mockear httpx en fetchers
- Mockear solo I/O (httpx, filesystem), no lógica de negocio
- Tests deben verificar comportamiento real, no implementación
- Configurar mocks para que fallen si no se usan (`assert_called_once()`)

### Docstrings

- **Formato Given-When-Then** o explicación clara
- "Given: configuración inicial del test"
- "When: acción que se ejecuta"
- "Then: resultado esperado"
- Explicar el propósito del test, no solo lo que hace

### Independencia

- **Tests deben ser independientes**: no depender del orden de ejecución
- Cada test debe poder ejecutarse solo
- Limpiar recursos en teardown (usar fixtures con `yield`)
- No compartir estado entre tests

### Errores y Reintentos

- **Casos de error obligatorios**: 404, timeout, JSON inválido, timeouts de red
- Testear reintentos cuando la lógica lo requiera
- Verificar que las excepciones lanzadas sean correctas
- Testear manejo de errores edge cases
