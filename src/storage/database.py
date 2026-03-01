"""Conexión a base de datos."""

import os
from contextlib import asynccontextmanager
from typing import Any

import asyncpg


class Database:
    """Gestor de conexión a PostgreSQL."""

    def __init__(self, database_url: str | None = None):
        self.database_url = database_url or os.environ.get("DATABASE_URL", "")
        self._pool: asyncpg.Pool | None = None

    async def conectar(self) -> None:
        """Crea el pool de conexiones."""
        self._pool = await asyncpg.create_pool(self.database_url)

    async def desconectar(self) -> None:
        """Cierra el pool de conexiones."""
        if self._pool:
            await self._pool.close()

    @asynccontextmanager
    async def conexion(self):
        """Context manager para obtener conexión."""
        async with self._pool.acquire() as conn:
            yield conn

    async def ejecutar(self, query: str, *args: Any) -> str:
        """Ejecuta una query sin retorno."""
        async with self.conexion() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args: Any) -> list[asyncpg.Record]:
        """Ejecuta una query con retorno."""
        async with self.conexion() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args: Any) -> asyncpg.Record | None:
        """Ejecuta una query con retorno de una fila."""
        async with self.conexion() as conn:
            return await conn.fetchrow(query, *args)

    async def executemany(self, query: str, *args: Any) -> None:
        """Ejecuta una query múltiples veces."""
        async with self.conexion() as conn:
            await conn.executemany(query, *args)
