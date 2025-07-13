import redis
import os

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.from_url(redis_url)

def store_memory(key: str, value: str):
    redis_client.set(key, value)

def retrieve_memory(key: str) -> str:
    return redis_client.get(key)
