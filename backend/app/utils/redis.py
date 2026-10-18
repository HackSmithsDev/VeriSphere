import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import REDIS_URL


logger = logging.getLogger(__name__)


async def get_or_load_json(
    key: str,
    ttl_seconds: int,
    loader: Callable[[], Awaitable[dict[str, Any]]],
) -> dict[str, Any]:
    client = Redis.from_url(
        REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=1,
        socket_timeout=1,
    )
    try:
        try:
            cached = await client.get(key)
        except RedisError as error:
            logger.warning("Redis cache read failed: %s.", type(error).__name__)
            cached = None
        if cached is not None:
            try:
                decoded = json.loads(cached)
            except ValueError:
                logger.warning("Redis cache entry %s contains invalid JSON.", key)
                try:
                    await client.delete(key)
                except RedisError as error:
                    logger.warning(
                        "Could not remove corrupt Redis cache entry: %s.",
                        type(error).__name__,
                    )
            else:
                if isinstance(decoded, dict):
                    return decoded
                logger.warning("Redis cache entry %s is not an object.", key)

        result = await loader()
        try:
            await client.set(key, json.dumps(result), ex=ttl_seconds)
        except RedisError as error:
            logger.warning("Redis cache write failed: %s.", type(error).__name__)
        return result
    finally:
        try:
            await client.aclose()
        except RedisError as error:
            logger.warning("Redis connection cleanup failed: %s.", type(error).__name__)
