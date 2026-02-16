# Fase 1-1: Pipeline de Ingesta

**Fecha:** 15 de febrero de 2026  
**Estado:** ✅ COMPLETADA  
**Rama:** feat/ingestion-pipeline

---

## 1. Resumen de la Fase

Esta fase implementa el pipeline de ingesta de datos ferroviarios, capturando automáticamente datos de Renfe desde tres fuentes diferentes y almacenándolos de forma estructurada para análisis posterior.

### Objetivos Alcanzados

- ✅ Implementar fetchers para los 3 endpoints de Renfe
- ✅ Sistema de almacenamiento de snapshots con timestamps
- ✅ Reintentos automáticos con backoff exponencial
- ✅ Tests unitarios con cobertura de casos de error
- ✅ Manejo robusto de errores y validación básica

---

## 2. Arquitectura Implementada

```
┌────────────────────────────────────────────────────────────────────┐
│                             INGESTA                                │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Scripts (scripts/)                       │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌───────────────────┐    │   │
│  │  │ GTFS-RT     │  │ Avisos      │  │ GTFS Estático     │    │   │
│  │  └──────┬──────┘  └──────┬──────┘  └────────┬──────────┘    │   │
│  └─────────┼────────────────┼──────────────────┼───────────────┘   │
│            │                │                  │                   │
│            ▼                ▼                  ▼                   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Fetchers (src/fetchers/)                 │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐ │   │
│  │  │ GtfsRtFetcher│ │ AvisosFetcher│ │ GtfsStaticFetcher    │ │   │
│  │  └──────┬───────┘ └──────┬───────┘ └──────────┬───────────┘ │   │
│  └─────────┼────────────────┼────────────────────┼─────────────┘   │
│            │                │                    │                 │
│            ▼                ▼                    ▼                 │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                 Almacenamiento (src/storage/)               │   │
│  │                                                             │   │
│  │  data/raw/                                                  │   │
│  │  ├── tiempo_real/YYYY-MM-DD/HH-MM-SS.json                   │   │
│  │  ├── avisos/YYYY-MM-DD/HH-MM-SS.json                        │   │
│  │  └── gtfs/google_transit_YYYYMMDD_HHMMSS.zip                │   │
│  │                                                             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 3. Componentes Implementados

### 3.1 Fetchers (`src/fetchers/`)

#### BaseFetcher (`base.py`)

Clase base abstracta para todos los fetchers:

```python
class BaseFetcher(ABC):
    DEFAULT_TIMEOUT = 30.0
    MAX_RETRIES = 3

    async def fetch(self) -> FetcherResult:
        # Implementado por subclases

    async def _http_get(self, url: str, as_json: bool = True) -> FetcherResult:
        # Con reintentos exponenciales usando tenacity
```

**Características:**

- Context manager asíncrono (`async with`)
- Reintentos automáticos con backoff exponencial
- Timeout configurable
- User-Agent personalizable
- Manejo centralizado de errores HTTP

#### GtfsRtFetcher (`gtfs_rt.py`)

Captura el feed de tiempo real GTFS-RT:

**Datos capturados:**

- `tripId`: Identificador del viaje (formato: `[número tren]-[YYYY]-[MM]-[DD]`)
- `delay`: Retraso en segundos (puede ser negativo para adelantos)
- `scheduleRelationship`: Estado del viaje (SCHEDULED, etc.)

#### AvisosFetcher (`avisos.py`)

Captura avisos e incidencias:

**Datos capturados:**

- `paragraph`: Texto descriptivo del aviso
- `chipText`: Fecha o período del aviso
- `link`: URL relativa al detalle
- `tags`: Etiquetas geográficas (Aragón, Cataluña, etc.)

#### GtfsStaticFetcher (`gtfs_static.py`)

Descarga el GTFS estático completo:

**Validación implementada:**

- Verificación de ZIP válido
- Chequeo de archivos GTFS requeridos:
  - `trips.txt` - Viajes programados
  - `stop_times.txt` - Horarios de paradas
  - `stops.txt` - Estaciones
  - `routes.txt` - Rutas

**Estructura de almacenamiento:**

```
data/gtfs/
├── google_transit_YYYYMMDD_HHMMSS.zip  # Backup versionado
├── latest.zip → symlink al más reciente
└── renfe_av_ld_md/                     # Extracción actual
    ├── agency.txt
    ├── routes.txt
    ├── stops.txt
    ├── stop_times.txt
    ├── trips.txt
    ├── calendar.txt
    └── calendar_dates.txt
```

### 3.2 Almacenamiento (`src/storage/`)

#### Sistema de Snapshots

```python
def save_snapshot(
    data: dict | list,
    timestamp: datetime,
    subdir: str,
    base_path: Path,
) -> Path
```

**Estructura de directorios:**

```
data/raw/
├── tiempo_real/
│   └── 2026-02-08/
│       ├── 10-30-00.json
│       ├── 10-35-00.json
│       └── ... (cada 5 min)
│
├── avisos/
│   └── 2026-02-08/
│       ├── 10-30-00.json
│       └── ... (cada 15 min)
│
└── gtfs/
    ├── google_transit_20260208_030000.zip
    ├── google_transit_20260201_030000.zip
    └── latest.zip → symlink
```

**Características:**

- Nombres de archivo con timestamp ISO
- JSON con indentación legible
- Creación automática de directorios
- Serialización con manejo de errores

### 3.3 Scripts (`scripts/`)

#### captura_tiempo_real.py

```bash
uv run python scripts/captura_tiempo_real.py
```

Flujo:

1. Crea `GtfsRtFetcher()`
2. Ejecuta `fetch()` con reintentos
3. Guarda snapshot en `data/raw/tiempo_real/`
4. Loguea resultado

#### captura_avisos.py

```bash
uv run python scripts/captura_avisos.py
```

Flujo idéntico para avisos.

#### actualizar_gtfs.py

```bash
uv run python scripts/actualizar_gtfs.py
```

Flujo:

1. Descarga ZIP con `GtfsStaticFetcher`
2. Valida contenido GTFS
3. Guarda con timestamp
4. Extrae en `data/gtfs/renfe_av_ld_md/`
5. Actualiza symlink `latest.zip`

### 3.4 Configuración (`src/config.py`)

```python
# Endpoints
GTFS_RT_URL = "https://gtfsrt.renfe.com/trip_updates_LD.json"
GTFS_STATIC_URL = "https://ssl.renfe.com/gtransit/Fichero_AV_LD/google_transit.zip"
AVISOS_URL = "https://www.renfe.com/.../noticeresults.json"

# Intervalos
CAPTURE_INTERVAL_SECONDS = 300  # 5 minutos

# Umbrales de retraso
DELAY_THRESHOLD_PUNTUAL = 5
DELAY_THRESHOLD_GRAVE = 15
DELAY_THRESHOLD_MUY_GRAVE = 30

# Tipos de servicio
TIPOS_SERVICIO = ("AVE", "AVLO", "ALVIA", "EUROMED", "MD", "Intercity", "Trenhotel")
```

---

## 4. Tests Implementados

| Módulo                    | Cobertura |
| ------------------------- | --------- |
| `fetchers/base.py`        | 95%       |
| `fetchers/gtfs_rt.py`     | 100%      |
| `fetchers/avisos.py`      | 100%      |
| `fetchers/gtfs_static.py` | 100%      |
| `storage/`                | 83%       |

---

## 5. Dependencias

### 5.1 Producción (`pyproject.toml`)

```toml
dependencies = [
    "httpx>=0.27.0",      # HTTP client asíncrono
    "pydantic>=2.0",      # Validación de datos
    "tenacity>=9.0",      # Reintentos con backoff
]
```

### 5.2 Desarrollo

```toml
dev = [
    "pytest>=8.0",        # Framework de testing
    "pytest-asyncio",     # Soporte async en tests
    "respx>=0.21",        # Mock de httpx
    "ruff",               # Linter y formatter
]
```

---

## 6. Decisiones Técnicas

### 6.1 Uso de `uv` vs `pip`

**Decisión:** Usar `uv` como gestor de dependencias

**Justificación:**

- Instalación más rápida
- Resolución de dependencias más eficiente
- Compatible con `pyproject.toml`
- Mejor para CI/CD

### 6.2 Estructura de Datos

**Decisión:** Guardar snapshots JSON crudos en lugar de procesados

**Justificación:**

- Permite re-procesar si cambia la lógica
- Facilita debugging
- Datos de respaldo en formato original
- Procesamiento se hará en fase posterior

### 6.3 Manejo de Errores

**Decisión:** Excepciones personalizadas (`FetcherError`)

**Justificación:**

- Mensajes de error claros con contexto (URL, status code)
- Facilita debugging en producción
- Permite diferenciar tipos de errores

### 6.4 Tests con `respx`

**Decisión:** Usar `respx` en lugar de `unittest.mock`

**Justificación:**

- Mock específico para `httpx`
- Sintaxis más limpia
- Soporte para async/await
- Verificación de requests

---

## 7. Próximos Pasos

1. **Validación de respuestas y procesadores de datos**
2. **Almacenamiento en Parquet/BDD**
3. **Dashboard MVP**

---

## 8. Referencias

- [Fase 0: Exploración](../fase-0-exploracion.md)
- [Plan de Implementación](../open-tren-implementation-proposal.md)
- [TODO](../../../TODO.md)
