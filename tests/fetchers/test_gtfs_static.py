"""Tests para GtfsStaticFetcher."""

import zipfile
from io import BytesIO

import httpx
import pytest
import respx

from src.fetchers import FetcherError, GtfsStaticFetcher


def _create_fake_zip() -> bytes:
    """Crea un ZIP válido con archivos GTFS de ejemplo."""
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("trips.txt", "trip_id,service_id\n1,1\n")
        zf.writestr("stop_times.txt", "trip_id,stop_id,arrival_time\n1,1,08:00:00\n")
        zf.writestr("stops.txt", "stop_id,stop_name\n1,Madrid\n")
        zf.writestr("routes.txt", "route_id,route_short_name\n1,AVE\n")
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_fetch_gtfs_static_success():
    """Test de fetch exitoso de GTFS estático."""
    url = "https://ssl.renfe.com/gtransit/Fichero_AV_LD/google_transit.zip"
    fake_zip = _create_fake_zip()

    with respx.mock:
        respx.get(url).mock(return_value=httpx.Response(200, content=fake_zip))

        fetcher = GtfsStaticFetcher(url=url)
        result = await fetcher.fetch()

        assert result.data == fake_zip
        assert result.status_code == 200
        assert isinstance(result.data, bytes)

        # Verificar que es un ZIP real
        with zipfile.ZipFile(BytesIO(result.data)) as zf:
            assert "trips.txt" in zf.namelist()


@pytest.mark.asyncio
async def test_fetch_gtfs_static_invalid_zip():
    """Test de respuesta que no es un ZIP válido."""
    url = "https://ssl.renfe.com/gtransit/Fichero_AV_LD/google_transit.zip"

    with respx.mock:
        respx.get(url).mock(return_value=httpx.Response(200, content=b"not a zip"))

        fetcher = GtfsStaticFetcher(url=url)

        with pytest.raises(FetcherError) as exc_info:
            await fetcher.fetch()

        assert "no es un ZIP válido" in str(exc_info.value)


@pytest.mark.asyncio
async def test_fetch_gtfs_static_no_txt_files():
    """Test de ZIP sin archivos .txt (no es GTFS válido)."""
    url = "https://ssl.renfe.com/gtransit/Fichero_AV_LD/google_transit.zip"

    # ZIP válido pero sin .txt
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("readme.md", "Este es un ZIP válido pero no GTFS")

    with respx.mock:
        respx.get(url).mock(return_value=httpx.Response(200, content=buffer.getvalue()))

        fetcher = GtfsStaticFetcher(url=url)

        with pytest.raises(FetcherError) as exc_info:
            await fetcher.fetch()

        assert "no contiene archivos GTFS" in str(exc_info.value)


@pytest.mark.asyncio
async def test_fetch_gtfs_static_not_found():
    """Test de 404 al obtener GTFS estático."""
    url = "https://ssl.renfe.com/gtransit/Fichero_AV_LD/google_transit.zip"

    with respx.mock:
        respx.get(url).mock(return_value=httpx.Response(404))

        fetcher = GtfsStaticFetcher(url=url)

        with pytest.raises(FetcherError) as exc_info:
            await fetcher.fetch()

        assert "404" in str(exc_info.value)


@pytest.mark.asyncio
async def test_custom_timeout():
    """Test de timeout personalizado para GTFS estático."""
    url = "https://ssl.renfe.com/gtransit/Fichero_AV_LD/google_transit.zip"

    with respx.mock:
        respx.get(url).mock(side_effect=httpx.ConnectTimeout("Connection timeout"))

        fetcher = GtfsStaticFetcher(url=url, timeout=0.1)

        with pytest.raises(FetcherError):
            await fetcher.fetch()
