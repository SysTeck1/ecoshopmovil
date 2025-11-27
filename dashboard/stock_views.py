from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django.http import JsonResponse
from django.db import transaction
from .models import SiteConfiguration
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
@require_GET
def obtener_stock_config(request):
    """
    Obtener configuración de stock mínimo actual
    """
    try:
        site_config = SiteConfiguration.get_solo()
        
        config_data = {
            'stock_minimo_default': site_config.stock_minimo_default,
            'bloquear_venta_sin_stock': site_config.bloquear_venta_sin_stock,
            'alerta_stock_bajo_porcentaje': site_config.alerta_stock_bajo_porcentaje,
        }
        return JsonResponse({'success': True, 'config': config_data})
    except Exception as e:
        logger.error(f"Error al obtener configuración de stock: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@csrf_exempt
@require_POST
def guardar_stock_config(request):
    """
    Guardar configuración de stock mínimo desde el frontend
    """
    try:
        import json
        data = json.loads(request.body)
        
        site_config = SiteConfiguration.get_solo()
        
        # Actualizar campos de configuración
        site_config.stock_minimo_default = int(data.get('stock_minimo_default', site_config.stock_minimo_default))
        site_config.bloquear_venta_sin_stock = data.get('bloquear_venta_sin_stock', site_config.bloquear_venta_sin_stock)
        site_config.alerta_stock_bajo_porcentaje = int(data.get('alerta_stock_bajo_porcentaje', site_config.alerta_stock_bajo_porcentaje))

        site_config.save()
        
        return JsonResponse({'success': True})
    except Exception as e:
        logger.error(f"Error al guardar configuración de stock: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
