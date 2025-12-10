import os
from typing import Optional

import redis
from redis.exceptions import RedisError

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

def _make_key(agent: str, prompt: str) -> str:
    return f"{agent}:{prompt}"

def get_cached_response(agent: str, prompt: str) -> Optional[str]:
    key = _make_key(agent, prompt)
    try:
        return _client.get(key)
    except RedisError:
        return None

def set_cached_response(agent: str, prompt: str, response: str) -> None:
    key = _make_key(agent, prompt)
    try:
        _client.set(key, response)
    except RedisError:
        pass
