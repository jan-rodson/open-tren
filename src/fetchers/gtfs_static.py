"""Fetcher para GTFS estático de Renfe."""

import zipfile
from io import BytesIO
from typing import Any, ClassVar

from ..config import GTFS_STATIC_URL
from .base import BaseFetcher, FetcherError, FetcherResult


class GtfsStaticFetcher(BaseFetcher):
    """Fetcher para el GTFS estático de Renfe (archivo ZIP)."""

    DEFAULT_TIMEOUT: ClassVar[float] = 60.0  # Más tiempo porque es un ZIP

    # Archivos GTFS requeridos según especificación
    REQUIRED_GTFS_FILES: ClassVar[frozenset[str]] = frozenset(
        {"trips.txt", "stop_times.txt", "stops.txt", "routes.txt"}
    )

    def __init__(
        self,
        url: str = GTFS_STATIC_URL,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.url = url

    async def fetch(self) -> FetcherResult:
        """
        Obtiene el archivo GTFS estático de Renfe.

        Returns:
            FetcherResult con el contenido binario del ZIP.

        Raises:
            FetcherError: Si hay error al obtener los datos o el contenido no es un ZIP válido.
        """
        result = await self._http_get(self.url, as_json=False)

        # Validar que es un ZIP válido con archivos GTFS requeridos
        try:
            with zipfile.ZipFile(BytesIO(result.data)) as zf:
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

        return result
