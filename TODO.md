# TODO - Open Tren

## Processors(`src/processors/`)

- [ ] **Validación de respuestas con Pydantic**
  - Crear modelos Pydantic para cada respuesta de API (GTFS-RT, Avisos, GTFS estático)
  - Validar estructura mínima antes de procesar
  - Requiere conocer bien los esquemas reales de las APIs de Renfe

## Models (`src/models/schemas.py`)

### Circulacion Model

- [ ] `hora_salida_programada`, `hora_salida_real`, `hora_llegada_programada`, `hora_llegada_estimada`
  - **Problema**: Son strings, no hay validación de formato
  - **Mejora**: Usar `datetime.time` o validar formato HH:MM con regex

- [ ] `estado`
  - **Problema**: String libre, puede ser cualquier valor
  - **Mejora**: Usar `Enum` con valores válidos (PROGRAMADO, EN_RUTA, LLEGADO, CANCELADO)

- [ ] `tipo_servicio`
  - **Problema**: String libre, sin validación
  - **Mejora**: Usar `Enum` con valores de `config.TIPOS_SERVICIO`

- [ ] `retraso_minutos`
  - **Problema**: Puede ser negativo
  - **Mejora**: Añadir `Field(ge=0)` para garantizar >= 0

- [ ] `codigo_tren`
  - **Problema**: No hay formato definido
  - **Mejora**: Añadir validador de regex si se conoce el formato

### Incidencia Model

- [ ] `tipo`
  - **Problema**: String libre
  - **Mejora**: Usar `Enum` (OBRAS, INCIDENCIA, HUELGA, METEOROLOGIA)

- [ ] `fecha_inicio`, `fecha_fin`
  - **Problema**: Son strings, no fechas validadas
  - **Mejora**: Usar `datetime.date` o validar formato
