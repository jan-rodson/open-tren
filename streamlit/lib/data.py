import logging
import random
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

import streamlit as st

from .types import Circulacion, Estacion, Incidencia, KPIs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


ESTACIONES = [
    Estacion("MD", "Madrid Atocha", 40.4115, -3.6942),
    Estacion("BCN", "Barcelona Sants", 41.3795, 2.1404),
    Estacion("VLL", "Valencia Joaquín Sorolla", 39.4699, -0.3763),
    Estacion("SEV", "Santa Justa (Sevilla)", 37.3896, -5.9845),
    Estacion("MAL", "María Zambrano (Málaga)", 36.7200, -4.4182),
    Estacion("ZAZ", "Zaragoza Delicias", 41.6456, -0.9325),
    Estacion("BCN3", "Barcelona P. Gràcia", 41.3973, 2.1748),
    Estacion("MIR", "Miranda de Ebro", 42.6833, -2.9500),
    Estacion("PAM", "Pamplona", 42.8125, -1.6458),
    Estacion("BIO", "Bilbao Abando", 43.2596, -2.9353),
]


INCIDENCIAS_DEMO = [
    Incidencia(
        id="INC001",
        titulo="Corte en vía Sevilla-Córdoba",
        descripcion="Corte de vía por trabajos de mantenimiento. Retrasos estimados de 20-30 minutos.",
        fecha_inicio=datetime.now() - timedelta(hours=2),
        fecha_fin=None,
        tipo="Infraestructura",
        afectados=["AV05", "AV12", "AV23"],
    ),
    Incidencia(
        id="INC002",
        titulo="Fallo técnico en Valencia",
        descripcion="Fallo en sistema de señalización. Servicios con retrasos menores.",
        fecha_inicio=datetime.now() - timedelta(hours=4),
        fecha_fin=datetime.now() - timedelta(minutes=30),
        tipo="Técnico",
        afectados=["LD08", "LD15"],
    ),
]


@st.cache_data(ttl=300, show_spinner=False)
def generar_circulaciones(
    num: int = 50, fecha: Optional[datetime] = None, seed: int = 42
) -> list[Circulacion]:
    random.seed(seed)
    fecha = fecha or datetime.now()
    circulaciones = []

    for i in range(num):
        tipo_servicio = random.choice(["AV", "LD", "MD"])

        origen = random.choice(ESTACIONES)
        destino = random.choice([e for e in ESTACIONES if e.id != origen.id])

        hora_salida = fecha + timedelta(
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
        )

        duracion_minutos = random.randint(60, 300)
        hora_llegada = hora_salida + timedelta(minutes=duracion_minutos)

        retraso = max(0, random.gauss(5, 15))

        circulacion = Circulacion(
            id=f"CIR{i:04d}",
            tren=f"{tipo_servicio}{random.randint(100, 9999)}",
            origen_id=origen.id,
            origen_nombre=origen.nombre,
            destino_id=destino.id,
            destino_nombre=destino.nombre,
            hora_salida=hora_salida,
            hora_llegada=hora_llegada,
            retraso_minutos=round(retraso, 1),
            tipo_servicio=tipo_servicio,  # type: ignore[arg-type]
        )
        circulaciones.append(circulacion)

    return circulaciones


@st.cache_data(ttl=300, show_spinner=False)
def calcular_kpis(circulaciones: list[Circulacion]) -> KPIs:
    if not circulaciones:
        return KPIs(0, 0.0, 0.0, 0)

    total = len(circulaciones)
    puntuales = sum(1 for c in circulaciones if c.retraso_minutos <= 5)
    retraso_prom = sum(c.retraso_minutos for c in circulaciones) / total

    return KPIs(
        trenes_en_circulacion=total,
        tasa_puntualidad=round((puntuales / total) * 100, 1),
        retraso_promedio=round(retraso_prom, 1),
        total_circulaciones=total,
    )


@st.cache_data(ttl=300, show_spinner=False)
def circulaciones_to_dataframe(circulaciones: list[Circulacion]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ID": c.id,
                "Tren": c.tren,
                "Origen": c.origen_nombre,
                "Destino": c.destino_nombre,
                "Salida": c.hora_salida.strftime("%H:%M"),
                "Llegada": c.hora_llegada.strftime("%H:%M"),
                "Retraso (min)": c.retraso_minutos,
                "Tipo": c.tipo_servicio,
            }
            for c in circulaciones
        ]
    )


@st.cache_data(ttl=3600, show_spinner=False)
def get_incidencias_demo() -> list[Incidencia]:
    return INCIDENCIAS_DEMO
