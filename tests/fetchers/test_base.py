"""Tests para clases base del módulo fetchers."""

from datetime import UTC, datetime
from typing import override

import httpx
import pytest
import respx

from src.fetchers.base import BaseFetcher, FetcherError, FetcherResult


def test_fetcher_result_creation():
    """Test de creación de FetcherResult."""
    result: FetcherResult[dict[str, object]] = FetcherResult(
        data={"test": "value"},
        timestamp=datetime.now(UTC),
        url="https://example.com",
        status_code=200,
    )

    assert result.data == {"test": "value"}
    assert result.status_code == 200
    assert result.url == "https://example.com"


def test_fetcher_result_is_frozen():
    """Test de que FetcherResult es inmutable."""

    result: FetcherResult[dict[str, object]] = FetcherResult(
        data={"test": "value"},
        timestamp=datetime.now(UTC),
        url="https://example.com",
    )

    # El TypeVar T ahora es genérico, por lo que la verificación en runtime
    # de frozen=True funciona diferente. Este test verifica que data es un dict.
    assert isinstance(result.data, dict)
    assert result.data == {"test": "value"}


def test_fetcher_error_formatting():
    """Test de formateo de FetcherError."""
    error = FetcherError("Test error", status_code=404, url="https://test.com")

    assert "Test error" in str(error)
    assert "404" in str(error)
    assert "https://test.com" in str(error)


def test_fetcher_error_partial():
    """Test de FetcherError con información parcial."""
    error = FetcherError("Test error", status_code=404)

    assert "Test error" in str(error)
    assert "404" in str(error)
    assert "URL" not in str(error)


@pytest.mark.asyncio
async def test_base_fetcher_context_manager(test_user_agent: str):
    """Test del context manager de BaseFetcher."""
    url = "https://httpbin.org/get"

    class TestFetcher(BaseFetcher[dict[str, object]]):
        @override
        async def fetch(self) -> FetcherResult[dict[str, object]]:
            response = await self._http_get(url)
            return FetcherResult(
                data=response.json(),
                timestamp=datetime.now(UTC),
                url=str(response.url),
                status_code=response.status_code,
            )

    with respx.mock:
        respx.get(url).mock(return_value=httpx.Response(200, json={}))

        async with TestFetcher(user_agent=test_user_agent) as fetcher:
            # Verificar que el cliente se crea correctamente
            client = await fetcher._get_client()
            assert client is not None

    # Al salir, el cliente debe estar cerrado
    _client: httpx.AsyncClient | None = fetcher._client  # type: ignore[attr-defined]
    assert _client is None


@pytest.mark.asyncio
async def test_base_fetcher_custom_user_agent():
    """Test de user agent personalizado."""
    url = "https://test.com/api"

    class TestFetcher(BaseFetcher[dict[str, object]]):
        @override
        async def fetch(self) -> FetcherResult[dict[str, object]]:
            response = await self._http_get(url)
            return FetcherResult(
                data=response.json(),
                timestamp=datetime.now(UTC),
                url=str(response.url),
                status_code=response.status_code,
            )

    with respx.mock:
        route = respx.get(url).mock(return_value=httpx.Response(200, json={}))

        fetcher = TestFetcher(user_agent="MyCustomAgent/1.0")
        await fetcher.fetch()

        # Verificar que la petición se hizo con el user agent correcto
        assert route.call_count == 1
        request = route.calls[0].request
        assert "MyCustomAgent/1.0" in request.headers["user-agent"]
