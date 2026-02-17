# Open Tren - Dashboard Streamlit

Dashboard de puntualidad ferroviaria en España.

## Estructura

```
streamlit/
├── app.py                     # Entry point principal
├── requirements.txt           # Dependencias de Python
├── .streamlit/
│   └── config.toml            # Configuración del tema
├── lib/
│   ├── __init__.py
│   ├── types.py               # Type hints y modelos de datos
│   ├── data.py                # Generador de datos mock
│   ├── db.py                  # Placeholder para conexión PostgreSQL
│   └── queries.py             # Consultas SQL placeholder
└── pages/
    ├── 1_🏠_Principal.py      # Dashboard principal
    ├── 2_🚨_Incidencias.py    # Página de incidencias
    └── 3_📊_Histórico.py      # Página de histórico
```

## Instalación

```bash
cd streamlit
pip install -r requirements.txt
```

## Ejecución

```bash
streamlit run app.py
```

## Estado Actual

- [x] Estructura base del proyecto
- [x] Tema personalizado (basado en categorizador-gastos)
- [x] Generador de datos mock
- [x] Página Principal con KPIs, mapa y tabla
- [x] Página de Incidencias
- [x] Página Histórico con gráficos
- [ ] Conexión con PostgreSQL/Neon
- [ ] Migración a datos reales

## Próximos Pasos

1. Configurar conexión con PostgreSQL
2. Implementar fetchers de datos reales
3. Reemplazar datos mock con datos de producción
