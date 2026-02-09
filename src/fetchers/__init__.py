"""Fetchers para descargar datos de Renfe."""

from .avisos import AvisosFetcher
from .base import BaseFetcher, FetcherError, FetcherResult
from .gtfs_rt import GtfsRtFetcher
from .gtfs_static import GtfsStaticFetcher

__all__ = [
    "BaseFetcher",
    "FetcherError",
    "FetcherResult",
    "GtfsRtFetcher",
    "AvisosFetcher",
    "GtfsStaticFetcher",
]
