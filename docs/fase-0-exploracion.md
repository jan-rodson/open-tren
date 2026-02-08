# Fase 0: Exploración y Validación

**Fecha:** 8 de febrero de 2026

**Estado:** ✅ COMPLETADA

**Decisión:** GO / NO-GO → **GO** (Proyecto viable)

---

## 1. Objetivos

Esta fase tenía como propósito validar la viabilidad técnica del proyecto antes de escribir código de producción:

1. **Confirmar disponibilidad de endpoints** - Verificar que los feeds de Renfe son accesibles
2. **Entender estructura de datos** - Documentar el formato real de los endpoints
3. **Validar marco legal** - Revisar términos de uso y condiciones de reutilización
4. **Detectar limitaciones** - Identificar restricciones o problemas técnicos

---

## 2. Metodología

La exploración se realizó mediante:

| Herramienta | Uso |
|-------------|-----|
| `curl` + `jq`/`python3` | Peticiones directas a APIs y parsing de JSON |
| Web search | Búsqueda de contexto legal y documentación |
| CKAN API (`data.renfe.com/api/3/`) | Listado y metadatos de datasets |

---

## 3. Endpoints Verificados

### 3.1 Feed de Tiempo Real (GTFS-RT)

| Campo | Valor |
|-------|-------|
| **URL** | `https://gtfsrt.renfe.com/trip_updates_LD.json` |
| **Método** | GET |
| **Formato** | JSON (GTFS Realtime simplificado) |
| **Actualización** | Cada ~30 segundos |
| **Tamaño** | ~100-200 KB por snapshot |
| **Licencia** | CC-BY-4.0 |

**Estructura de respuesta:**
```json
{
  "header": {
    "gtfsRealtimeVersion": "2.0",
    "timestamp": "1770496280"
  },
  "entity": [
    {
      "id": "TUUPDATE_3716712026-02-06",
      "tripUpdate": {
        "trip": {
          "tripId": "3716712026-02-06",
          "scheduleRelationship": "SCHEDULED"
        },
        "delay": 240
      }
    }
  ]
}
```

**Campos disponibles:**
- `tripId`: Identificador único del viaje (formato: `[número tren]-[YYYY]-[MM]-[DD]`)
- `delay`: Retraso en **segundos** (positivo = retraso, negativo = adelanto)

**⚠️ LIMITACIÓN IMPORTANTE:**

El feed GTFS-RT de Renfe **solo contiene trenes con retrasos o incidencias activas**. Si un tren va según horario programado, no aparece en el feed.

*Ejemplo real:* Un snapshot tomado el 2026-02-08 contenía 634 entidades, pero ninguna correspondía a esa fecha - todas eran de 2026-02-06 y 2026-02-07 (trenes con incidencias aún activas de días anteriores).

Esto significa que para obtener el **estado completo de la red** es necesario:

1. Obtener los trenes programados del GTFS estático
2. Cruzar con el GTFS-RT para obtener retrasos
3. Los trenes que no aparecen en GTFS-RT se asumen puntuales (delay=0)

---

### 3.2 GTFS Estático (Horarios Programados)

| Campo | Valor |
|-------|-------|
| **URL** | `https://ssl.renfe.com/gtransit/Fichero_AV_LD/google_transit.zip` |
| **Formato** | ZIP conteniendo archivos GTFS (.txt) |
| **Actualización** | Diaria (según metadatos) |
| **Tamaño** | ~800 KB comprimido, ~42 MB descomprimido |
| **Licencia** | CC-BY-4.0 |

**Archivos incluidos:**
| Archivo | Tamaño | Descripción |
|---------|--------|-------------|
| `agency.txt` | 702 bytes | Información de la operadora |
| `routes.txt` | 220 KB | Rutas y líneas |
| `stops.txt` | 271 KB | Estaciones y paradas |
| `stop_times.txt` | 17 MB | Horarios de paso por estación |
| `trips.txt` | 2.1 MB | Viajes programados |
| `calendar.txt` | 2.1 MB | Calendario de servicios |
| `calendar_dates.txt` | 20 MB | Excepciones y fechas específicas |

**Estructura de `trips.txt`:**
```csv
route_id,service_id,trip_id,trip_headsign,trip_short_name,direction_id,block_id,shape_id,wheelchair_accessible
1700037606GL023,2026-02-082026-02-13001901,0019012026-02-08,,00190,,,1
```

**Campos clave:**
- `trip_id`: Identificador que cruza con GTFS-RT (ej: `0019012026-02-08`)
- `trip_short_name`: Código de tren visible para usuarios (ej: `00190`)
- `route_id`: Identificador de ruta para cruzar con `routes.txt`

**Estructura de `routes.txt`:**
```csv
route_id,agency_id,route_short_name,route_long_name,route_desc,route_type,route_url,route_color,route_text_color
1700037606GL023,1071,ALVIA,,,2,,F2F5F5,
```

**Tipos de servicio encontrados:**
- AVE
- ALVIA
- AVLO
- Intercity
- Trenhotel
- Euromed
- Media Distancia (MD)

---

### 3.3 Feed de Avisos e Incidencias

| Campo | Valor |
|-------|-------|
| **URL** | `https://www.renfe.com/content/renfe/es/es/grupo-renfe/comunicacion/renfe-al-dia/avisos/jcr:content/root/responsivegrid/rfincidentreports_co.noticeresults.json` |
| **Formato** | JSON |
| **Actualización** | Eventual (cuando hay avisos nuevos) |

**Estructura de respuesta:**
```json
[
  {
    "paragraph": "Renfe modifica ligeramente y de forma temporal los horarios...",
    "chipText": "Desde el 16 de febrero",
    "aspect": "primary",
    "link": "/es/es/grupo-renfe/comunicacion/renfe-al-dia/avisos/...",
    "tags": [
      {"text": "Aragón"}
    ],
    "target": "_self"
  }
]
```

**Tipos de incidencias encontradas:**
- Obras de infraestructura (Adif)
- Modificaciones horarias temporales
- Servicios alternativos por carretera (autobuses)
- Alertas climatológicas
- Planes de transporte alternativos

---

## 4. Validación de Cruce de Datos

### 4.1 Formato del trip_id

El formato del `trip_id` es consistente entre GTFS estático y GTFS-RT:

```
[numero tren] + [YYYY] + [MM] + [DD]
```

Ejemplos:
- `0019012026-02-08` → Tren 00190 del 8 de febrero de 2026
- `3716712026-02-06` → Tren 37167 del 6 de febrero de 2026

### 4.2 Estrategia de cruce

```python
# Pseudocódigo de la estrategia
def obtener_estado_completo(fecha):
    # 1. Obtener trenes programados del GTFS estático
    trenes_programados = gtfs.trips.filter(fecha=fecha)

    # 2. Obtener actualizaciones del GTFS-RT
    actualizaciones = gtfs_rt.descargar()

    # 3. Crear diccionario de retrasos
    retrasos = {a.trip_id: a.delay for a in actualizaciones}

    # 4. Combinar
    estado = []
    for tren in trenes_programados:
        delay = retrasos.get(tren.trip_id, 0)  # 0 si no está en GTFS-RT
        estado.append({
            "codigo_tren": tren.trip_short_name,
            "origen": obtener_origen(tren),
            "destino": obtener_destino(tren),
            "retraso_segundos": delay,
            "retraso_minutos": delay // 60
        })

    return estado
```

---

## 5. Marco Legal y Condiciones de Uso

### 5.1 Términos de Reutilización

Fuente: [data.renfe.com/legal](https://data.renfe.com/legal)

| Condición | Requisito |
|-----------|-----------|
| **Uso permitido** | Fines comerciales y no comerciales |
| **Atribución obligatoria** | "Origen de los datos: Renfe Operadora" |
| **Fecha de actualización** | Incluir cuando esté disponible |
| **Sin implicación de patrocinio** | No sugerir que Renfe apoya el proyecto |
| **Metadatos** | Conservar sin alterar |
| **Responsabilidad** | Uso bajo cuenta y riesgo del reutilizador |

### 5.2 Licencia

Todos los datasets se distribuyen bajo **Creative Commons Attribution 4.0 (CC-BY-4.0)**.

### 5.3 Contexto Legal Adicional

En **2024**, la Comisión Europea concluyó una investigación antimonopolio contra Renfe por negarse a compartir datos con plataformas de terceros. Como resultado:

- Renfe firmó compromisos legalmente vinculantes para proporcionar acceso extensivo a datos
- Incumplimiento puede conllevar multas de hasta el **10% de la facturación anual**
- Esto refuerza la estabilidad del acceso a los datos

Fuente: [Compromisos Renfe UE](https://www.renfe.com/content/dam/renfe/en/legal-information/communications/Compromisos-EN.pdf)

### 5.4 Garantías

Renfe **NO garantiza**:
- Continuidad en la disponibilidad de los datos
- Ausencia de errores u omisiones
- Actualización en intervalos específicos

**Implicación para el proyecto:** Necesario monitorear la disponibilidad de los endpoints y estar preparado para cambios.

---

## 6. Volumen de Datos Estimado

### 6.1 Feed GTFS-RT

| Período | Snapshots | Tamaño por snapshot | Total estimado |
|---------|-----------|---------------------|----------------|
| 5 min | 1 | ~150 KB | 150 KB |
| 1 hora | 12 | ~150 KB | 1.8 MB |
| 1 día | 288 | ~150 KB | 43 MB (JSON crudo) |
| 1 día | 288 | ~150 KB | ~3-5 MB (Parquet comprimido) |
| 1 mes | ~8,640 | - | ~90-150 MB (Parquet) |
| 1 año | ~105,000 | - | ~1-1.8 GB (Parquet) |

### 6.2 Feed de Avisos

| Período | Estimación |
|---------|------------|
| Por snapshot | ~10-50 KB |
| Por mes | ~1-5 MB |

### 6.3 GTFS Estático

| Archivo | Tamaño | Frecuencia de actualización |
|---------|--------|----------------------------|
| ZIP completo | 800 KB | ~1 vez al día |

**Estrategia:** Descargar semanalmente; almacenar solo la versión más reciente.

---

## 7. Descubrimientos Técnicos Importantes

### 7.1 Delay Negativos

El feed contiene delays negativos (ej: `-8280` segundos = -138 minutos).

**Interpretación probable:** Tren que salió con adelanto según el último reporte, o datos inconsistentes.

**Recomendación:** Tratar delays muy negativos como datos potencialmente erróneos; establecer umbral razonable (ej: `min(-300, delay)`).

### 7.2 Formato JSON vs Protobuf

El feed estándar GTFS-RT utiliza **Protocol Buffers**, pero Renfe lo expone en **JSON**.

**Ventaja:** Más simple de parsear, no requiere dependencias de Protobuf.

**Desventaja:** Tamaño ligeramente mayor.

### 7.3 Timestamps

El `timestamp` del header está en formato **Unix epoch** (segundos desde 1970-01-01).

Ejemplo: `1770496280` → 2026-02-08 ~10:30 UTC

---

## 8. Decisiones Técnicas Tomadas

### 8.1 Frecuencia de Captura

**Decisión:** Capturar cada **5 minutos**

| Opción | Ventajas | Desventajas |
|--------|----------|-------------|
| 30 seg (frecuencia real) | Máxima resolución | Datos demasiado voluminosos |
| 5 min | Balance resolución/volumen | ✅ **ELEGIDA** |
| 15 min | Menor volumen | Puede perder eventos |

**Justificación:** El feed se actualiza cada 30 seg, pero para análisis de retrasos ferroviarios, 5 min ofrece resolución suficiente sin sobrecargar almacenamiento.

### 8.2 Modelo de Datos

**Decisión:** Almacenar dos tipos de datos:

1. **Snapshots crudos (JSON)** - Primeros 30 días, para poder re-procesar
2. **Datos procesados (Parquet)** - Histórico completo con compactación

### 8.3 Estrategia de Compactación

Para mantener el repo dentro de límites de GitHub:

```
data/processed/circulaciones/
├── 2026-02.parquet          # Mes actual: detalle completo (~60-80 MB)
├── 2026-01.parquet          # Mes anterior: detalle completo
├── 2025-12.parquet          # Hace 2 meses: detalle completo
└── archive/
    ├── 2025-Q3-stats.parquet    # Trimestres antiguos: solo agregados
    └── 2025-Q4-stats.parquet
```

**Trigger de compactación:** Meses con más de 90 días de antigüedad.

---

## 9. Riesgos Identificados y Mitigación

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Endpoint cambia sin aviso | Media | Alto | Monitoreo + alertas; almacenar snapshots crudos |
| Rate limiting | Baja | Medio | Empezar con 5 min; reducir si hay problemas |
| Feed cae (errores 5xx) | Media | Medio | Reintentos exponenciales; alertas |
| Datos inconsistentes | Media | Bajo | Validación; limpieza de outliers |
| Formato de trip_id cambia | Baja | Alto | Versionado de schema; tests de regresión |
| Cambio a Protobuf | Baja | Medio | Parser flexible; detección automática de formato |

---

## 10. Conclusión

### 10.1 Viabilidad del Proyecto

| Aspecto | Estado |
|---------|--------|
| Disponibilidad de datos tiempo real | ✅ Confirmada |
| Calidad de datos | ✅ Adecuada |
| Marco legal | ✅ Favorable |
| Volumen de datos | ✅ Gestionable |
| Complejidad técnica | ✅ Media (afrontable) |

**Decisión:** ✅ **GO** - Proceder con Fase 1 (Pipeline de Ingesta)

### 10.2 Cambios Respecto al Plan Inicial

| Aspecto | Plan original | Descubrimiento | Ajuste necesario |
|---------|---------------|----------------|------------------|
| Contenido del GTFS-RT | Estado completo de todos los trenes | Solo trenes con retraso | Cruce con GTFS estático obligatorio |
| Formato GTFS-RT | Protobuf | JSON | Más simple de lo previsto |
| Geolocalización | Incluida en feed | No disponible | Omitir en MVP |
| Frecuencia de actualización | A determinar | 30 segundos | Usar 5 min para captura |

---

## 11. Próximos Pasos (Fase 1)

Con la fase 0 completada, la Fase 1 consistirá en:

1. **Configuración del proyecto** - Estructura de directorios, dependencias
2. **Implementación de fetchers** - Módulos para descargar cada feed
3. **Procesador de cruce** - Combinar GTFS estático + GTFS-RT
4. **Almacenamiento en Parquet** - Persistencia eficiente
5. **GitHub Actions** - Automatización de capturas cada 5 min

**Hitos de la Fase 1:**
- Día 1-2: Setup + fetchers básicos
- Día 3-4: Procesador + almacenamiento
- Día 5: GitHub Actions funcionando
- Día 6-7: Tests + documentación

---

## Apéndice A: Comandos Útiles

### Descarga manual de feeds

```bash
# GTFS Realtime
curl -s "https://gtfsrt.renfe.com/trip_updates_LD.json" | jq .

# GTFS Estático
curl -O "https://ssl.renfe.com/gtransit/Fichero_AV_LD/google_transit.zip"

# Avisos
curl -s "https://www.renfe.com/content/renfe/es/es/grupo-renfe/comunicacion/renfe-al-dia/avisos/jcr:content/root/responsivegrid/rfincidentreports_co.noticeresults.json" | jq .
```

### Listado de datasets vía API CKAN

```bash
# Todos los datasets
curl -s "https://data.renfe.com/api/3/action/package_list" | jq .

# Metadatos de un dataset específico
curl -s "https://data.renfe.com/api/3/action/package_show?id=horarios-viaje-alta-velocidad-larga-media-distancia" | jq .
```

---

## Apéndice B: Referencias

- [Portal data.renfe.com](https://data.renfe.com/)
- [Información Legal](https://data.renfe.com/legal)
- [GTFS Realtime Specification](https://gtfs.org/realtime/)
- [GTFS Schedule Reference](https://gtfs.org/schedule/reference/)
- [Renfe Antitrust Commitments (EU)](https://www.renfe.com/content/dam/renfe/en/legal-information/communications/Compromisos-EN.pdf)
- [CKAN API Documentation](https://docs.ckan.org/en/latest/api/)
