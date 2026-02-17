# Plan de Implementación - Open Tren

## 📋 Tabla de Contenidos

- [Arquitectura General](#arquitectura-general)
- [Infraestructura](#infraestructura)
- [Schema de Base de Datos](#schema-de-base-de-datos)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Flujo de Trabajo en Paralelo](#flujo-de-trabajo-en-paralelo)
- [Fase 1: Pipeline de Ingestión](#fase-1-pipeline-de-ingestión)
- [Fase 2: Dashboard](#fase-2-dashboard)
- [Cronograma](#cronograma)
- [Checklist de Configuración Neon](#checklist-de-configuración-neon)
- [Próximos Pasos](#próximos-pasos)

---

## Arquitectura General

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        INGESTIÓN (Backend)                         │
│  GitHub Actions (cron cada 5 min)                                │
│         ↓                                                            │
│  Script Python (httpx, polars, psycopg)                         │
│         ↓                                                            │
│  ├── Feed tiempo real Renfe (JSON GTFS-RT) → retrasos          │
│  ├── Feed avisos Renfe (JSON) → incidencias                    │
│  └── GTFS estático (ZIP semanal) → horarios               │
│         ↓                                                            │
│  Procesador Python                                                   │
│  ├── Cruce GTFS estático + GTFS-RT (trenes programados)      │
│  ├── Cálculo de retrasos (real vs programado)                  │
│  └── Normalización y validación                                       │
│         ↓                                                            │
│  Neon PostgreSQL v17 (eu-central-1)                                │
│  ├── Tablas: circulaciones, incidencias, stats_diarias           │
│  ├── Índices optimizados para queries de tiempo                    │
│  └── Connection pooling (PgBouncer built-in)                     │
└─────────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                      FRONTEND (Dashboard)                        │
│  Streamlit (MVP) → Dash (Producción futuro)                   │
│         ↓                                                            │
│  ┌───────────────────────────────────────────────────────────────┐      │
│  │  Vista Principal: Estado Actual                               │      │
│  │  ├── KPIs: Trenes en circulación, puntualidad, etc.  │      │
│  │  ├── Mapa: Estaciones + trenes con color por retraso       │      │
│  │  ├── Filtros: Tipo servicio, línea, solo retrasos         │      │
│  │  └── Tabla: Detalle de trenes                              │      │
│  ├───────────────────────────────────────────────────────────────┤      │
│  │  Vista Incidencias: Avisos activos                        │      │
│  │  ├── Tarjetas expandibles por severidad                        │      │
│  │  ├── Timeline histórico                                        │      │
│  │  └── Filtros por tipo de incidencia                        │      │
│  ├───────────────────────────────────────────────────────────────┤      │
│  │  Vista Histórico: Estadísticas                              │      │
│  │  ├── Gráficos: Evolución puntualidad, distribución retrasos   │      │
│  │  ├── Tablas: Top rutas con peor puntualidad              │      │
│  │  └── Selector de rango temporal                             │      │
│  └───────────────────────────────────────────────────────────────┘      │
│                                                                 │
│  Hosting: Streamlit Cloud (gratis) → VPS Hetzner (futuro)      │
│                                                                 │
│  Datos: Leídos desde Neon PostgreSQL                              │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Infraestructura

### Proveedor de Base de Datos: Neon PostgreSQL v17

**Configuración:**

- **Región:** `eu-central-1` (Frankfurt) o `eu-west-1` (Irlanda)
- **Versión PostgreSQL:** 17 (estable)
- **Compute:** Autoscaling (Min: 0.25 CU, Max: 1 CU)
- **Storage:** Bottomless (pagas solo lo que usas)

**Costes estimados (primer año):**

- **Storage:** ~0.2-0.5 GB → $0.10-0.25/mes
- **Compute:** ~15-20 CU-hours/mes (burst pipeline) → $2-3/mes
- **Total:** ~$20-35/año (Free tier cubre los primeros meses)

### Git y Worktrees

```
open-tren/
├── main                    → Branch principal
├── feat/ingestion-pipeline → Rama pipeline (tu trabajo)
├── streamlit-dashboard    → Rama dashboard (mi trabajo)
└── docs/                  → Documentación compartida
```

**Desarrollo en paralelo:**

- Dos worktrees independientes
- Compartir `docs/` y configuración común
- Cada rama tiene su `pyproject.toml` y estructura

---

## Schema de Base de Datos

### Tabla 1: `circulaciones`

**Propósito:** Almacenar snapshots de trenes en circulación

```sql
CREATE TABLE circulaciones (
    id SERIAL PRIMARY KEY,
    timestamp_captura TIMESTAMPTZ NOT NULL,
    codigo_tren VARCHAR(20) NOT NULL,
    tipo_servicio VARCHAR(10) NOT NULL,  -- AVE, ALVIA, AVLO, MD, etc.
    linea VARCHAR(100),
    origen VARCHAR(100),
    destino VARCHAR(100),
    hora_salida_programada TIME,
    hora_llegada_programada TIME,
    retraso_minutos INTEGER NOT NULL,
    estado VARCHAR(20) NOT NULL,  -- PROGRAMADO, EN_RUTA, LLEGADO, CANCELADO
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_circulaciones_timestamp ON circulaciones(timestamp_captura);
CREATE INDEX idx_circulaciones_tren ON circulaciones(codigo_tren);
CREATE INDEX idx_circulaciones_tipo ON circulaciones(tipo_servicio);
```

**Volumen estimado:**

- ~1.7M filas/mes
- ~57,600 filas/día (288 snapshots × ~200 trenes)
- Tamaño por fila: ~100 bytes
- ~150-200 MB/mes comprimido en PostgreSQL

### Tabla 2: `incidencias`

**Propósito:** Almacenar avisos de Renfe

```sql
CREATE TABLE incidencias (
    id SERIAL PRIMARY KEY,
    id_aviso VARCHAR(50) UNIQUE NOT NULL,  -- ID del aviso de Renfe
    tipo VARCHAR(50) NOT NULL,  -- OBRAS, INCIDENCIA, HUELGA, METEOROLOGIA
    titulo VARCHAR(200) NOT NULL,
    descripcion TEXT,
    lineas_afectadas TEXT[],  -- Array de strings (postgres nativo)
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE,
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_incidencias_activas ON incidencias(activo) WHERE activo = TRUE;
CREATE INDEX idx_incidencias_fecha ON incidencias(fecha_inicio);
```

**Volumen estimado:**

- ~5-20 incidencias/mes
- ~10-50 KB por incidencia

### Tabla 3: `stats_diarias`

**Propósito:** Agregación diaria para histórico y dashboard

```sql
CREATE TABLE stats_diarias (
    id SERIAL PRIMARY KEY,
    fecha DATE NOT NULL,
    tipo_servicio VARCHAR(10),
    linea VARCHAR(100),
    total_circulaciones INTEGER,
    retraso_medio DECIMAL(5,2),
    retraso_mediana DECIMAL(5,2),
    retraso_maximo INTEGER,
    puntuales INTEGER,  -- retraso <= 5 min
    con_retraso INTEGER,  -- retraso > 5 min
    retraso_grave INTEGER,  -- retraso > 15 min
    retraso_muy_grave INTEGER,  -- retraso > 30 min
    UNIQUE(fecha, tipo_servicio, linea)
);

CREATE INDEX idx_stats_fecha ON stats_diarias(fecha);
```

**Volumen estimado:**

- ~30-100 filas/día (una por tipo de servicio × líneas principales)
- ~1,000-3,000 filas/mes
- ~50 KB/mes

### Tabla 4: `estaciones` (opcional para mapa)

**Propósito:** Datos de estaciones para visualización en mapa

```sql
CREATE TABLE estaciones (
    id SERIAL PRIMARY KEY,
    stop_id VARCHAR(50) UNIQUE NOT NULL,  -- ID del GTFS
    nombre VARCHAR(100) NOT NULL,
    lat DECIMAL(9,6) NOT NULL,
    lon DECIMAL(9,6) NOT NULL,
    es_principal BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_estaciones_latlon ON estaciones USING GIST (lat, lon);
```

**Volumen estimado:**

- ~100-200 estaciones principales
- ~10 KB total

---

## Estructura del Proyecto

```
open-tren/
├── .github/
│   └── workflows/
│       ├── captura_tiempo_real.yml    # Cada 5 min
│       ├── captura_avisos.yml         # Cada 15 min
│       └── migrar_schema.yml           # Ejecución inicial
├── data/
│   └── gtfs/                         # GTFS estático (no en git)
├── docs/
│   ├── fase-0-exploracion.md
│   ├── fase-1-ingestion.md              # ← ESTE FICHERO
│   └── fase-2-dashboard.md              # ← ESTE FICHERO
├── src/
│   ├── __init__.py
│   ├── config.py                         # URLs, constantes
│   ├── fetchers/
│   │   ├── __init__.py
│   │   ├── tiempo_real.py            # httpx → JSON GTFS-RT
│   │   ├── avisos.py                 # httpx → JSON avisos
│   │   └── gtfs.py                   # httpx → ZIP GTFS
│   ├── processors/
│   │   ├── __init__.py
│   │   ├── calcular_retrasos.py     # Cruce datos
│   │   └── normalizar.py             # Limpieza
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── postgres_store.py         # psycopg → Neon
│   │   └── schema.sql               # Schema inicial
│   └── models/
│       ├── __init__.py
│       └── schemas.py                 # Pydantic (opcional)
├── dashboard/
│   ├── app.py                         # Entry point Streamlit
│   ├── pages/
│   │   ├── 1_🚄_Estado_Actual.py
│   │   ├── 2_⚠️_Incidencias.py
│   │   └── 3_📊_Histórico.py
│   ├── components/
│   │   ├── mapa.py
│   │   ├── tabla_trenes.py
│   │   ├── kpis.py
│   │   └── graficos.py
│   └── utils/
│       ├── __init__.py
│       ├── data_loader.py             # Lee de Neon
│       └── styles.py
├── scripts/
│   ├── captura_tiempo_real.py     # Entry point GH Actions
│   ├── captura_avisos.py
│   └── migrar_schema.py
├── tests/
│   ├── test_fetchers.py
│   ├── test_processors.py
│   └── test_storage.py
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## Flujo de Trabajo en Paralelo

### Pipeline (Rama `feat/ingestion-pipeline`)

```
Fase 1.1: Setup
├── Crear estructura de directorios
├── Configurar pyproject.toml
├── Crear fetchers básicos
└── Tests unitarios

Fase 1.2: Fetchers
├── tiempo_real.py: Descargar GTFS-RT cada 5 min
├── avisos.py: Descargar avisos cada 15 min
└── gtfs.py: Descargar GTFS estático semanal

Fase 1.3: Procesadores
├── calcular_retrasos.py: Cruce GTFS estático + GTFS-RT
├── normalizar.py: Validación y limpieza
└── Tests de integración

Fase 1.4: Storage
├── postgres_store.py: Escritura a Neon
├── Implementar batch inserts
├── Connection pooling
└── Tests de carga

Fase 1.5: Automatización
├── Configurar GitHub Actions (cron 5 min)
├── Script captura_tiempo_real.py
├── Script captura_avisos.py
└── Tests en producción
```

### Dashboard (Rama `streamlit-dashboard`)

```
Fase 2.1: Setup
├── Crear estructura dashboard/
├── Configurar Streamlit
├── data_loader.py básico
└── Página Estado Actual (placeholder)

Fase 2.2: Páginas principales
├── Estado Actual
│   ├── KPIs
│   ├── Mapa simple (folium)
│   └── Tabla con filtros
├── Incidencias
│   ├── Tarjetas expandibles
│   └── Timeline
└── Histórico
    ├── Gráfico de tendencia
    └── Tabla de rutas

Fase 2.3: Componentes reutilizables
├── mapa.py: Componente de mapa
├── tabla_trenes.py: Tabla con filtros
├── kpis.py: Métricas principales
└── graficos.py: Plotly charts

Fase 2.4: Despliegue
├── Test local (streamlit run app.py)
├── Responsive design (CSS)
└── Despliegue Streamlit Cloud
```

**Punto de integración:**

- Dashboard puede leer de PostgreSQL con tablas VACÍAS
- Solo necesita el schema definido (estructura y tipos)
- El pipeline poblara los datos cuando esté listo

---

## Fase 1: Pipeline de Ingestión

### Objetivos

- Capturar datos de forma automatizada cada 5 minutos
- Procesar y cruzar GTFS estático con GTFS-RT
- Almacenar en Neon PostgreSQL
- GitHub Actions para automatización

### Dependencias Python

```toml
[project]
name = "open-tren"
version = "0.1.0"
dependencies = [
    "httpx>=0.27",
    "polars>=0.20",
    "psycopg[binary]>=3.1",
    "pydantic>=2.0",
    "python-dotenv>=1.0",
    "gtfs-kit>=5.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "ruff>=0.1",
    "pytest-cov>=4.0",
]

[tool.pytest.iniOptions]
addopts = "-ra -q"
testpaths = ["tests"]
```

### Tareas críticas

| Tarea                    | Prioridad | Estimado   | Responsable |
| ------------------------ | --------- | ---------- | ----------- |
| Setup inicial estructura | Alta      | 2-4h       | Pipeline    |
| Fetch tiempo_real.py     | Alta      | 4-6h       | Pipeline    |
| Fetch avisos.py          | Alta      | 2-3h       | Pipeline    |
| Procesador cruzar datos  | Alta      | 6-8h       | Pipeline    |
| postgres_store.py        | Alta      | 4-6h       | Pipeline    |
| GitHub Actions config    | Alta      | 2-4h       | Pipeline    |
| Tests integración        | Alta      | 4-6h       | Pipeline    |
| Documentation            | Media     | 2-3h       | Pipeline    |
| **TOTAL Fase 1**         |           | **24-40h** |             |

---

## Fase 2: Dashboard

### Objetivos

- Dashboard funcional accesible públicamente
- Diseño responsive (mobile-first)
- Tres vistas principales: Estado Actual, Incidencias, Histórico

### Dependencias Python

```toml
[project.optional-dependencies]
dashboard = [
    "streamlit>=1.30",
    "plotly>=5.18",
    "folium>=0.15",
    "streamlit-folium>=0.15",
]
```

### Páginas principales

#### Vista 1: Estado Actual

**Componentes:**

- KPIs: Trenes en circulación, puntualidad, retraso medio, incidencias activas
- Mapa: Estaciones principales + trenes con colores por retraso
- Filtros: Tipo de servicio, línea, solo trenes con retraso
- Tabla: Lista de trenes con ordenamiento por retraso

#### Vista 2: Incidencias

**Componentes:**

- Tarjetas expandibles por severidad (ALTA/MEDIA/BAJA)
- Filtros por tipo de incidencia
- Timeline histórico
- Detalle de líneas afectadas

#### Vista 3: Histórico

**Componentes:**

- Gráfico de evolución puntualidad (últimos 7/30/90 días)
- Distribución de retrasos (histograma)
- Tabla de rutas con peor puntualidad
- Selector de rango temporal

### Tareas críticas

| Tarea                       | Prioridad | Estimado   | Responsable |
| --------------------------- | --------- | ---------- | ----------- |
| Setup estructura dashboard  | Alta      | 1-2h       | Dashboard   |
| data_loader.py (PostgreSQL) | Alta      | 3-5h       | Dashboard   |
| Página Estado Actual        | Alta      | 6-8h       | Dashboard   |
| Página Incidencias          | Media     | 4-6h       | Dashboard   |
| Página Histórico            | Media     | 4-6h       | Dashboard   |
| Componentes reutilizables   | Media     | 4-6h       | Dashboard   |
| Responsive CSS              | Baja      | 2-3h       | Dashboard   |
| Despliegue local            | Alta      | 1-2h       | Dashboard   |
| Streamlit Cloud deploy      | Media     | 1-2h       | Dashboard   |
| Documentation               | Baja      | 1-2h       | Dashboard   |
| **TOTAL Fase 2**            |           | **26-44h** |             |

---

## Cronograma

### Semana 1-2: Setup + Pipeline básico

```
Día 1-2: Setup inicial
  ├── Estructura de directorios
  ├── Configuración Neon
  ├── pyproject.toml y requirements.txt
  └── Schema SQL en Neon

Día 3-5: Fetchers
  ├── tiempo_real.py (GTFS-RT)
  ├── avisos.py
  └── gtfs.py (GTFS estático)

Día 6-8: Procesadores
  ├── calcular_retrasos.py
  ├── normalizar.py
  └── Tests unitarios

Día 9-10: Storage + Automatización
  ├── postgres_store.py
  ├── GitHub Actions (captura_tiempo_real.yml)
  └── Tests de integración
```

### Semana 3-4: Dashboard MVP

```
Día 11-14: Dashboard básico
  ├── data_loader.py (lee de Neon)
  ├── Página Estado Actual
  ├── Mapa simple
  └── KPIs básicos

Día 15-18: Páginas adicionales
  ├── Página Incidencias
  ├── Página Histórico
  └── Componentes reutilizables

Día 19-21: Refinamiento
  ├── Responsive design
  ├── Filtros avanzados
  └── Gráficos Plotly

Día 22: Despliegue
  ├── Testing local completo
  ├── Streamlit Cloud deploy
  └── Documentación
```

### Semana 5-6: Refinamiento y features

```
Mejoras iterativas:
- Optimización de queries
- Caching (@st.cache_data)
- Animaciones y transiciones
- Filtros adicionales
- Exportación de datos
```

---

## Checklist de Configuración Neon

### Pre-Setup

- [x] Cuenta Neon creada
- [x] Proyecto `open-tren` creado
- [x] Región seleccionada: `eu-central-1`
- [x] PostgreSQL versión: `17` (stable)
- [ ] Database `open-tren-db` creada
- [ ] Connection string copiada

### Configuración

- [ ] Autoscaling activado (Min: 0.25 CU, Max: 1 CU)
- [ ] Compute size: Default (o ajustado según uso)
- [ ] Connection pooling: Default (PgBouncer built-in)

### Secrets en GitHub

```bash
gh secret set DATABASE_URL
# Pega: postgresql://user:password@ep-xyz.aws.neon.tech/neondb?sslmode=require

gh secret set DATABASE_HOST
# Pega: ep-xyz.aws.neon.tech
```

- [ ] `DATABASE_URL` configurado
- [ ] `DATABASE_HOST` configurado
- [ ] Test de conexión desde local:
  ```bash
  psql $DATABASE_URL -c "SELECT version();"
  ```

### Schema en Neon

- [ ] Schema SQL ejecutado (`schema.sql`)
- [ ] Tablas creadas: `circulaciones`, `incidencias`, `stats_diarias`, `estaciones`
- [ ] Índices creados
- [ ] Test de inserts

### GitHub Actions

- [ ] Workflow `captura_tiempo_real.yml` creado
- [ ] Schedule: `*/5 * * * *` (cada 5 min)
- [ ] Workflow `captura_avisos.yml` creado
- [ ] Schedule: `*/15 * * * *` (cada 15 min)
- [ ] Secret `DATABASE_URL` referenciado
- [ ] Test manual de workflow

---

## Próximos Pasos

### Inmediato (hoy)

1. **Validar schema SQL**
   - ¿Tipos de datos correctos?
   - ¿Índices adecuados?
   - ¿Tablas suficientes?

2. **Crear estructura de proyecto**
   - `src/` con módulos
   - `dashboard/` con páginas
   - `scripts/` para GH Actions
   - `tests/` para testing

3. **Configurar dependencias**
   - `pyproject.toml` completo
   - `requirements.txt` actualizado

### Esta semana

1. **Setup Neon completo**
   - Ejecutar `schema.sql` en la DB
   - Verificar tablas e índices
   - Test de conexión desde código

2. **Empezar pipeline** (tu trabajo)
   - Implementar `tiempo_real.py` fetcher
   - Implementar `calcular_retrasos.py` procesador
   - Implementar `postgres_store.py` storage
   - Crear workflow GH Actions

3. **Empezar dashboard** (mi trabajo)
   - Crear `data_loader.py` básico
   - Crear página `1_🚄_Estado_Actual.py`
   - Test local con datos vacíos o mock

### Próximas semanas

1. **Completar pipeline**
   - Tests completos
   - Documentación en `docs/fase-1-ingestion.md`
   - Pipeline capturando datos

2. **Completar dashboard MVP**
   - Tres páginas funcionales
   - Responsive design
   - Despliegue en Streamlit Cloud
   - Documentación en `docs/fase-2-dashboard.md`

### Futuro (meses 3-6)

1. **Migración a VPS**
   - Hetzner o DigitalOcean
   - TimescaleDB (cuando migremos)
   - Migración de datos de Neon a VPS

2. **Mejoras de dashboard**
   - Dash (de Streamlit a Dash)
   - Más visualizaciones
   - API REST pública
   - Auth de usuarios (si necesario)

---

## Notas Importantes

### Sobre Neon Auth

❌ **NO activar "Neon Auth"** para Open Tren

- El dashboard es público, no tiene usuarios
- No necesitas passwordless auth
- Solo necesitas conexión PostgreSQL estándar (usuario:password)

### Sobre PostgreSQL v17 vs v18

- **Usar v17 (stable):** v18 está en preview con bugs no descubiertos
- Features de v18 NO necesarias para Open Tren (Async I/O, UUIDv7, etc.)
- Migración a v18 cuando sea estable (no es urgente)

### Sobre Git LFS

- **NO usar Git LFS:** Almacenar datos en Neon, no en el repo
- `.gitignore`: Ignorar `data/` (GTFS crudos)
- Solo código y documentación en el repo

### Sobre Compactación

Con PostgreSQL normal, necesitarás:

- Script de agregación diaria (stats_diarias)
- Script de compactación mensual (borrar datos >90 días, guardar solo stats)
- Ejecución automática via GitHub Actions (cron nocturno)

### Sobre Connection Pooling

- **Usar pooling nativo de Neon:** `?pgbouncer=true` en connection string
- Configurar tamaño de pool: `min_size=2`, `max_size=10`
- Evitar abrir/cerrar conexiones en cada query

---

## Referencias

- [Fase 0: Exploración](docs/fase-0-exploracion.md)
- [Fase 1: Implementación](docs/fase-1-ingestion.md) ← POR CREAR
- [Fase 2: Dashboard](docs/fase-2-dashboard.md) ← POR CREAR
- [Plan Original](docs/open-tren-implementation-proposal.md)
- [Neon Docs](https://neon.com/docs/introduction)
- [PostgreSQL 17 Release](https://www.postgresql.org/about/news/postgresql-17-released-3199/)
- [GTFS Specification](https://gtfs.org/schedule/reference/)
- [GTFS Realtime](https://gtfs.org/realtime/)
- [Streamlit Docs](https://docs.streamlit.io/)
- [Plotly Python](https://plotly.com/python/)
- [Folium Docs](https://python-visualization.github.io/folium/)

---

**Última actualización:** 15 de febrero de 2026
**Estado:** Plan aprobado, ready to implement
