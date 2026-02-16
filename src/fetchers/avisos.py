"""Fetcher para avisos e incidencias de Renfe."""

from datetime import UTC, datetime
from typing import Any, cast, override

from ..config import AVISOS_URL
from .base import BaseFetcher, FetcherResult


class AvisosFetcher(BaseFetcher[list[Any]]):
    """Fetcher para el feed de avisos de Renfe."""

    url: str

    def __init__(
        self,
        user_agent: str,
        url: str = AVISOS_URL,
        timeout: float = BaseFetcher.DEFAULT_TIMEOUT,
        max_retries: int = BaseFetcher.MAX_RETRIES,
    ) -> None:
        super().__init__(
            user_agent=user_agent,
            timeout=timeout,
            max_retries=max_retries,
        )
        self.url = url

    @override
    async def fetch(self) -> FetcherResult[list[Any]]:
        """
        Obtiene los avisos de Renfe.

        Returns:
            FetcherResult con la lista de avisos y timestamp de captura.

        Raises:
            FetcherError: Si hay error al obtener los datos.
        """
        response = await self._http_get(self.url)
        data = cast(list[Any], response.json())

        return FetcherResult(
            data=data,
            timestamp=datetime.now(UTC),
            url=str(response.url),
            status_code=response.status_code,
        )
