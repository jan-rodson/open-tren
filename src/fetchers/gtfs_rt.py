"""Fetcher para datos de tiempo real GTFS-RT de Renfe."""

from typing import Any

from ..config import GTFS_RT_URL
from .base import BaseFetcher, FetcherResult


class GtfsRtFetcher(BaseFetcher):
    """Fetcher para el feed GTFS-RT de Renfe."""

    def __init__(
        self,
        url: str = GTFS_RT_URL,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.url = url

    async def fetch(self) -> FetcherResult:
        """
        Obtiene el feed GTFS-RT de Renfe.

        Returns:
            FetcherResult con el JSON parseado y timestamp de captura.

        Raises:
            FetcherError: Si hay error al obtener los datos.
        """
        return await self._http_get(self.url, as_json=True)
