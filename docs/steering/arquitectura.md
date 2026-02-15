# Steering: Arquitectura

Documentación de la arquitectura del sistema.

## Flujo de Datos

```
┌─────────────────┐     ┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Endpoints     │───▶│  Fetchers   │───▶│   Storage    │───▶│  Dashboard  │
│    Renfe        │     │   (async)   │     │  (JSON/ZIP)  │     │  (Futuro)   │
└─────────────────┘     └─────────────┘     └──────────────┘     └─────────────┘
```

## Componentes

### 1. Fetchers (`src/fetchers/`)

**Diseño**: Genéricos con tipos específicos usando `FetcherResult[T]`

```python
T = TypeVar("T", bytes, dict[str, Any], list[Any])

@dataclass(frozen=True)
class FetcherResult(Generic[T]):
    data: T  # Tipo específico según el fetcher
    timestamp: datetime
    url: str
    status_code: int = 200
```

**Implementaciones**:

- `GtfsRtFetcher(BaseFetcher[dict[str, Any]])` → JSON parseado
- `AvisosFetcher(BaseFetcher[list[Any]])` → Lista de avisos
- `GtfsStaticFetcher(BaseFetcher[bytes])` → Contenido ZIP

**Características**:

- Context manager asíncrono
- Reintentos automáticos con backoff (tenacity)
- Timeout configurable
- User-Agent obligatorio (importado de config.py)

### 2. Storage (`src/storage/`)

Sistema de snapshots con estructura de directorios:

```
data/raw/
├── tiempo_real/YYYY-MM-DD/HH-MM-SS.json
├── avisos/YYYY-MM-DD/HH-MM-SS.json
└── gtfs/google_transit_YYYYMMDD_HHMMSS.zip
```

### 3. Scripts (`scripts/`)

- `captura_tiempo_real.py` - Ejecuta GtfsRtFetcher
- `captura_avisos.py` - Ejecuta AvisosFetcher
- `actualizar_gtfs.py` - Descarga y extrae GTFS

## Endpoints de Datos

| Fuente        | URL                                                                                                                                                              | Formato |
| ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| GTFS-RT       | `https://gtfsrt.renfe.com/trip_updates_LD.json`                                                                                                                  | JSON    |
| Avisos        | `https://www.renfe.com/content/renfe/es/es/grupo-renfe/comunicacion/renfe-al-dia/avisos/jcr:content/root/responsivegrid/rfincidentreports_co.noticeresults.json` | JSON    |
| GTFS Estático | `https://ssl.renfe.com/gtransit/Fichero_AV_LD/google_transit.zip`                                                                                                | ZIP     |

**Nota**: GTFS-RT solo contiene trenes con retrasos, no los puntuales.

## Estructura de Directorios

```
open-tren/
├── scripts/              # Scripts ejecutables
├── src/
│   ├── fetchers/        # Clases para descargar datos
│   ├── models/          # Modelos Pydantic
│   ├── processors/      # Procesadores de datos
│   ├── storage/         # Almacenamiento
│   └── config.py        # Constantes y URLs
├── tests/               # Tests unitarios
├── data/                # Datos (gitignored)
└── docs/                # Documentación
```
