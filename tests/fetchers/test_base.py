"""Tests para clases base del módulo fetchers."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import httpx
import pytest
import respx

from src.fetchers.base import BaseFetcher, FetcherError, FetcherResult


def test_fetcher_result_creation():
    """Test de creación de FetcherResult."""
    result = FetcherResult(
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

    result = FetcherResult(
        data={"test": "value"},
        timestamp=datetime.now(UTC),
        url="https://example.com",
    )

    with pytest.raises(FrozenInstanceError):
        result.data = "other"


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
async def test_base_fetcher_context_manager():
    """Test del context manager de BaseFetcher."""
    url = "https://httpbin.org/get"

    class TestFetcher(BaseFetcher):
        async def fetch(self):
            client = await self._get_client()
            response = await client.get(url)
            return FetcherResult.from_response(response)

    with respx.mock:
        respx.get(url).mock(return_value=httpx.Response(200, json={}))

        async with TestFetcher() as fetcher:
            # Verificar que el cliente se crea correctamente
            client = await fetcher._get_client()
            assert client is not None

    # Al salir, el cliente debe estar cerrado
    assert fetcher._client is None


@pytest.mark.asyncio
async def test_base_fetcher_custom_user_agent():
    """Test de user agent personalizado."""
    url = "https://test.com/api"

    class TestFetcher(BaseFetcher):
        async def fetch(self):
            client = await self._get_client()
            response = await client.get(url)
            return FetcherResult.from_response(response)

    with respx.mock:
        route = respx.get(url).mock(return_value=httpx.Response(200, json={}))

        fetcher = TestFetcher(user_agent="MyCustomAgent/1.0")
        await fetcher.fetch()

        # Verificar que la petición se hizo con el user agent correcto
        assert route.call_count == 1
        request = route.calls[0].request
        assert "MyCustomAgent/1.0" in request.headers["user-agent"]


def test_fetcher_result_invalid_json():
    """Test de manejo de JSON inválido."""
    import httpx

    # Response con JSON inválido
    request = httpx.Request("GET", "https://example.com")
    response = httpx.Response(200, text="{invalid json}", request=request)

    with pytest.raises(FetcherError) as exc_info:
        FetcherResult.from_response(response, as_json=True)

    assert "JSON inválido" in str(exc_info.value)
    assert exc_info.value.status_code == 200
