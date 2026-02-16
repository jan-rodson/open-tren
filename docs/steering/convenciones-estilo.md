# Steering: Convenciones de Código

Guía detallada de convenciones y estilo para Open Tren.

## Idioma

- **Todo en español**: código, docstrings, comentarios, nombres de variables
- Ejemplos de commits: `"feat(fetchers): add retry logic"`, `"fix(tests): correct timeout"`

## Estilo

- **Line length**: 100 caracteres
- **Python target**: 3.12+ (usar sintaxis moderna: `str | None`, match/case)
- **Linter**: ruff
- **Type checker**: basedpyright (modo estricto para `src/`)

## Nomenclatura

```python
# Clases: PascalCase
class BaseFetcher(ABC, Generic[T]):
class GtfsRtFetcher(BaseFetcher[dict[str, Any]]):

# Funciones/variables: snake_case
async def fetch(self) -> FetcherResult[dict[str, Any]]:
    timestamp_captura = datetime.now(UTC)

# Constantes: UPPER_SNAKE_CASE
GTFS_RT_URL: str = "https://..."
DEFAULT_TIMEOUT: float = 30.0
```

## Type Hints (Obligatorios)

```python
# Genéricos explícitos
async def fetch(self) -> FetcherResult[dict[str, Any]]:

# TypeVars bien definidos
T = TypeVar("T", bytes, dict[str, Any], list[Any])

# Evitar Any cuando sea posible
def save_snapshot(
    data: dict[str, Any] | list[Any],  # ✅ Bien
) -> Path:

# No usar
def save_snapshot(data: dict | list) -> Path:  # ❌ Muy genérico
```

## Decoradores

### @override

Usar `@override` para marcar métodos que sobrescriben métodos de clases base:

```python
from typing import override

@override
async def fetch(self) -> FetcherResult[dict[str, Any]]:
    return await self._http_get(self.url)
```

Mejora legibilidad y permite verificación estática con type checkers.

## Type Assertions

Usar `cast()` cuando el type checker no puede inferir el tipo correcto:

```python
from typing import cast

# En fetchers donde response.json() retorna dict[str, Any]
data = cast(dict[str, Any], response.json())
```

**Preferible:** Definir tipos específicos (TypedDict, type aliases) en lugar de depender de `cast()` frecuentemente.

## Docstrings

Obligatorias para módulos, clases y métodos públicos:

```python
"""Fetcher para datos de tiempo real GTFS-RT de Renfe."""

class GtfsRtFetcher(BaseFetcher[dict[str, Any]]):
    """Fetcher para el feed GTFS-RT de Renfe."""

    async def fetch(self) -> FetcherResult[dict[str, Any]]:
        """
        Obtiene el feed GTFS-RT de Renfe.

        Returns:
            FetcherResult con el JSON parseado y timestamp de captura.

        Raises:
            FetcherError: Si hay error al obtener los datos.
        """
```

## Async/Await

- Usar `async/await` para todas las operaciones I/O
- Los fetchers deben ser context managers: `async with GtfsRtFetcher() as fetcher:`
- Cerrar recursos en `__aexit__`

## Imports

```python
# Orden: stdlib, third-party, local
import json
from datetime import UTC, datetime

import httpx
from tenacity import retry

from ..config import GTFS_RT_URL
from .base import BaseFetcher
```

## Patrones a Seguir

### Fetcher nuevo

```python
class MiFetcher(BaseFetcher[TipoDato]):
    """Docstring obligatoria."""

    async def fetch(self) -> FetcherResult[TipoDato]:
        """Docstring obligatoria."""
        response = await self._http_get(self.url)
        data = self._procesar(response)
        return FetcherResult(
            data=data,
            timestamp=datetime.now(UTC),
            url=str(response.url),
            status_code=response.status_code,
        )
```

### Testing

```python
@pytest.mark.asyncio
async def test_mi_fetcher():
    """Test descriptivo."""
    with respx.mock:
        respx.get(URL).mock(return_value=httpx.Response(200, json={}))
        async with MiFetcher() as fetcher:
            result = await fetcher.fetch()
            assert result.data == {}
```

## Anti-patrones

❌ No hacer:

- Usar `requests` en lugar de `httpx`
- Síncrono en lugar de async
- Ignorar type hints
- Mutar objetos `frozen=True`
- Hardcodear URLs (usar `src/config.py`)
