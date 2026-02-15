# Open Tren 🚄

Dashboard de puntualidad ferroviaria en España.

Captura y archiva automáticamente datos de puntualidad e incidencias de trenes Renfe en tiempo real, creando el primer repositorio público de datos históricos sobre puntualidad ferroviaria en España.

## Estado del Proyecto

| Fase                                    | Estado              |
| --------------------------------------- | ------------------- |
| Fase 0: Exploración                     | ✅ Completada       |
| Fase 1: Pipeline de Ingesta y procesado | ⏳ En proceso       |
| Fase 2: Dashboard para visualización    | ⏳ En planificación |

## ¿Qué hace?

- **Descarga** de horarios semanales de trenes
- **Captura constante** de datos de trenes con retrasos en tiempo real
- **Archivo de avisos** e incidencias de Renfe
- **Almacenamiento versionado** de snapshots en formato JSON

## Stack Tecnológico

- **Python 3.12+** con type hints estrictos
- **httpx** - Cliente HTTP asíncrono
- **pydantic** - Validación de datos
- **pytest** - Testing
- **ruff** - Linter y formatter
- **basedpyright** - Type checking
- **uv** - Gestor de dependencias

## Instalación

```bash
# Clonar repositorio
git clone https://github.com/jan-rodson/open-tren.git
cd open-tren

# Instalar dependencias
uv sync
```

## Uso

### Captura manual de datos

```bash
# Capturar datos de tiempo real
uv run python scripts/captura_tiempo_real.py

# Capturar avisos e incidencias
uv run python scripts/captura_avisos.py

# Actualizar GTFS estático
uv run python scripts/actualizar_gtfs.py
```

### Tests y calidad de código

```bash
# Ejecutar tests
uv run pytest tests/ -v

# Ejecutar linter
uv run ruff check .
```

## Estructura de Datos

Los datos capturados se almacenan en:

```
data/
├── raw/
│   ├── tiempo_real/    # Snapshots GTFS-RT (JSON)
│   └── avisos/         # Avisos Renfe (JSON)
└── gtfs/
    └── renfe_av_ld_md/ # GTFS estático descomprimido
```

## Documentación

- **[Fase 0: Exploración](./docs/fase-0-exploracion.md)** - Validación de endpoints y estructura de datos
- **[Fase 1-1: Pipeline de Ingesta](./docs/fase-1-1-pipeline-ingestion.md)** - Implementación del sistema de captura

## Licencia

- **Código:** [MIT License](./LICENSE)
- **Datos:** CC-BY-4.0 (datos de Renfe Operadora)

---

**Nota:** Este es un proyecto independiente sin afiliación oficial con Renfe.
