# AGENTS.md - Open Tren

**Instrucciones para asistentes AI trabajando en Open Tren.**

## Contexto Rápido

Open Tren captura y archiva datos de puntualidad ferroviaria de Renfe (GTFS-RT, avisos, GTFS estático)

## Comandos

```bash
# Instalar dependencias
uv sync

# Tests
uv run pytest tests/ -v              # Todos los tests
uv run pytest tests/ --cov=src       # Con cobertura

# Calidad de código
uv run ruff check .                  # Linting
uv run ruff check . --fix            # Auto-fix
uv run ruff format .                 # Formatear
uv run basedpyright                  # Type checking

# Ejecución manual
uv run python scripts/captura_tiempo_real.py
uv run python scripts/captura_avisos.py
uv run python scripts/actualizar_gtfs.py
```

## Estructura Rápida

```
open-tren/
├── scripts/              # Entry points ejecutables
│   ├── captura_tiempo_real.py
│   ├── captura_avisos.py
│   └── actualizar_gtfs.py
├── src/
│   ├── fetchers/        # Clientes HTTP para APIs de Renfe
│   ├── storage/         # Persistencia de snapshots
│   ├── processors/      # Procesamiento y transformación
│   └── config.py        # URLs y constantes
├── tests/               # Tests unitarios con pytest
├── docs/
│   ├── steering/        # Normas y guías técnicas
│   ├── fase-0-exploracion.md
│   └── fase-1-1-pipeline-ingestion.md
└── data/                # Datos capturados (gitignored)
    ├── raw/             # Snapshots crudos
    ├── processed/       # Datos procesados
    └── gtfs/            # GTFS estático
```

## Steering Files

Estas son las normas y guías técnicas que definen cómo trabajar en Open Tren. **Deben seguirse obligatoriamente** en todo nuevo código.

- [`docs/steering/convenciones-estilo.md`](docs/steering/convenciones-estilo.md) - Convenciones de código
- [`docs/steering/arquitectura.md`](docs/steering/arquitectura.md) - Arquitectura y patrones
- [`docs/steering/decisiones.md`](docs/steering/decisiones.md) - Decisiones técnicas (ADRs)
- [`docs/steering/testing.md`](docs/steering/testing.md) - Guía de testing

**Importante:** Estos archivos son **documentación viva**. Si necesitas cambiar una convención, actualiza primero el steering file correspondiente.

## Recursos

- **Fase 0 (Exploración):** [`docs/fase-0-exploracion.md`](docs/fase-0-exploracion.md)
- **Fase 1-1 (Ingesta de datos):** [`docs/fase-1-1-pipeline-ingestion.md`](docs/fase-1-1-pipeline-ingestion.md)

**Nota:** Estos documentos reflejan trabajo completado y decisiones históricas. Para las reglas actuales del proyecto, consultar `docs/steering/`.

## Licencia

MIT (código) / CC-BY-4.0 (datos Renfe)
