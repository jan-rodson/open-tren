"""Clases base y excepciones para fetchers."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from types import TracebackType
from typing import Any, ClassVar, Generic, Self, TypeVar

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bytes, dict[str, Any], list[Any])


class FetcherError(Exception):
    """Excepción base para errores en fetchers."""

    message: str
    status_code: int | None
    url: str | None

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        url: str | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.url = url
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        parts = [self.message]
        if self.url:
            parts.append(f"URL: {self.url}")
        if self.status_code:
            parts.append(f"Status: {self.status_code}")
        return " | ".join(parts)


@dataclass(frozen=True)
class FetcherResult(Generic[T]):
    """Resultado inmutable de una operación de fetch."""

    data: T
    timestamp: datetime
    url: str
    status_code: int = 200


class BaseFetcher(ABC, Generic[T]):
    """Clase base para fetchers de APIs HTTP."""

    DEFAULT_TIMEOUT: ClassVar[float] = 30.0
    MAX_RETRIES: ClassVar[int] = 3

    timeout: float
    user_agent: str
    max_retries: int

    def __init__(
        self,
        user_agent: str,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = MAX_RETRIES,
    ) -> None:
        self.timeout = timeout
        self.user_agent = user_agent
        self.max_retries = max_retries
        self._client: httpx.AsyncClient | None = None

    @abstractmethod
    async def fetch(self) -> FetcherResult[T]:
        """Obtiene datos del endpoint. Debe ser implementado por subclases."""

    async def _get_client(self) -> httpx.AsyncClient:
        """Obtiene o crea el cliente HTTP asíncrono."""
        if self._client is None or self._client.is_closed:
            headers = {"User-Agent": self.user_agent}
            self._client = httpx.AsyncClient(timeout=self.timeout, headers=headers)
        return self._client

    async def _http_get(self, url: str) -> httpx.Response:
        """Realiza petición GET HTTP con reintentos.

        Args:
            url: URL a la que hacer la petición.

        Returns:
            Respuesta HTTP completa para que el fetcher procese los datos.

        Raises:
            FetcherError: Si después de los reintentos la petición falla.
        """
        retryer = retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, max=10),
            retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
            reraise=True,
        )

        @retryer
        async def _do_request() -> httpx.Response:
            client = await self._get_client()
            response = await client.get(url)
            response.raise_for_status()
            return response

        try:
            return await _do_request()
        except httpx.HTTPError as e:
            raise self._handle_error(e, url) from e

    async def close(self) -> None:
        """Cierra el cliente HTTP."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> Self:
        """Soporte para context manager asíncrono."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Cierra el cliente al salir del context manager."""
        await self.close()

    def _handle_error(self, error: Exception, url: str) -> FetcherError:
        """Convierte excepciones de httpx a FetcherError."""
        logger.debug("Error al obtener %s: %s", url, error)

        if isinstance(error, httpx.TimeoutException):
            return FetcherError("Timeout al obtener datos", url=url)
        if isinstance(error, httpx.HTTPStatusError):
            status = error.response.status_code
            if 400 <= status < 500:
                msg = f"Error de cliente (HTTP {status})"
            elif 500 <= status < 600:
                msg = f"Error de servidor (HTTP {status})"
            else:
                msg = f"Error HTTP {status}"
            return FetcherError(msg, status_code=status, url=url)
        if isinstance(error, httpx.HTTPError):
            return FetcherError(f"Error de conexión: {error}", url=url)
        return FetcherError(f"Error inesperado: {error}", url=url)
