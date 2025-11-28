"""
Configuración de cache Redis para datos frecuentes
"""
import json
import pickle
from django.conf import settings
from django.core.cache import cache
from typing import Any, Optional, Dict
import hashlib

# Intentar importar redis, pero manejar si no está disponible
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

class RedisCacheManager:
    """Gestor de cache Redis para datos frecuentes"""
    
    def __init__(self):
        self.enabled = False
        
        if not REDIS_AVAILABLE:
            print("⚠️  Redis no instalado, usando cache de Django")
            return
            
        try:
            self.redis_client = redis.Redis(
                host='localhost',
                port=6379,
                db=0,
                decode_responses=False,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            # Test connection
            self.redis_client.ping()
            self.enabled = True
            print("✅ Redis cache conectado exitosamente")
        except (redis.ConnectionError, redis.TimeoutError, Exception):
            self.enabled = False
            print("⚠️  Redis no disponible, usando cache de Django")
    
    def get_cache_key(self, prefix: str, **kwargs) -> str:
        """Generar clave de cache única"""
        key_data = f"{prefix}:{json.dumps(kwargs, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get_product_options(self, page: int = 1, page_size: int = 20) -> Optional[Dict]:
        """Obtener opciones de productos cacheadas"""
        if self.enabled:
            cache_key = self.get_cache_key("product_options", page=page, page_size=page_size)
            try:
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    return pickle.loads(cached_data)
            except Exception as e:
                print(f"Error obteniendo cache de productos: {e}")
        else:
            # Usar cache de Django como fallback
            cache_key = f"product_options_{page}_{page_size}"
            return cache.get(cache_key)
        return None
    
    def set_product_options(self, page: int, page_size: int, data: Dict, ttl: int = 300):
        """Guardar opciones de productos en cache"""
        if self.enabled:
            cache_key = self.get_cache_key("product_options", page=page, page_size=page_size)
            try:
                self.redis_client.setex(cache_key, ttl, pickle.dumps(data))
            except Exception as e:
                print(f"Error guardando cache de productos: {e}")
        else:
            # Usar cache de Django como fallback
            cache_key = f"product_options_{page}_{page_size}"
            cache.set(cache_key, data, ttl)
    
    def get_product_units(self, product_id: int) -> Optional[Dict]:
        """Obtener unidades de producto cacheadas"""
        if self.enabled:
            cache_key = self.get_cache_key("product_units", product_id=product_id)
            try:
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    return pickle.loads(cached_data)
            except Exception as e:
                print(f"Error obteniendo cache de unidades: {e}")
        else:
            # Usar cache de Django como fallback
            cache_key = f"product_units_{product_id}"
            return cache.get(cache_key)
        return None
    
    def set_product_units(self, product_id: int, data: Dict, ttl: int = 600):
        """Guardar unidades de producto en cache"""
        if self.enabled:
            cache_key = self.get_cache_key("product_units", product_id=product_id)
            try:
                self.redis_client.setex(cache_key, ttl, pickle.dumps(data))
            except Exception as e:
                print(f"Error guardando cache de unidades: {e}")
        else:
            # Usar cache de Django como fallback
            cache_key = f"product_units_{product_id}"
            cache.set(cache_key, data, ttl)
    
    def get_filter_options(self) -> Optional[Dict]:
        """Obtener opciones de filtros cacheadas"""
        if self.enabled:
            cache_key = self.get_cache_key("filter_options")
            try:
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    return pickle.loads(cached_data)
            except Exception as e:
                print(f"Error obteniendo cache de filtros: {e}")
        else:
            # Usar cache de Django como fallback
            return cache.get("filter_options")
        return None
    
    def set_filter_options(self, data: Dict, ttl: int = 1800):
        """Guardar opciones de filtros en cache"""
        if self.enabled:
            cache_key = self.get_cache_key("filter_options")
            try:
                self.redis_client.setex(cache_key, ttl, pickle.dumps(data))
            except Exception as e:
                print(f"Error guardando cache de filtros: {e}")
        else:
            # Usar cache de Django como fallback
            cache.set("filter_options", data, ttl)
    
    def invalidate_product_cache(self, product_id: Optional[int] = None):
        """Invalidar cache de productos"""
        if self.enabled:
            try:
                if product_id:
                    # Invalidar cache de un producto específico
                    cache_key = self.get_cache_key("product_units", product_id=product_id)
                    self.redis_client.delete(cache_key)
                else:
                    # Invalidar todo el cache de productos
                    pattern = self.get_cache_key("product_options", page="*")
                    keys = self.redis_client.keys(pattern)
                    if keys:
                        self.redis_client.delete(*keys)
            except Exception as e:
                print(f"Error invalidando cache: {e}")
        else:
            # Usar cache de Django como fallback
            if product_id:
                cache.delete(f"product_units_{product_id}")
            else:
                cache.delete_many([key for key in cache.keys("product_options_*")])
    
    def get_cache_stats(self) -> Dict:
        """Obtener estadísticas del cache"""
        if self.enabled:
            try:
                info = self.redis_client.info()
                return {
                    "enabled": True,
                    "used_memory": info.get("used_memory_human", "N/A"),
                    "connected_clients": info.get("connected_clients", 0),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0),
                    "hit_rate": (
                        info.get("keyspace_hits", 0) / 
                        max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1)
                    ) * 100
                }
            except Exception as e:
                return {"enabled": False, "error": str(e)}
        else:
            return {"enabled": False, "fallback": "Django cache"}

# Instancia global del cache
cache_manager = RedisCacheManager()
