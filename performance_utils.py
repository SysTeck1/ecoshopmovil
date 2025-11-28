"""
Utilidades de rendimiento para compresión y optimización
"""
import gzip
import json
import zlib
from django.http import JsonResponse, HttpResponse
from django.core.serializers.json import DjangoJSONEncoder
from typing import Dict, Any, Union
import time
import logging

# Intentar importar psutil, pero manejar si no está disponible
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

logger = logging.getLogger(__name__)

class CompressedJsonResponse(JsonResponse):
    """Respuesta JSON con compresión gzip para reducir tamaño de transferencia"""
    
    def __init__(self, data: Dict[str, Any], compress_threshold: int = 1024, **kwargs):
        # Convertir datos a JSON
        json_data = json.dumps(data, cls=DjangoJSONEncoder, ensure_ascii=False)
        
        # Determinar si necesitamos compresión
        if len(json_data.encode('utf-8')) > compress_threshold:
            compressed_data = gzip.compress(json_data.encode('utf-8'))
            
            # Llamar al constructor de JsonResponse con datos comprimidos
            super().__init__({}, **kwargs)
            
            # Reemplazar el contenido con datos comprimidos
            self.content = compressed_data
            self['Content-Encoding'] = 'gzip'
            self['Content-Length'] = len(compressed_data)
            self['X-Compression-Ratio'] = f"{len(json_data) / len(compressed_data):.2f}x"
        else:
            # Usar JsonResponse normal
            super().__init__(data, **kwargs)
        
        # Agregar headers de rendimiento a ambos casos
        self['X-Response-Time'] = f"{time.time():.3f}"
        self['Cache-Control'] = 'public, max-age=300'

class PerformanceMiddleware:
    """Middleware para medir y optimizar rendimiento"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        start_time = time.time()
        
        response = self.get_response(request)
        
        # Calcular tiempo de respuesta
        response_time = time.time() - start_time
        
        # Agregar headers de rendimiento
        response['X-Response-Time'] = f"{response_time:.3f}s"
        response['X-Server-Time'] = f"{time.time():.3f}"
        
        # Log de respuestas lentas
        if response_time > 2.0:
            logger.warning(f"Respuesta lenta: {request.path} - {response_time:.3f}s")
        
        return response

def optimize_query_response(data: Dict[str, Any], request_path: str) -> Dict[str, Any]:
    """Optimizar respuesta según el tipo de petición"""
    
    # Eliminar campos innecesarios para respuestas grandes
    if 'units' in data and len(data['units']) > 100:
        # Para listas grandes de unidades, eliminar campos detallados
        optimized_units = []
        for unit in data['units']:
            optimized_unit = {
                'key': unit.get('key'),
                'producto_id': unit.get('producto_id'),
                'unidad_index': unit.get('unidad_index'),
                'etiqueta': unit.get('etiqueta'),
                'precio': unit.get('precio'),
                'vendido': unit.get('vendido', False),
            }
            # Agregar campos importantes solo si no están vendidos
            if not unit.get('vendido', False):
                optimized_unit.update({
                    'impuesto_porcentaje': unit.get('impuesto_porcentaje', '0'),
                    'impuesto_activo': unit.get('impuesto_activo', False),
                    'imei': unit.get('imei', ''),
                    'color': unit.get('color', ''),
                })
            optimized_units.append(optimized_unit)
        
        data['units'] = optimized_units
        data['optimized'] = True
    
    # Para respuestas de filtros, limitar opciones
    if 'brands' in data and len(data['brands']) > 50:
        data['brands'] = data['brands'][:50]
        data['brands_truncated'] = True
    
    if 'models' in data and len(data['models']) > 100:
        data['models'] = data['models'][:100]
        data['models_truncated'] = True
    
    return data

def cache_response_key(request, params: Dict[str, Any] = None) -> str:
    """Generar clave única para cache basada en petición y parámetros"""
    import hashlib
    
    key_parts = [
        request.path,
        str(request.GET),
        str(params or {}),
    ]
    
    key_string = '|'.join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()

def get_cache_ttl(request_path: str) -> int:
    """Obtener TTL de cache según el tipo de petición"""
    
    if '/ventas/productos/unidades/' in request_path:
        return 600  # 10 minutos para unidades
    elif '/ventas/productos/pagina/' in request_path:
        return 300  # 5 minutos para páginas
    elif '/reportes/' in request_path:
        return 1800  # 30 minutos para reportes
    else:
        return 120  # 2 minutos por defecto

class SmartCache:
    """Cache inteligente con invalidación automática"""
    
    def __init__(self):
        self.cache = {}
        self.timestamps = {}
    
    def get(self, key: str) -> Any:
        """Obtener valor del cache"""
        if key in self.cache:
            timestamp = self.timestamps.get(key, 0)
            if time.time() - timestamp < 300:  # 5 minutos TTL
                return self.cache[key]
            else:
                # Expired, remove from cache
                self.delete(key)
        return None
    
    def set(self, key: str, value: Any, ttl: int = 300):
        """Guardar valor en cache"""
        self.cache[key] = value
        self.timestamps[key] = time.time()
    
    def delete(self, key: str):
        """Eliminar del cache"""
        self.cache.pop(key, None)
        self.timestamps.pop(key, None)
    
    def clear_pattern(self, pattern: str):
        """Eliminar claves que coincidan con patrón"""
        keys_to_delete = [key for key in self.cache if pattern in key]
        for key in keys_to_delete:
            self.delete(key)
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del cache"""
        return {
            'size': len(self.cache),
            'keys': list(self.cache.keys()),
            'memory_usage': len(str(self.cache))
        }

# Instancia global de cache inteligente
smart_cache = SmartCache()
