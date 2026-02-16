"""Fetcher para datos de tiempo real GTFS-RT de Renfe."""

from datetime import UTC, datetime
from typing import Any, cast, override

from ..config import GTFS_RT_URL
from .base import BaseFetcher, FetcherResult


class GtfsRtFetcher(BaseFetcher[dict[str, Any]]):
    """Fetcher para el feed GTFS-RT de Renfe."""

    url: str

    def __init__(
        self,
        user_agent: str,
        url: str = GTFS_RT_URL,
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
    async def fetch(self) -> FetcherResult[dict[str, Any]]:
        """
        Obtiene el feed GTFS-RT de Renfe.

        Returns:
            FetcherResult con el JSON parseado y timestamp de captura.

        Raises:
            FetcherError: Si hay error al obtener los datos.
        """
        response = await self._http_get(self.url)
        data = cast(dict[str, Any], response.json())

        return FetcherResult(
            data=data,
            timestamp=datetime.now(UTC),
            url=str(response.url),
            status_code=response.status_code,
        )
