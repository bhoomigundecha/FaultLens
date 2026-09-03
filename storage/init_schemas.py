"""
Schema initialiser — run once before starting services.
Creates all tables, hypertables, indexes, and ES indices.
"""

from __future__ import annotations

import asyncio
import logging

import asyncpg
from elasticsearch import AsyncElasticsearch

from config.settings import get_settings
import storage.timescale as ts_store
import storage.elasticsearch_client as es_store
import storage.neo4j_client as neo4j_store
import storage.postgres_client as pg_store

logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")
logger = logging.getLogger(__name__)
settings = get_settings()


async def init_all() -> None:
    logger.info("Initialising TimescaleDB …")
    ts_pool = await ts_store.get_pool()
    await ts_store.init_schema(ts_pool)

    logger.info("Initialising Elasticsearch …")
    await es_store.init_indices()
    await es_store.close_client()

    logger.info("Initialising Neo4j …")
    neo4j_store.init_schema()
    neo4j_store.close_driver()

    logger.info("Initialising PostgreSQL …")
    pg_pool = await pg_store.get_pool()
    await pg_store.init_schema(pg_pool)

    await ts_store.close_pool()
    await pg_store.close_pool()

    logger.info("✅  All schemas initialised successfully.")


if __name__ == "__main__":
    asyncio.run(init_all())
