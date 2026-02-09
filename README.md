# Open Tren 🚄

Dashboard de puntualidad ferroviaria en España.

## Visión

Crear un repositorio de datos histórico sobre la puntualidad del transporte ferroviario en España.

## Documentación

- [Plan de Implementación](./docs/open-tren-implementation-proposal.md)
- [Fase 0: Exploración](./docs/fase-0-exploracion.md)

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
