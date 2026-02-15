"""Configuración y constantes del proyecto."""

from pathlib import Path

# Directorios base
BASE_DIR: Path = Path(__file__).parent.parent
DATA_DIR: Path = BASE_DIR / "data"
RAW_DATA_DIR: Path = DATA_DIR / "raw"
PROCESSED_DATA_DIR: Path = DATA_DIR / "processed"
GTFS_DIR: Path = DATA_DIR / "gtfs"

# Endpoints de Renfe
GTFS_RT_URL: str = "https://gtfsrt.renfe.com/trip_updates_LD.json"
GTFS_STATIC_URL: str = "https://ssl.renfe.com/gtransit/Fichero_AV_LD/google_transit.zip"
AVISOS_URL: str = "https://www.renfe.com/content/renfe/es/es/grupo-renfe/comunicacion/renfe-al-dia/avisos/jcr:content/root/responsivegrid/rfincidentreports_co.noticeresults.json"

# Frecuencia de captura (segundos)
CAPTURE_INTERVAL_SECONDS: int = 300  # 5 minutos

# Umbrales de retraso (minutos)
DELAY_THRESHOLD_PUNTUAL: int = 5
DELAY_THRESHOLD_GRAVE: int = 15
DELAY_THRESHOLD_MUY_GRAVE: int = 30

# Tipos de servicio
TIPOS_SERVICIO: tuple[str, ...] = (
    "AVE",
    "AVLO",
    "ALVIA",
    "EUROMED",
    "MD",
    "Intercity",
    "Trenhotel",
)
