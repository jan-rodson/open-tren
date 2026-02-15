# Open Tren 🚄

Dashboard de puntualidad ferroviaria en España.

Captura y archiva automáticamente datos de puntualidad e incidencias de trenes Renfe en tiempo real.

## Visión

Crear un repositorio de datos histórico sobre la puntualidad del transporte ferroviario en España.

## Documentación

### Fases Completadas
- [Fase 0: Exploración](./docs/fase-0-exploracion.md) - Validación de endpoints y viabilidad
- [Fase 1-1: Pipeline de Ingesta](./docs/fase-1-1-pipeline-ingestion.md) - Captura automatizada de datos

### Planificación y Guías
- [Plan de Implementación](./docs/open-tren-implementation-proposal.md) - Roadmap inicial del proyecto

## Desarrollo

### Instalación

```bash
uv sync
```

### Ejecutar scripts

```bash
# Capturar datos de tiempo real
uv run python scripts/captura_tiempo_real.py

# Capturar avisos
uv run python scripts/captura_avisos.py

# Actualizar GTFS estático
uv run python scripts/actualizar_gtfs.py
```

### Tests

```bash
uv run pytest tests/
```

## Licencia

Este proyecto se distribuye bajo [MIT License](./LICENSE).
