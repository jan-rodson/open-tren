# Plan de Acción: Dashboard de Puntualidad Ferroviaria en España

## Visión del Proyecto

**Objetivo**: Crear la primera herramienta pública que capture, archive y visualice datos de retrasos e incidencias de trenes de media y larga distancia en España, llenando el vacío que existe respecto a otros países europeos.

**Usuario objetivo**: Viajeros frecuentes, periodistas, investigadores y ciudadanos interesados en la calidad del servicio ferroviario.

**Foco principal (MVP)**: Retrasos + Incidencias de Renfe AV/LD/MD

**Foco secundario (futuro)**: Comparativas multi-operador, tendencias históricas, predicciones

---

## Dimensionamiento: Volumen de Datos Esperado

### Trenes a procesar

| Tipo de servicio | Trenes/día aproximados |
|------------------|------------------------|
| AVE | ~180 |
| AVLO | ~40 |
| ALVIA | ~120 |
| EUROMED | ~20 |
| MD (Media Distancia) | ~400 |
| **Total AV/LD/MD** | **~750-800 trenes/día** |

**Nota**: En cada snapshot (cada 5 min) hay ~150-250 trenes "en circulación" simultáneamente.

### Cálculo de volumen

```
Por snapshot (cada 5 min):
├── Trenes en circulación: ~200
├── Campos por tren: ~15
├── Bytes por registro: ~500 bytes
└── Total por snapshot: ~100 KB (JSON crudo)

Por día:
├── Snapshots: 288 (cada 5 min × 24h)
├── Registros totales: ~57,600 filas
├── JSON crudo: ~29 MB
└── Parquet comprimido (ZSTD): ~2-5 MB

Por mes:
├── Filas: ~1.7 millones
└── Parquet: ~60-80 MB

Por año:
├── Filas: ~21 millones
└── Parquet: ~700 MB - 1 GB
```

### Capacidad del MVP vs. límites

| Recurso | Límite gratuito | Uso al año | Margen |
|---------|-----------------|------------|--------|
| GitHub repo size | 5 GB (soft) | ~1-1.5 GB | ✅ 3x de sobra |
| Git LFS storage | 1 GB | ~1 GB | ⚠️ Justo, usar estrategia de limpieza |
| Git LFS bandwidth | 1 GB/mes | ~200 MB/mes | ✅ 5x de sobra |
| GitHub Actions | 2000 min/mes | ~720 min/mes | ✅ 2.7x de sobra |
| Streamlit Cloud RAM | 1 GB | ~200-400 MB (3 meses cargados) | ✅ 2-3x de sobra |

**Conclusión: El MVP aguanta 12-24 meses** antes de necesitar migrar a VPS.

---

## Arquitectura General

```
┌─────────────────────────────────────────────────────────────────┐
│                        INGESTA (Backend)                        │
├─────────────────────────────────────────────────────────────────┤
│  GitHub Actions (cron cada 5 min)                               │
│       ↓                                                         │
│  Script Python (httpx)                                          │
│       ├── Feed tiempo real Renfe (JSON) → retrasos actuales     │
│       ├── Feed avisos Renfe (JSON) → incidencias                │
│       └── GTFS estático (semanal) → horarios programados        │
│       ↓                                                         │
│  DuckDB + Parquet (almacenados en repo o R2/S3)                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      FRONTEND (Dashboard)                       │
├─────────────────────────────────────────────────────────────────┤
│  Streamlit (MVP) → Dash (Producción)                            │
│       ├── Vista principal: Estado actual de la red              │
│       ├── Vista incidencias: Alertas activas                    │
│       ├── Vista histórico: Tendencias y estadísticas            │
│       └── Responsive: Mobile-first con Tailwind/CSS             │
│                                                                 │
│  Hosting: Streamlit Cloud (gratis) → VPS Hetzner (€5/mes)       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Fase 0: Preparación y Validación (1-2 días)

### Objetivos
- Confirmar que los endpoints de Renfe funcionan como se espera
- Entender la estructura real de los datos
- Validar la viabilidad técnica antes de escribir código de producción

### Tareas

#### 0.1 Exploración de endpoints
```bash
# Crear entorno de trabajo
mkdir open-tren && cd open-tren
python -m venv .venv && source .venv/bin/activate
pip install httpx pandas jupyter
```

**Endpoints a probar:**
- `https://data.renfe.com/api/3/action/package_list` → lista de datasets
- `https://data.renfe.com/api/3/action/package_show?id=horarios-viaje-alta-velocidad-larga-media-distancia` → metadatos del feed tiempo real
- URL del recurso JSON del feed tiempo real (extraer de metadatos)
- `https://data.renfe.com/api/3/action/package_show?id=avisos` → feed de incidencias

#### 0.2 Documentar estructura de datos
Crear un notebook `exploration.ipynb` que:
1. Descargue un snapshot del feed tiempo real
2. Analice los campos disponibles (`CODTREN`, `RETRASO`, `LINEA`, etc.)
3. Descargue el feed de avisos y documente su estructura
4. Descargue el GTFS y explore `stop_times.txt`, `trips.txt`, `stops.txt`

#### 0.3 Definir el modelo de datos objetivo
```python
# Esquema conceptual para circulaciones
{
    "timestamp_captura": "2026-02-08T10:30:00Z",
    "codigo_tren": "AVE 3142",
    "tipo_servicio": "AVE",  # AVE, AVLO, ALVIA, MD, etc.
    "linea": "Madrid-Barcelona",
    "origen": "Madrid Puerta de Atocha",
    "destino": "Barcelona Sants",
    "hora_salida_programada": "08:00",
    "hora_salida_real": "08:05",
    "hora_llegada_programada": "10:30",
    "hora_llegada_estimada": "10:38",
    "retraso_minutos": 8,
    "estado": "EN_RUTA",  # PROGRAMADO, EN_RUTA, LLEGADO, CANCELADO
    "parada_actual": "Zaragoza Delicias"
}

# Esquema conceptual para incidencias
{
    "timestamp_captura": "2026-02-08T10:30:00Z",
    "id_aviso": "AV-2026-1234",
    "tipo": "OBRAS",  # OBRAS, INCIDENCIA, HUELGA, METEOROLOGIA
    "titulo": "Obras en túnel de Guadarrama",
    "descripcion": "...",
    "lineas_afectadas": ["Madrid-Segovia", "Madrid-Valladolid"],
    "fecha_inicio": "2026-02-01",
    "fecha_fin": "2026-02-15",
    "activo": true
}
```

### Entregable Fase 0
- Notebook con exploración completa de los 3 feeds
- Documento `DATOS.md` con estructura real de cada endpoint
- Decisión go/no-go basada en calidad de datos disponibles

---

## Fase 1: Pipeline de Ingesta (3-5 días)

### Objetivos
- Capturar datos de forma automatizada y fiable
- Almacenar histórico desde el día 1
- Código limpio y mantenible

### Estructura del proyecto

```
open-tren/
├── .github/
│   └── workflows/
│       ├── captura_tiempo_real.yml    # Cada 5 min
│       ├── captura_avisos.yml         # Cada 15 min
│       └── actualiza_gtfs.yml         # Semanal
├── src/
│   ├── __init__.py
│   ├── config.py                      # URLs, constantes
│   ├── fetchers/
│   │   ├── __init__.py
│   │   ├── tiempo_real.py             # Descarga feed JSON
│   │   ├── avisos.py                  # Descarga incidencias
│   │   └── gtfs.py                    # Descarga y parsea GTFS
│   ├── processors/
│   │   ├── __init__.py
│   │   ├── calcular_retrasos.py       # Compara real vs programado
│   │   └── normalizar.py              # Limpieza y transformación
│   ├── storage/
│   │   ├── __init__.py
│   │   └── parquet_store.py           # Lectura/escritura Parquet
│   └── models/
│       ├── __init__.py
│       └── schemas.py                 # Pydantic models
├── data/
│   ├── raw/                           # Snapshots crudos (JSON)
│   │   ├── tiempo_real/
│   │   │   └── 2026-02-08/
│   │   │       ├── 10-30-00.json
│   │   │       └── 10-35-00.json
│   │   └── avisos/
│   ├── processed/                     # Datos limpios (Parquet)
│   │   ├── circulaciones/
│   │   │   └── 2026-02.parquet
│   │   └── incidencias/
│   │       └── 2026-02.parquet
│   └── gtfs/                          # GTFS actual
│       └── renfe_av_ld_md/
├── scripts/
│   ├── captura_tiempo_real.py         # Entry point para GH Actions
│   ├── captura_avisos.py
│   └── actualiza_gtfs.py
├── tests/
├── pyproject.toml
└── README.md
```

### Tareas

#### 1.1 Configuración del proyecto
```toml
# pyproject.toml
[project]
name = "open-tren"
version = "0.1.0"
dependencies = [
    "httpx>=0.27",
    "pydantic>=2.0",
    "duckdb>=1.0",
    "pyarrow>=15.0",
    "polars>=0.20",        # Alternativa rápida a pandas
    "gtfs-kit>=5.0",       # Parser GTFS
]

[project.optional-dependencies]
dev = ["pytest", "ruff", "ipykernel"]
dashboard = ["streamlit>=1.30", "plotly>=5.18", "folium>=0.15"]
```

#### 1.2 Implementar fetchers
```python
# src/fetchers/tiempo_real.py
import httpx
from datetime import datetime
from pathlib import Path
import json

async def fetch_tiempo_real() -> dict:
    """Descarga el feed de tiempo real de Renfe."""
    # URL real a extraer de la exploración en Fase 0
    url = "https://tiempo-real.renfe.com/..."  
    
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()

def save_snapshot(data: dict, base_path: Path) -> Path:
    """Guarda snapshot con timestamp en estructura de directorios."""
    now = datetime.utcnow()
    dir_path = base_path / "raw" / "tiempo_real" / now.strftime("%Y-%m-%d")
    dir_path.mkdir(parents=True, exist_ok=True)
    
    file_path = dir_path / f"{now.strftime('%H-%M-%S')}.json"
    file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return file_path
```

#### 1.3 Implementar procesador de retrasos
```python
# src/processors/calcular_retrasos.py
import polars as pl
from datetime import datetime

def procesar_snapshot(raw_data: dict, gtfs_stop_times: pl.DataFrame) -> pl.DataFrame:
    """
    Transforma snapshot crudo en registros de circulación con retraso calculado.
    
    El feed de Renfe puede incluir campo RETRASO directamente, o puede
    requerir calcularlo comparando hora real vs GTFS.
    """
    # Convertir a DataFrame
    df = pl.DataFrame(raw_data["circulaciones"])  # Ajustar según estructura real
    
    # Normalizar campos
    df = df.with_columns([
        pl.col("CODTREN").alias("codigo_tren"),
        pl.col("LINEA").alias("linea"),
        pl.col("RETRASO").cast(pl.Int32).alias("retraso_minutos"),
        pl.lit(datetime.utcnow()).alias("timestamp_captura"),
    ])
    
    # Enriquecer con datos GTFS si es necesario
    # ...
    
    return df.select([
        "timestamp_captura",
        "codigo_tren",
        "linea",
        "retraso_minutos",
        # ... otros campos
    ])
```

#### 1.4 Configurar GitHub Actions
```yaml
# .github/workflows/captura_tiempo_real.yml
name: Captura Tiempo Real

on:
  schedule:
    - cron: '*/5 * * * *'  # Cada 5 minutos
  workflow_dispatch:        # Permite ejecución manual

jobs:
  captura:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'
      
      - name: Install dependencies
        run: pip install -e .
      
      - name: Ejecutar captura
        run: python scripts/captura_tiempo_real.py
      
      - name: Commit datos
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add data/
          git diff --staged --quiet || git commit -m "📊 Snapshot $(date -u +%Y-%m-%dT%H:%M:%SZ)"
          git push
```

#### 1.5 Agregación diaria (job nocturno)
```yaml
# .github/workflows/agregacion_diaria.yml
name: Agregación Diaria

on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM UTC

jobs:
  agregar:
    runs-on: ubuntu-latest
    steps:
      # ... setup ...
      - name: Agregar snapshots del día anterior
        run: python scripts/agregar_dia.py --fecha yesterday
      
      - name: Generar estadísticas
        run: python scripts/generar_stats.py
```

#### 1.6 Compactación mensual (mantener repo pequeño)
```yaml
# .github/workflows/compactacion_mensual.yml
name: Compactación Mensual

on:
  schedule:
    - cron: '0 3 1 * *'  # Día 1 de cada mes, 3 AM UTC
  workflow_dispatch:      # Permite ejecución manual

jobs:
  compactar:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          lfs: true       # Importante: descargar archivos LFS
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'
      
      - name: Install dependencies
        run: pip install -e .
      
      - name: Compactar meses antiguos (>3 meses)
        run: python scripts/compactar_historico.py
      
      - name: Commit cambios
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add data/
          git diff --staged --quiet || git commit -m "📦 Compactación mensual $(date +%Y-%m)"
          git push
```

### Cómo Streamlit Cloud lee los datos del repo

Streamlit Cloud **clona tu repositorio** cada vez que despliega. Los archivos Parquet están disponibles como archivos locales dentro de la app.

```python
# dashboard/utils/data_loader.py
import polars as pl
from pathlib import Path
from datetime import datetime, timedelta
import streamlit as st

@st.cache_data(ttl=300)  # Cache 5 minutos, luego relee
def cargar_circulaciones_recientes(horas: int = 6) -> pl.DataFrame:
    """Carga datos de las últimas N horas."""
    
    # Los parquet están en el repo clonado
    data_dir = Path("data/processed/circulaciones")
    mes_actual = datetime.now().strftime("%Y-%m")
    
    df = pl.read_parquet(data_dir / f"{mes_actual}.parquet")
    
    corte = datetime.now() - timedelta(hours=horas)
    return df.filter(pl.col("timestamp") > corte)

@st.cache_data(ttl=3600)  # Cache 1 hora para históricos
def cargar_historico(meses: int = 3) -> pl.DataFrame:
    """Carga los últimos N meses completos."""
    
    data_dir = Path("data/processed/circulaciones")
    archivos = sorted(data_dir.glob("*.parquet"))[-meses:]
    
    return pl.concat([pl.read_parquet(f) for f in archivos])

@st.cache_data(ttl=3600)
def cargar_estadisticas_historicas() -> pl.DataFrame:
    """Carga estadísticas agregadas de meses compactados."""
    
    archive_dir = Path("data/processed/circulaciones/archive")
    if not archive_dir.exists():
        return pl.DataFrame()
    
    archivos = list(archive_dir.glob("*-stats.parquet"))
    if not archivos:
        return pl.DataFrame()
    
    return pl.concat([pl.read_parquet(f) for f in archivos])
```

**Flujo de actualización:**
1. GitHub Actions hace commit de nuevos datos cada 5 min
2. Streamlit Cloud detecta el push (webhook)
3. En el siguiente request de un usuario (tras expirar caché), Streamlit hace `git pull`
4. La app lee los Parquet actualizados

**El caché `@st.cache_data`** es clave: evita releer los archivos en cada visita. Con `ttl=300` (5 minutos), los datos se refrescan con frecuencia suficiente sin sobrecargar.

**Opción A: Datos en el repo (MVP)**
- Pros: Simple, versionado automático, gratis
- Contras: Límite ~1GB en GitHub, commits frecuentes ensucian historial
- Mitigación: Usar Git LFS para Parquet, `.gitignore` para JSON crudos antiguos

**Opción B: Cloudflare R2 (Producción)**
- Pros: S3-compatible, egress gratis, 10GB gratis/mes
- Contras: Requiere configuración adicional
- Cuándo migrar: Cuando los datos superen 500MB

### Git LFS: Qué es y cómo usarlo

Git LFS (Large File Storage) evita que el repo se hinche con archivos grandes. Git normal guarda **todas las versiones** de cada archivo. Con LFS, solo guarda un "puntero" y el archivo real va a un storage separado.

**Configuración inicial:**
```bash
# Instalar Git LFS (una vez)
git lfs install

# Trackear archivos Parquet
git lfs track "*.parquet"

# Commitear el archivo de configuración
git add .gitattributes
git commit -m "Configurar Git LFS para Parquet"
```

**Límites gratuitos de Git LFS en GitHub:**
- Storage: 1 GB
- Bandwidth: 1 GB/mes

Con la estrategia de compactación (ver más abajo), estos límites son suficientes para 2+ años.

### Estrategia de compactación para alargar el MVP

Para mantener el repo pequeño y el MVP funcionando años:

```
data/
├── processed/
│   ├── circulaciones/
│   │   ├── 2026-02.parquet          ← Mes actual: detalle completo (~60-80 MB)
│   │   ├── 2026-01.parquet          ← Mes anterior: detalle completo
│   │   ├── 2025-12.parquet          ← Hace 2 meses: detalle completo
│   │   └── archive/
│   │       ├── 2025-Q3-stats.parquet    ← Trimestres antiguos: solo agregados (~100 KB)
│   │       └── ...
```

**Job de compactación (ejecutar mensualmente):**
```python
# scripts/compactar_historico.py
import polars as pl
from pathlib import Path
from datetime import datetime, timedelta

def compactar_mes_antiguo(mes: str):
    """
    Reduce un mes de ~1.7M filas a ~30 filas (stats diarias).
    Ejecutar para meses con más de 3 meses de antigüedad.
    """
    ruta = Path(f"data/processed/circulaciones/{mes}.parquet")
    if not ruta.exists():
        return
    
    df = pl.read_parquet(ruta)
    
    # Agregar a nivel diario
    stats = df.group_by([
        pl.col("timestamp").dt.date().alias("fecha"),
        pl.col("tipo_servicio"),
        pl.col("linea"),
    ]).agg([
        pl.count().alias("total_circulaciones"),
        pl.col("retraso_minutos").mean().alias("retraso_medio"),
        pl.col("retraso_minutos").median().alias("retraso_mediana"),
        pl.col("retraso_minutos").max().alias("retraso_maximo"),
        (pl.col("retraso_minutos") <= 5).sum().alias("puntuales"),
        (pl.col("retraso_minutos") > 5).sum().alias("con_retraso"),
        (pl.col("retraso_minutos") > 15).sum().alias("retraso_grave"),
        (pl.col("retraso_minutos") > 30).sum().alias("retraso_muy_grave"),
    ])
    
    # Guardar agregado (~100 KB vs ~60 MB original)
    Path("data/processed/circulaciones/archive").mkdir(exist_ok=True)
    stats.write_parquet(f"data/processed/circulaciones/archive/{mes}-stats.parquet")
    
    # Borrar el archivo detallado
    ruta.unlink()
    print(f"Compactado {mes}: {len(df):,} filas → {len(stats):,} filas")

# Compactar meses con más de 3 meses de antigüedad
if __name__ == "__main__":
    hace_3_meses = (datetime.now() - timedelta(days=90)).strftime("%Y-%m")
    # Listar todos los parquet y compactar los antiguos
    for f in Path("data/processed/circulaciones").glob("*.parquet"):
        mes = f.stem  # "2025-10"
        if mes < hace_3_meses:
            compactar_mes_antiguo(mes)
```

**Resultado con compactación:**
- Últimos 3 meses: detalle completo (~200 MB)
- Histórico: solo agregados (~1 MB/año)
- **Total después de 5 años: ~250 MB** (muy dentro de los límites)

### Entregables Fase 1
- Pipeline funcionando con capturas cada 5 min
- Primeros días de datos históricos acumulándose
- Tests básicos para fetchers y procesadores
- README con instrucciones de desarrollo local

---

## Fase 2: Dashboard MVP (5-7 días)

### Objetivos
- Dashboard funcional accesible públicamente
- Diseño responsive (mobile-first)
- Tres vistas principales: Estado Actual, Incidencias, Histórico básico

### Stack elegido: Streamlit

**Justificación:**
- Desarrollo rapidísimo (1 archivo Python = app completa)
- Streamlit Cloud gratis con dominio `*.streamlit.app`
- Componentes responsive por defecto
- `st.columns()` para layouts adaptativos
- `streamlit-folium` para mapas

### Estructura del dashboard

```
dashboard/
├── app.py                    # Entry point
├── pages/
│   ├── 1_🚄_Estado_Actual.py
│   ├── 2_⚠️_Incidencias.py
│   └── 3_📊_Histórico.py
├── components/
│   ├── __init__.py
│   ├── mapa.py               # Mapa de la red
│   ├── tabla_trenes.py       # Tabla con filtros
│   ├── kpis.py               # Tarjetas de métricas
│   └── graficos.py           # Gráficos Plotly
├── utils/
│   ├── __init__.py
│   ├── data_loader.py        # Carga desde Parquet
│   └── styles.py             # CSS custom
└── .streamlit/
    └── config.toml           # Tema y configuración
```

### Tareas

#### 2.1 Vista "Estado Actual" (página principal)

```python
# dashboard/pages/1_🚄_Estado_Actual.py
import streamlit as st
import polars as pl
from components.kpis import render_kpis
from components.mapa import render_mapa_red
from components.tabla_trenes import render_tabla

st.set_page_config(
    page_title="Trenes España - Estado Actual",
    page_icon="🚄",
    layout="wide",
    initial_sidebar_state="collapsed"  # Mejor en móvil
)

# CSS para responsive
st.markdown("""
<style>
    /* Mobile-first */
    .stMetric { padding: 0.5rem; }
    
    @media (max-width: 768px) {
        .block-container { padding: 1rem; }
        [data-testid="column"] { width: 100% !important; }
    }
</style>
""", unsafe_allow_html=True)

# Header
st.title("🚄 Estado de la Red Ferroviaria")
st.caption(f"Última actualización: {get_last_update()}")

# KPIs principales (responsive: 4 cols en desktop, 2 en móvil)
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Trenes en circulación", "342", delta="12")
with col2:
    st.metric("Puntualidad", "87%", delta="-3%")
with col3:
    st.metric("Retraso medio", "8 min", delta="2 min")
with col4:
    st.metric("Incidencias activas", "3", delta="1")

# Filtros (en sidebar en desktop, colapsable en móvil)
with st.sidebar:
    tipo_servicio = st.multiselect(
        "Tipo de servicio",
        ["AVE", "AVLO", "ALVIA", "EUROMED", "MD"],
        default=["AVE", "AVLO", "ALVIA"]
    )
    linea = st.selectbox("Línea", ["Todas"] + get_lineas())
    solo_retrasos = st.checkbox("Solo trenes con retraso", value=False)

# Mapa de la red (ocupa ancho completo)
st.subheader("Mapa de circulaciones")
render_mapa_red(filtros={
    "tipo_servicio": tipo_servicio,
    "linea": linea,
    "solo_retrasos": solo_retrasos
})

# Tabla de trenes
st.subheader("Detalle de trenes")
render_tabla(filtros=...)
```

#### 2.2 Vista "Incidencias"

```python
# dashboard/pages/2_⚠️_Incidencias.py
import streamlit as st

st.title("⚠️ Incidencias Activas")

# Tarjetas de incidencias (estilo alertas)
incidencias = load_incidencias_activas()

for inc in incidencias:
    severity_color = {
        "ALTA": "🔴",
        "MEDIA": "🟡",
        "BAJA": "🟢"
    }.get(inc.severidad, "⚪")
    
    with st.expander(f"{severity_color} {inc.titulo}", expanded=inc.severidad == "ALTA"):
        st.write(f"**Tipo:** {inc.tipo}")
        st.write(f"**Líneas afectadas:** {', '.join(inc.lineas)}")
        st.write(f"**Periodo:** {inc.fecha_inicio} - {inc.fecha_fin or 'Sin fecha fin'}")
        st.write(inc.descripcion)

# Timeline de incidencias recientes
st.subheader("Historial reciente")
render_timeline_incidencias()
```

#### 2.3 Vista "Histórico" (básico para MVP)

```python
# dashboard/pages/3_📊_Histórico.py
import streamlit as st
import plotly.express as px

st.title("📊 Estadísticas Históricas")

# Selector de rango temporal
col1, col2 = st.columns(2)
with col1:
    fecha_inicio = st.date_input("Desde", value=default_inicio)
with col2:
    fecha_fin = st.date_input("Hasta", value=today)

# Gráfico de evolución de puntualidad
df_puntualidad = load_stats_puntualidad(fecha_inicio, fecha_fin)

fig = px.line(
    df_puntualidad,
    x="fecha",
    y="puntualidad_pct",
    color="tipo_servicio",
    title="Evolución de la puntualidad"
)
fig.update_layout(yaxis_range=[70, 100])
st.plotly_chart(fig, use_container_width=True)

# Distribución de retrasos
fig2 = px.histogram(
    df_retrasos,
    x="retraso_minutos",
    nbins=30,
    title="Distribución de retrasos"
)
st.plotly_chart(fig2, use_container_width=True)

# Top rutas con más retrasos
st.subheader("Rutas con peor puntualidad")
st.dataframe(
    df_rutas_peores.head(10),
    use_container_width=True,
    hide_index=True
)
```

#### 2.4 Componente de mapa

```python
# dashboard/components/mapa.py
import folium
from streamlit_folium import st_folium
import polars as pl

def render_mapa_red(circulaciones: pl.DataFrame, estaciones: pl.DataFrame):
    """Renderiza mapa con estado de trenes."""
    
    # Centro de España
    m = folium.Map(
        location=[40.4168, -3.7038],
        zoom_start=6,
        tiles="cartodbpositron"  # Tiles limpios
    )
    
    # Añadir marcadores de estaciones principales
    for est in estaciones.iter_rows(named=True):
        folium.CircleMarker(
            location=[est["lat"], est["lon"]],
            radius=5,
            color="gray",
            fill=True,
            popup=est["nombre"]
        ).add_to(m)
    
    # Añadir trenes en circulación
    for tren in circulaciones.iter_rows(named=True):
        color = get_color_retraso(tren["retraso_minutos"])
        
        folium.Marker(
            location=[tren["lat"], tren["lon"]],
            icon=folium.Icon(color=color, icon="train", prefix="fa"),
            popup=f"""
                <b>{tren['codigo_tren']}</b><br>
                {tren['origen']} → {tren['destino']}<br>
                Retraso: {tren['retraso_minutos']} min
            """
        ).add_to(m)
    
    # Renderizar (responsive)
    st_folium(m, use_container_width=True, height=500)

def get_color_retraso(minutos: int) -> str:
    if minutos <= 5:
        return "green"
    elif minutos <= 15:
        return "orange"
    else:
        return "red"
```

#### 2.5 Configuración Streamlit Cloud

```toml
# .streamlit/config.toml
[theme]
primaryColor = "#1E88E5"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F5F5F5"
textColor = "#262730"
font = "sans serif"

[server]
headless = true
port = 8501

[browser]
gatherUsageStats = false
```

```
# requirements.txt (para Streamlit Cloud)
streamlit>=1.30
plotly>=5.18
folium>=0.15
streamlit-folium>=0.15
polars>=0.20
duckdb>=1.0
httpx>=0.27
```

### Entregables Fase 2
- Dashboard desplegado en `open-tren.streamlit.app` (o similar)
- 3 páginas funcionales: Estado Actual, Incidencias, Histórico
- Diseño responsive probado en móvil
- Datos actualizándose automáticamente desde el pipeline

---

## Fase 3: Refinamiento y Features Adicionales (2-4 semanas)

### 3.1 Mejoras de UX
- [ ] Dark mode toggle
- [ ] Selector de idioma (ES/EN)
- [ ] PWA para instalación en móvil
- [ ] Notificaciones push para incidencias (vía web push o Telegram bot)

### 3.2 Mejoras de datos
- [ ] Añadir feed de Cercanías (GTFS-RT Protobuf)
- [ ] Scraper para Ouigo (usando librería existente)
- [ ] Integrar informes CNMC trimestrales
- [ ] Geolocalización de trenes en ruta (interpolar posición)

### 3.3 Análisis avanzado
- [ ] Predicción de retrasos por hora/día de la semana
- [ ] Detección de patrones (ej: "los viernes hay más retrasos")
- [ ] Comparativa con años anteriores
- [ ] Correlación retrasos vs. meteorología

### 3.4 API pública
- [ ] Endpoint REST para consultar datos históricos
- [ ] Documentación OpenAPI
- [ ] Rate limiting básico
- [ ] Licencia CC BY 4.0 para los datos

### 3.5 Migración a VPS (cuando el MVP se quede corto)

**Cuándo migrar** (cualquiera de estos triggers):
- Repo supera 1 GB y la compactación no es suficiente
- Más de 20-30 usuarios simultáneos (Streamlit Cloud se ralentiza)
- Necesitas queries complejas sobre todo el histórico
- Quieres tu propio dominio con control total
- Quieres exponer una API pública

**Qué cambia en la arquitectura:**

```
MVP (GitHub + Streamlit Cloud)              VPS (Hetzner €4-5/mes)
───────────────────────────────────         ───────────────────────────────────
GitHub Actions (cron cada 5 min)      ──▶   Systemd timer o Celery Beat
                                            (control total, sin límites)

Archivos Parquet en repo              ──▶   PostgreSQL + TimescaleDB
                                            - Hypertables particionadas por tiempo
                                            - Compresión automática
                                            - Queries SQL complejas instantáneas

Streamlit Cloud                       ──▶   Dash en Docker + Nginx + Certbot
                                            - Mejor rendimiento multiusuario
                                            - HTTPS con tu dominio

streamlit.app subdomain               ──▶   Tu dominio (open-tren.es ~€10/año)
```

**Cambios mínimos en el código:**

```python
# MVP: lee de archivos Parquet locales
df = pl.read_parquet("data/processed/circulaciones/2026-02.parquet")

# VPS: lee de PostgreSQL (cambias 1 línea)
df = pl.read_database(
    "SELECT * FROM circulaciones WHERE timestamp > now() - interval '6 hours'",
    connection_string
)
```

**Docker Compose para VPS:**
```yaml
# docker-compose.yml
version: '3.8'
services:
  db:
    image: timescale/timescaledb:latest-pg15
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    
  dashboard:
    build: ./dashboard
    depends_on:
      - db
    environment:
      DATABASE_URL: postgresql://postgres:${DB_PASSWORD}@db/trenes
    
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./certbot:/etc/letsencrypt

volumes:
  pgdata:
```

**Coste estimado en VPS:**
- Hetzner CX22: €4.5/mes (2 vCPU, 4GB RAM, 40GB SSD)
- Dominio: ~€10/año
- **Total: ~€60/año**

---

## Cronograma Estimado

### Desarrollo inicial

```
Semana 1:  ████░░░░░░  Fase 0 (2d) + Fase 1 inicio (3d)
Semana 2:  ██████░░░░  Fase 1 completa + Fase 2 inicio
Semana 3:  ████████░░  Fase 2 completa (MVP público)
Semana 4+: ██████████  Fase 3 (mejoras iterativas)
```

**Hitos clave:**
- **Día 2**: Exploración completa, decisión go/no-go
- **Día 7**: Pipeline capturando datos automáticamente
- **Día 14**: Dashboard MVP público con datos reales
- **Día 21**: Primera versión refinada con feedback de usuarios

### Ciclo de vida del MVP

```
Mes 1-3:     Acumulando datos, refinando dashboard
Mes 4-6:     Primeras estadísticas históricas interesantes
Mes 7-12:    Dataset significativo, posibles análisis de tendencias
Mes 12-24:   Evaluar migración a VPS si hay tracción

Triggers para migrar a VPS:
├── Repo > 1 GB (con compactación, improbable antes de 18-24 meses)
├── > 30 usuarios simultáneos frecuentes
├── Necesidad de API pública
└── Querer dominio propio y control total
```

**Estimación conservadora: El MVP es viable 12-24 meses** sin tocar VPS ni pagar nada.

---

## Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Endpoint de Renfe cambia sin aviso | Media | Alto | Monitorizar errores, alertas en Telegram |
| Rate limiting de Renfe | Baja | Medio | Empezar con 5 min, reducir si hay problemas |
| GitHub Actions límite de minutos | Baja | Medio | 2000 min/mes gratis, suficiente para MVP |
| Datos de baja calidad/incompletos | Media | Medio | Validación en pipeline, logging detallado |
| GTFS no actualizado por Renfe | Baja | Bajo | Detectar cambios, alertar para revisión manual |

---

## Recursos y Referencias

**Documentación técnica:**
- [API CKAN v3](https://docs.ckan.org/en/latest/api/)
- [Especificación GTFS](https://gtfs.org/schedule/reference/)
- [Streamlit docs](https://docs.streamlit.io/)
- [DuckDB Python API](https://duckdb.org/docs/api/python/overview)

**Proyectos de referencia:**
- [deutsche-bahn-data](https://github.com/piebro/deutsche-bahn-data) - Patrón de archivado
- [railway-opendata](https://github.com/MarcoBuster/railway-opendata) - Arquitectura scraper
- [renfe-cli](https://github.com/gerardcl/renfe-cli) - Parsing GTFS Renfe
- [rijdendetreinen.nl](https://www.rijdendetreinen.nl/en/open-data) - Modelo de datos abiertos

**Feeds de Renfe:**
- [Portal data.renfe.com](https://data.renfe.com/)
- [GTFS AV/LD/MD](https://data.renfe.com/dataset/horarios-de-alta-velocidad-larga-distancia-y-media-distancia)
- [Avisos](https://data.renfe.com/dataset/avisos)

---

## Próximos Pasos Inmediatos

1. **Hoy**: Crear repositorio `open-tren` en GitHub
2. **Hoy**: Ejecutar exploración de endpoints (Fase 0.1)
3. **Mañana**: Documentar estructura de datos real
4. **Día 3**: Implementar primer fetcher funcional
5. **Día 4**: Configurar GitHub Actions con captura cada 5 min
6. **Día 5**: Verificar que se acumulan datos, iniciar dashboard
