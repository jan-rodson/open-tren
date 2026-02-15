"""Tests para AvisosFetcher."""

import httpx
import pytest
import respx

from src.fetchers import AvisosFetcher, FetcherError


@pytest.mark.asyncio
async def test_fetch_avisos_success(sample_avisos_response: list[object], test_user_agent: str):
    """Test de fetch exitoso de avisos."""
    url = "https://www.renfe.com/.../json"

    with respx.mock:
        respx.get(url).mock(return_value=httpx.Response(200, json=sample_avisos_response))

        fetcher = AvisosFetcher(user_agent=test_user_agent, url=url)
        result = await fetcher.fetch()

        assert result.data == sample_avisos_response
        assert result.status_code == 200


@pytest.mark.asyncio
async def test_fetch_avisos_empty(test_user_agent: str):
    """Test de respuesta vacía."""
    url = "https://www.renfe.com/.../json"

    with respx.mock:
        route = respx.get(url).mock(return_value=httpx.Response(200, json=[]))

        fetcher = AvisosFetcher(user_agent=test_user_agent, url=url)
        result = await fetcher.fetch()

        assert result.data == []
        _ = route.call_count  # type: ignore[unused-call-result]


@pytest.mark.asyncio
async def test_fetch_avisos_error(test_user_agent: str):
    """Test de error al obtener avisos."""
    url = "https://www.renfe.com/.../json"

    with respx.mock:
        _ = respx.get(url).mock(return_value=httpx.Response(500))  # type: ignore[assignment]

        fetcher = AvisosFetcher(user_agent=test_user_agent, url=url)

        with pytest.raises(FetcherError) as exc_info:
            await fetcher.fetch()

        assert "500" in str(exc_info.value)
