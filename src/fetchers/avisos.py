"""Fetcher para avisos e incidencias de Renfe."""

from typing import Any

from ..config import AVISOS_URL
from .base import BaseFetcher, FetcherResult


class AvisosFetcher(BaseFetcher):
    """Fetcher para el feed de avisos de Renfe."""

    def __init__(
        self,
        url: str = AVISOS_URL,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.url = url

    async def fetch(self) -> FetcherResult:
        """
        Obtiene los avisos de Renfe.

        Returns:
            FetcherResult con la lista de avisos y timestamp de captura.

        Raises:
            FetcherError: Si hay error al obtener los datos.
        """
        return await self._http_get(self.url, as_json=True)
