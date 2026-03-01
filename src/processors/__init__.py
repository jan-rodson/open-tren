"""Procesadores de datos."""

from src.processors.gtfs_rt import GtfsRtLoader
from src.processors.gtfs_static import GtfsStaticLoader

__all__ = [
    "GtfsStaticLoader",
    "GtfsRtLoader",
]
