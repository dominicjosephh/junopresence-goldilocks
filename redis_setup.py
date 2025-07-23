import os
import time
import hashlib
import pickle

# Optional dependencies - gracefully handle missing modules
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

redis_client = None
PERFORMANCE_MONITORING_ENABLED = True

def init_redis():
    global redis_client
    try:
        import redis
        redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=False)
        redis_client.ping()
        print("🟢 Redis connected!")
        return True
    except:
        print("🟡 Redis unavailable - using local cache")
        return False

class SmartCacheManager:
    def __init__(self):
        self.local_cache = {}
        self.stats = {'hits': 0, 'misses': 0}
    
    def get(self, key_components, cache_type="default"):
        key = hashlib.md5(str(key_components).encode()).hexdigest()
        if redis_client:
            try:
                data = redis_client.get(f"{cache_type}:{key}")
                if data:
                    self.stats['hits'] += 1
                    return pickle.loads(data)
            except: pass
        self.stats['misses'] += 1
        return None
    
    def set(self, key_components, data, cache_type="default", ttl=3600):
        key = hashlib.md5(str(key_components).encode()).hexdigest()
        if redis_client:
            try:
                redis_client.setex(f"{cache_type}:{key}", ttl, pickle.dumps(data))
                return True
            except: pass
        return False
    
    def get_stats(self):
        total = self.stats['hits'] + self.stats['misses']
        return {
            'hit_rate': round(self.stats['hits'] / total * 100, 1) if total > 0 else 0,
            'redis_available': redis_client is not None,
            'total_hits': self.stats['hits'],
            'total_misses': self.stats['misses']
        }

class PerformanceMonitor:
    def __init__(self):
        self.metrics = {'response_times': [], 'active_requests': 0}
    
    def start_request(self):
        self.metrics['active_requests'] += 1
        return time.time()
    
    def end_request(self, start_time):
        self.metrics['response_times'].append(time.time() - start_time)
        self.metrics['active_requests'] = max(0, self.metrics['active_requests'] - 1)
        if len(self.metrics['response_times']) > 50:
            self.metrics['response_times'] = self.metrics['response_times'][-50:]
    
    def record_system_metrics(self): pass
    
    def get_performance_report(self):
        if not self.metrics['response_times']:
            return {'message': 'No data yet', 'active_requests': 0}
        avg = sum(self.metrics['response_times']) / len(self.metrics['response_times'])
        return {
            'response_times': {'average': round(avg, 3)},
            'active_requests': self.metrics['active_requests']
        }

cache_manager = SmartCacheManager()
performance_monitor = PerformanceMonitor()
print("🚀 Basic caching system ready!")
