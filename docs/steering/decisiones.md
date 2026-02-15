# Steering: Decisiones Técnicas (ADRs)

Architecture Decision Records para Open Tren.

## ADR-001: Uso de uv en lugar de pip

**Contexto**: Necesitamos un gestor de dependencias rápido y moderno.

**Decisión**: Usar `uv` (de Astral) en lugar de pip.

**Justificación**:

- Instalación 10-100x más rápida
- Resolución de dependencias más eficiente
- Compatible con pyproject.toml
- Mejor para CI/CD

**Consecuencias**:

- Los desarrolladores necesitan instalar uv
- Comandos ligeramente diferentes (`uv run` vs `python`)

---

## ADR-002: Fetchers con tipos genéricos

**Contexto**: `FetcherResult.data` tenía tipo `bytes | dict | list`, causando errores LSP.

**Decisión**: Usar `FetcherResult[T]` con `TypeVar`.

**Implementación**:

```python
T = TypeVar("T", bytes, dict[str, Any], list[Any])

@dataclass(frozen=True)
class FetcherResult(Generic[T]):
    data: T

class GtfsRtFetcher(BaseFetcher[dict[str, Any]]):
    async def fetch(self) -> FetcherResult[dict[str, Any]]: ...
```

**Ventajas**:

- Type safety en tiempo de compilación
- basedpyright detecta errores de tipo
- Cada fetcher expone su tipo concreto

---

## ADR-003: Cada fetcher crea su propio FetcherResult

**Contexto**: El método `FetcherResult.from_response()` causaba problemas de tipos.

**Decisión**: Cada fetcher crea directamente el `FetcherResult` en su método `fetch()`.

**Implementación**:

```python
async def fetch(self) -> FetcherResult[dict[str, Any]]:
    response = await self._http_get(self.url)
    data = response.json()

    return FetcherResult(
        data=data,
        timestamp=datetime.now(UTC),
        url=str(response.url),
        status_code=response.status_code,
    )
```

**Ventajas**:

- Control total sobre el tipo de datos
- Sin métodos helper genéricos problemáticos
- Más explícito y claro

---

## ADR-004: Type checking con basedpyright

**Contexto**: Necesitamos detectar errores de tipo antes de producción.

**Decisión**: Usar basedpyright (fork mejorado de pyright) con modo estricto para `src/`.

**Configuración**:

```toml
[tool.pyright]
include = ["src", "tests", "scripts"]
strict = ["src"]
pythonVersion = "3.12"
typeCheckingMode = "strict"
```

**Ventajas**:

- Detecta errores antes de runtime
- Mejor calidad de código
- Documentación viva mediante tipos

**Consecuencias**:

- Mayor tiempo de desarrollo inicial
- Necesidad de tipar todo correctamente

---

## ADR-005: User-Agent como parámetro obligatorio

**Contexto**: Los fetchers tenían `user_agent` opcional con valor por defecto hardcodeado en `__init__`, lo que creaba inconsistencias.

**Decisión**: Hacer `user_agent` parámetro obligatorio en `__init__` de `BaseFetcher`.

**Justificación**:

- Evita hardcoding del user agent en múltiples lugares
- Permite testing con user agents específicos (fixture `test_user_agent`)
- Facilita cambios globales del user agent desde `src/config.py`
- Promueve consistencia con buenas prácticas de configuración externa

**Consecuencias**:

- Todos los fetchers requieren user_agent explícito al instanciarse
- Scripts deben importar `DEFAULT_USER_AGENT` de `config.py`
- Tests usan fixture `test_user_agent` para aislamiento

**Fecha**: 15 de febrero de 2026
**Commit**: a605553
