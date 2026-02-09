"""Configuración y constantes del proyecto."""

from pathlib import Path

# Directorios base
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
GTFS_DIR = DATA_DIR / "gtfs"

# Endpoints de Renfe
GTFS_RT_URL = "https://gtfsrt.renfe.com/trip_updates_LD.json"
GTFS_STATIC_URL = "https://ssl.renfe.com/gtransit/Fichero_AV_LD/google_transit.zip"
AVISOS_URL = "https://www.renfe.com/content/renfe/es/es/grupo-renfe/comunicacion/renfe-al-dia/avisos/jcr:content/root/responsivegrid/rfincidentreports_co.noticeresults.json"

# Frecuencia de captura (segundos)
CAPTURE_INTERVAL_SECONDS = 300  # 5 minutos

# Umbrales de retraso (minutos)
DELAY_THRESHOLD_PUNTUAL = 5
DELAY_THRESHOLD_GRAVE = 15
DELAY_THRESHOLD_MUY_GRAVE = 30

# Tipos de servicio
TIPOS_SERVICIO = ["AVE", "AVLO", "ALVIA", "EUROMED", "MD", "Intercity", "Trenhotel"]
