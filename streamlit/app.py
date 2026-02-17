import logging
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
from lib.db import (
    get_circulaciones,
    get_destinos,
    get_estadisticas_rutas,
    get_fechas_disponibles,
    get_origenes,
    get_tipos_servicio,
)

import streamlit as st

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Open Tren - Dashboard",
    page_icon=":material/train:",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def calcular_tiempo_trayecto_minutos(hora_salida: str, hora_llegada: str) -> float:
    """Calcula tiempo de trayecto en minutos."""
    try:
        salida = pd.to_datetime(hora_salida, format="%H:%M:%S")
        llegada = pd.to_datetime(hora_llegada, format="%H:%M:%S")
        if llegada < salida:
            llegada += pd.Timedelta(days=1)
        return (llegada - salida).total_seconds() / 60
    except Exception:
        return 0


def main():
    st.title(":material/train: Open Tren")
    st.markdown("Dashboard de puntualidad ferroviaria en España")

    with st.spinner("Cargando datos..."):
        fechas = get_fechas_disponibles()
        origenes = get_origenes()
        destinos = get_destinos()
        tipos = get_tipos_servicio()

    if not fechas:
        st.error("No hay datos disponibles en la base de datos")
        return

    st.markdown("### Filtros")

    from datetime import time

    col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns(
        [2, 1, 2, 2, 2], vertical_alignment="bottom"
    )

    fecha_max = max(fechas)
    fecha_min = min(fechas)
    fecha_hoy = date.today()

    with col_f1:
        fechas_seleccionadas = st.date_input(
            "Fechas",
            value=(fecha_hoy, fecha_hoy),
            min_value=fecha_min,
            max_value=fecha_max,
        )

    if isinstance(fechas_seleccionadas, tuple) and len(fechas_seleccionadas) == 2:
        fecha_inicio, fecha_fin = fechas_seleccionadas
    else:
        fecha_inicio = fecha_fin = fechas_seleccionadas

    with col_f2:
        with st.expander("Hora salida", expanded=False):
            hora_inicio = st.time_input("Desde", value=time(0, 0), key="hora_inicio")
            hora_fin = st.time_input("Hasta", value=time(23, 59), key="hora_fin")

    with col_f3:
        tipo_servicio = st.selectbox(
            "Tipo de servicio",
            options=["Todos"] + tipos,
        )

    with col_f4:
        origen = st.selectbox(
            "Origen",
            options=["Todos"] + origenes,
        )

    with col_f5:
        destino = st.selectbox(
            "Destino",
            options=["Todos"] + destinos,
        )

    if fecha_inicio > fecha_fin:
        st.error("La fecha de inicio debe ser anterior o igual a la fecha fin")
        return

    with st.spinner("Cargando circulaciones..."):
        df = get_circulaciones(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            tipo_servicio=tipo_servicio if tipo_servicio != "Todos" else None,
            origen=origen if origen != "Todos" else None,
            destino=destino if destino != "Todos" else None,
        )

    if df.empty:
        st.info("No hay circulaciones que coincidan con los filtros seleccionados")
        return

    df["delay_minutos"] = df["delay_segundos"] // 60
    df["tiempo_trayecto"] = df.apply(
        lambda r: calcular_tiempo_trayecto_minutos(str(r["hora_salida"]), str(r["hora_llegada"])),
        axis=1,
    )
    df["delay_pct"] = df.apply(
        lambda r: (
            (r["delay_minutos"] / r["tiempo_trayecto"] * 100) if r["tiempo_trayecto"] > 0 else 0
        ),
        axis=1,
    )

    total = len(df)
    con_retraso = len(df[df["delay_minutos"] > 0])
    pct_retraso = (con_retraso / total * 100) if total > 0 else 0
    retraso_medio = df["delay_minutos"].mean()
    retraso_medio_pct = df["delay_pct"].mean()

    st.markdown("---")
    st.markdown("### Indicadores")

    col_k1, col_k2, col_k3, col_k4, col_k5 = st.columns(5)

    with col_k1:
        st.metric(
            label="Total trenes",
            value=total,
        )

    with col_k2:
        st.metric(
            label="Con retraso",
            value=con_retraso,
        )

    with col_k3:
        st.metric(
            label="% con retraso",
            value=f"{pct_retraso:.1f}%",
        )

    with col_k4:
        st.metric(
            label="Retraso medio (min)",
            value=f"{retraso_medio:.1f}",
        )

    with col_k5:
        st.metric(
            label="Retraso medio (%)",
            value=f"{retraso_medio_pct:.1f}%",
        )

    st.markdown("---")
    st.markdown(f"### Circulaciones ({total} resultados)")

    df_display = df[
        [
            "codigo_tren",
            "origen_nombre",
            "destino_nombre",
            "hora_salida",
            "hora_llegada",
            "delay_minutos",
            "delay_pct",
            "tipo_servicio",
        ]
    ].copy()

    df_display.columns = [
        "Tren",
        "Origen",
        "Destino",
        "Salida",
        "Llegada",
        "Retraso (min)",
        "Retraso (%)",
        "Tipo",
    ]

    df_display["Salida"] = pd.to_datetime(df_display["Salida"], format="%H:%M:%S").dt.strftime(
        "%H:%M"
    )
    df_display["Llegada"] = pd.to_datetime(df_display["Llegada"], format="%H:%M:%S").dt.strftime(
        "%H:%M"
    )

    max_pct = df_display["Retraso (%)"].max() if df_display["Retraso (%)"].max() > 0 else 100

    def color_fila(row):
        pct = row["Retraso (%)"]
        if max_pct == 0:
            return ["background-color: #d1fae5"] * len(row)
        t = pct / max_pct
        if t < 0.25:
            factor = t / 0.25
            r = int(34 + (250 - 34) * factor)
            g = int(197 + (250 - 197) * factor)
            b = int(94 + (229 - 94) * factor)
        elif t < 0.5:
            factor = (t - 0.25) / 0.25
            r = int(250 + (245 - 250) * factor)
            g = int(250 + (204 - 250) * factor)
            b = int(229 + (157 - 229) * factor)
        elif t < 0.75:
            factor = (t - 0.5) / 0.25
            r = int(245 + (249 - 245) * factor)
            g = int(204 + (115 - 204) * factor)
            b = int(157 + (26 - 157) * factor)
        else:
            factor = (t - 0.75) / 0.25
            r = int(249 + (220 - 249) * factor)
            g = int(115 + (38 - 115) * factor)
            b = int(26 + (38 - 26) * factor)
        return [f"background-color: rgb({r},{g},{b})"] * len(row)

    df_display = df_display.sort_values("Retraso (%)", ascending=False)

    styled = df_display.style.apply(color_fila, axis=1).format(
        {
            "Retraso (min)": "{:.0f}",
            "Retraso (%)": "{:.1f}",
        },
        na_rep="-",
    )

    df_display = df_display.sort_values("Retraso (%)", ascending=False)

    st.dataframe(
        styled,
        column_config={
            "Tren": st.column_config.TextColumn("Tren", width="small"),
            "Origen": st.column_config.TextColumn("Origen", width="medium"),
            "Destino": st.column_config.TextColumn("Destino", width="medium"),
            "Salida": st.column_config.TextColumn("Salida", width="small"),
            "Llegada": st.column_config.TextColumn("Llegada", width="small"),
            "Retraso (min)": st.column_config.NumberColumn("Retraso (min)", width="small"),
            "Retraso (%)": st.column_config.NumberColumn("Retraso (%)", width="small"),
            "Tipo": st.column_config.TextColumn("Tipo", width="small"),
        },
        width="stretch",
        hide_index=True,
        height="auto",
    )

    st.markdown("---")
    st.markdown("### Análisis: Retraso por ruta")

    with st.spinner("Cargando estadísticas por ruta..."):
        df_rutas = get_estadisticas_rutas(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            tipo_servicio=tipo_servicio if tipo_servicio != "Todos" else None,
            origen=origen if origen != "Todos" else None,
            destino=destino if destino != "Todos" else None,
        )

    if not df_rutas.empty:
        df_rutas["ruta_label"] = df_rutas["origen_nombre"] + " → " + df_rutas["destino_nombre"]

        fig = px.scatter(
            df_rutas,
            x="trenes_con_retraso",
            y="retraso_medio_minutos",
            color="tipo_servicio",
            hover_name="ruta_label",
            hover_data={
                "trenes_con_retraso": True,
                "retraso_medio_minutos": ":,.1f",
                "retraso_medio_pct": ":.1f",
                "total_trenes": True,
                "tipo_servicio": True,
            },
            labels={
                "trenes_con_retraso": "Trenes con retraso",
                "retraso_medio_minutos": "Retraso medio (min)",
                "tipo_servicio": "Tipo de servicio",
            },
            title="Trenes con retraso vs Retraso medio por ruta",
        )
        fig.update_layout(height=500)
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("No hay suficientes datos para el gráfico")


if __name__ == "__main__":
    main()
