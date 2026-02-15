"""Fetcher para GTFS estático de Renfe."""

import zipfile
from datetime import UTC, datetime
from io import BytesIO
from typing import ClassVar, override

from ..config import GTFS_STATIC_URL
from .base import BaseFetcher, FetcherError, FetcherResult


class GtfsStaticFetcher(BaseFetcher[bytes]):
    """Fetcher para el GTFS estático de Renfe (archivo ZIP)."""

    DEFAULT_TIMEOUT: ClassVar[float] = 60.0  # Más tiempo porque es un ZIP

    # Archivos GTFS requeridos según especificación
    REQUIRED_GTFS_FILES: ClassVar[frozenset[str]] = frozenset(
        {"trips.txt", "stop_times.txt", "stops.txt", "routes.txt"}
    )

    url: str

    def __init__(
        self,
        user_agent: str,
        url: str = GTFS_STATIC_URL,
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
    async def fetch(self) -> FetcherResult[bytes]:
        """
        Obtiene el archivo GTFS estático de Renfe.

        Returns:
            FetcherResult con el contenido binario del ZIP.

        Raises:
            FetcherError: Si hay error al obtener los datos o el contenido no es un ZIP válido.
        """
        response = await self._http_get(self.url)
        data = response.content

        # Validar que es un ZIP válido con archivos GTFS requeridos
        try:
            with zipfile.ZipFile(BytesIO(data)) as zf:
                files = set(zf.namelist())
                if not self.REQUIRED_GTFS_FILES.issubset(files):
                    missing = self.REQUIRED_GTFS_FILES - files
                    raise FetcherError(
                        f"ZIP no contiene archivos GTFS obligatorios: {missing}",
                        url=self.url,
                    )
        except zipfile.BadZipFile as e:
            raise FetcherError(
                f"El contenido descargado no es un ZIP válido: {e}",
                url=self.url,
            ) from e

        return FetcherResult(
            data=data,
            timestamp=datetime.now(UTC),
            url=str(response.url),
            status_code=response.status_code,
        )
