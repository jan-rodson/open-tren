"""Tests para GtfsRtFetcher."""

from datetime import datetime

import httpx
import pytest
import respx

from src.fetchers import FetcherError, GtfsRtFetcher


@pytest.mark.asyncio
async def test_fetch_success(sample_gtfs_rt_response):
    """Test de fetch exitoso."""
    url = "https://gtfsrt.renfe.com/trip_updates_LD.json"

    with respx.mock:
        respx.get(url).mock(return_value=httpx.Response(200, json=sample_gtfs_rt_response))

        fetcher = GtfsRtFetcher(url=url)
        result = await fetcher.fetch()

        assert result.data == sample_gtfs_rt_response
        assert isinstance(result.timestamp, datetime)
        assert result.status_code == 200
        assert result.url == url


@pytest.mark.asyncio
async def test_fetch_with_context_manager(sample_gtfs_rt_response):
    """Test usando context manager."""
    url = "https://gtfsrt.renfe.com/trip_updates_LD.json"

    with respx.mock:
        respx.get(url).mock(return_value=httpx.Response(200, json=sample_gtfs_rt_response))

        async with GtfsRtFetcher(url=url) as fetcher:
            result = await fetcher.fetch()
            assert result.data == sample_gtfs_rt_response


@pytest.mark.asyncio
async def test_fetch_http_error():
    """Test de manejo de errores HTTP."""
    url = "https://gtfsrt.renfe.com/trip_updates_LD.json"

    with respx.mock:
        respx.get(url).mock(return_value=httpx.Response(404))

        fetcher = GtfsRtFetcher(url=url)

        with pytest.raises(FetcherError) as exc_info:
            await fetcher.fetch()

        assert "404" in str(exc_info.value)
        assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_fetch_timeout():
    """Test de manejo de timeout."""
    url = "https://gtfsrt.renfe.com/trip_updates_LD.json"

    with respx.mock:
        respx.get(url).mock(side_effect=httpx.ConnectTimeout("Connection timeout"))

        fetcher = GtfsRtFetcher(url=url, timeout=0.1)

        with pytest.raises(FetcherError) as exc_info:
            await fetcher.fetch()

        assert "Timeout" in str(exc_info.value)


@pytest.mark.asyncio
async def test_retry_on_failure_then_success():
    """Test verifica que reintenta 2 veces antes de conseguir éxito."""
    url = "https://gtfsrt.renfe.com/trip_updates_LD.json"
    call_count = 0

    def failing_then_success(_request):
        nonlocal call_count
        call_count += 1
        if call_count < 3:  # Falla las 2 primeras veces
            raise httpx.ConnectTimeout("Connection timeout")
        return httpx.Response(200, json={"header": {"gtfs_realtime_version": "2.0"}, "entity": []})

    with respx.mock:
        respx.get(url).mock(side_effect=failing_then_success)

        fetcher = GtfsRtFetcher(url=url, max_retries=3)
        result = await fetcher.fetch()

        assert call_count == 3  # 2 fallos + 1 éxito
        assert result.data["header"]["gtfs_realtime_version"] == "2.0"
