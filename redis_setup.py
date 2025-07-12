import os
import time
import redis
import pickle
import hashlib
import psutil
from typing import Any, Optional

# Redis Configuration & Environment
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)
EMOTION_ANALYSIS_ENABLED = os.getenv('EMOTION_ANALYSIS_ENABLED', 'true').lower() == 'true'
PERFORMANCE_MONITORING_ENABLED = os.getenv('PERFORMANCE_MONITORING_ENABLED', 'true').lower() == 'true'

# Cache TTL settings (in seconds)
CACHE_TTL = {
    'ai_responses': 3600,
    'music_data': 7200,
    'emotion_analysis': 300,
    'user_context': 1800,
    'spotify_tokens': 3000
}

redis_pool = None
redis_client = None

def init_redis():
    global redis_pool, redis_client
    try:
        redis_pool = redis.ConnectionPool(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD if REDIS_PASSWORD else None,
            decode_responses=False,
            max_connections=20,
            retry_on_timeout=True,
            health_check_interval=30
        )
        redis_client = redis.Redis(connection_pool=redis_pool)
        redis_client.ping()
        print("🟢 Redis connection established successfully")
        return True
    except redis.ConnectionError:
        print("🟡 Redis not available - continuing without caching")
        redis_client = None
        return False
    except Exception as e:
        print(f"🟡 Redis setup warning: {e}")
        redis_client = None
        return False

class SmartCacheManager:
    def __init__(self):
        self.local_cache = {}
        self.cache_stats = {'hits': 0, 'misses': 0, 'errors': 0, 'redis_available': False}

    def _generate_cache_key(self, key_components: list, prefix: str = "") -> str:
        key_string = "|".join(str(component) for component in key_components)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        return f"{prefix}:{key_hash}" if prefix else key_hash

    def _serialize_data(self, data: Any) -> bytes:
        try:
            return pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception as e:
            print(f"🔴 Serialization error: {e}")
            return None

    def _deserialize_data(self, data: bytes) -> Any:
        try:
            return pickle.loads(data)
        except Exception as e:
            print(f"🔴 Deserialization error: {e}")
            return None

    def get(self, key_components: list, cache_type: str = "default") -> Optional[Any]:
        cache_key = self._generate_cache_key(key_components, cache_type)
        # Try Redis first
        if redis_client:
            try:
                cached_data = redis_client.get(cache_key)
                if cached_data:
                    deserialized = self._deserialize_data(cached_data)
                    if deserialized is not None:
                        self.cache_stats['hits'] += 1
                        print(f"🟢 Cache hit (Redis): {cache_type}")
                        return deserialized
            except Exception as e:
                print(f"🟡 Redis get error: {e}")
                self.cache_stats['errors'] += 1
        # Try local cache fallback
        if cache_key in self.local_cache:
            cache_entry = self.local_cache[cache_key]
            if time.time() - cache_entry['timestamp'] < cache_entry['ttl']:
                self.cache_stats['hits'] += 1
                print(f"🟢 Cache hit (Local): {cache_type}")
                return cache_entry['data']
            else:
                del self.local_cache[cache_key]
        self.cache_stats['misses'] += 1
        return None

    def set(self, key_components: list, data: Any, cache_type: str = "default", ttl: Optional[int] = None) -> bool:
        cache_key = self._generate_cache_key(key_components, cache_type)
        ttl = ttl or CACHE_TTL.get(cache_type, 3600)
        serialized_data = self._serialize_data(data)
        if not serialized_data:
            return False
        if redis_client:
            try:
                redis_client.setex(cache_key, ttl, serialized_data)
                print(f"🟢 Data cached (Redis): {cache_type} for {ttl}s")
                return True
            except Exception as e:
                print(f"🟡 Redis set error: {e}")
                self.cache_stats['errors'] += 1
        self.local_cache[cache_key] = {
            'data': data,
            'timestamp': time.time(),
            'ttl': ttl
        }
        if len(self.local_cache) > 100:
            oldest_keys = sorted(self.local_cache.keys(), key=lambda k: self.local_cache[k]['timestamp'])[:20]
            for key in oldest_keys:
                del self.local_cache[key]
        print(f"🟢 Data cached (Local): {cache_type} for {ttl}s")
        return True

    def delete(self, key_components: list, cache_type: str = "default") -> bool:
        cache_key = self._generate_cache_key(key_components, cache_type)
        deleted = False
        if redis_client:
            try:
                redis_client.delete(cache_key)
                deleted = True
            except Exception as e:
                print(f"🟡 Redis delete error: {e}")
        if cache_key in self.local_cache:
            del self.local_cache[cache_key]
            deleted = True
        if deleted:
            print(f"🟢 Cache invalidated: {cache_type}")
        return deleted

    def get_stats(self) -> dict:
        total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
        hit_rate = (self.cache_stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        redis_info = {}
        if redis_client:
            try:
                info = redis_client.info()
                redis_info = {
                    'connected_clients': info.get('connected_clients', 0),
                    'used_memory_human': info.get('used_memory_human', 'Unknown'),
                    'keyspace_hits': info.get('keyspace_hits', 0),
                    'keyspace_misses': info.get('keyspace_misses', 0)
                }
                self.cache_stats['redis_available'] = True
            except:
                self.cache_stats['redis_available'] = False
        return {
            'hit_rate': round(hit_rate, 2),
            'total_hits': self.cache_stats['hits'],
            'total_misses': self.cache_stats['misses'],
            'total_errors': self.cache_stats['errors'],
            'redis_available': self.cache_stats['redis_available'],
            'local_cache_size': len(self.local_cache),
            'redis_info': redis_info
        }

    def clear_all(self) -> bool:
        cleared = False
        if redis_client:
            try:
                our_prefixes = ['ai_responses:*', 'music_data:*', 'emotion_analysis:*', 'user_context:*', 'spotify_tokens:*']
                for prefix in our_prefixes:
                    keys = redis_client.keys(prefix)
                    if keys:
                        redis_client.delete(*keys)
                cleared = True
            except Exception as e:
                print(f"🟡 Redis clear error: {e}")
        self.local_cache.clear()
        cleared = True
        if cleared:
            print("🟢 All cache data cleared")
        return cleared

cache_manager = SmartCacheManager()

class PerformanceMonitor:
    def __init__(self):
        self.metrics = {
            'response_times': [],
            'memory_usage': [],
            'cpu_usage': [],
            'active_requests': 0
        }

    def start_request(self):
        self.metrics['active_requests'] += 1
        return time.time()

    def end_request(self, start_time: float):
        response_time = time.time() - start_time
        self.metrics['response_times'].append(response_time)
        self.metrics['active_requests'] = max(0, self.metrics['active_requests'] - 1)
        if len(self.metrics['response_times']) > 100:
            self.metrics['response_times'] = self.metrics['response_times'][-100:]

    def record_system_metrics(self):
        if PERFORMANCE_MONITORING_ENABLED:
            try:
                memory_info = psutil.virtual_memory()
                self.metrics['memory_usage'].append(memory_info.percent)
                cpu_percent = psutil.cpu_percent(interval=None)
                self.metrics['cpu_usage'].append(cpu_percent)
                if len(self.metrics['memory_usage']) > 100:
                    self.metrics['memory_usage'] = self.metrics['memory_usage'][-100:]
                if len(self.metrics['cpu_usage']) > 100:
                    self.metrics['cpu_usage'] = self.metrics['cpu_usage'][-100:]
            except Exception as e:
                print(f"🟡 Performance monitoring error: {e}")

    def get_performance_report(self) -> dict:
        if not self.metrics['response_times']:
            return {"message": "No performance data available yet"}
        avg_response_time = sum(self.metrics['response_times']) / len(self.metrics['response_times'])
        max_response_time = max(self.metrics['response_times'])
        min_response_time = min(self.metrics['response_times'])
        report = {
            'response_times': {
                'average': round(avg_response_time, 3),
                'max': round(max_response_time, 3),
                'min': round(min_response_time, 3),
                'recent_count': len(self.metrics['response_times'])
            },
            'active_requests': self.metrics['active_requests'],
            'cache_stats': cache_manager.get_stats()
        }
        if self.metrics['memory_usage']:
            report['system'] = {
                'memory_usage_avg': round(sum(self.metrics['memory_usage']) / len(self.metrics['memory_usage']), 2),
                'cpu_usage_avg': round(sum(self.metrics['cpu_usage']) / len(self.metrics['cpu_usage']), 2),
                'memory_usage_current': self.metrics['memory_usage'][-1] if self.metrics['memory_usage'] else 0,
                'cpu_usage_current': self.metrics['cpu_usage'][-1] if self.metrics['cpu_usage'] else 0
            }
        return report

performance_monitor = PerformanceMonitor()
