from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.DashboardHomeView.as_view(), name="inicio"),
    path("ventas/", views.VentasView.as_view(), name="ventas"),
    path(
        "ventas/historial/",
        views.ventas_historial_api,
        name="ventas_historial_api",
    ),
    path(
        "reportes/ventas-totales/",
        views.report_total_sales_api,
        name="report_total_sales_api",
    ),
    path(
        "reportes/ganancias/",
        views.report_profit_api,
        name="report_profit_api",
    ),
    path(
        "reportes/costo-inventario/",
        views.report_inventory_cost_api,
        name="report_inventory_cost_api",
    ),
    path(
        "reportes/costo-ventas/",
        views.report_sales_cost_api,
        name="report_sales_cost_api",
    ),
    path(
        "reportes/ventas-periodo/",
        views.report_sales_period_api,
        name="report_sales_period_api",
    ),
    path(
        "reportes/ganancias-periodo/",
        views.report_profit_period_api,
        name="report_profit_period_api",
    ),
    path(
        "reportes/categorias-analitico/",
        views.report_category_analysis_api,
        name="report_category_analysis_api",
    ),
    path(
        "reportes/ventas-producto/",
        views.report_product_sales_api,
        name="report_product_sales_api",
    ),
    path(
        "reportes/cuotas/",
        views.report_credit_installments_api,
        name="report_credit_installments_api",
    ),
    path(
        "caja/estado/",
        views.cash_session_status_api,
        name="cash_session_status_api",
    ),
    path(
        "caja/abrir/",
        views.cash_session_open_api,
        name="cash_session_open_api",
    ),
    path(
        "caja/cerrar/",
        views.cash_session_close_api,
        name="cash_session_close_api",
    ),
    path(
        "reportes/caja/",
        views.cash_session_report_api,
        name="cash_session_report_api",
    ),
    path(
        "ventas/registrar/",
        views.registrar_venta_api,
        name="registrar_venta_api",
    ),
    path(
        "fiscal/configuracion/",
        views.fiscal_voucher_config_api,
        name="fiscal_voucher_config_api",
    ),
    path(
        "fiscal/xml/",
        views.fiscal_voucher_xml_api,
        name="fiscal_voucher_xml_api",
    ),
    path(
        "fiscal/xml/<int:xml_id>/check/",
        views.fiscal_voucher_xml_check_api,
        name="fiscal_voucher_xml_check_api",
    ),
    path("cotizaciones/", views.CotizacionesView.as_view(), name="cotizaciones"),
    path("inventario/", views.InventarioView.as_view(), name="inventario"),
    path("inventario/<int:producto_id>/", views.ProductoDetailView.as_view(), name="producto_detail"),
    path(
        "inventario/marcas/<int:brand_id>/toggle/",
        views.toggle_brand_status_api,
        name="toggle_brand_status_api",
    ),
    path(
        "inventario/marcas/crear/",
        views.create_brand_api,
        name="create_brand_api",
    ),
    path(
        "inventario/modelos/<int:model_id>/toggle/",
        views.toggle_model_status_api,
        name="toggle_model_status_api",
    ),
    path(
        "inventario/modelos/crear/",
        views.create_model_api,
        name="create_model_api",
    ),
    path("clientes/", views.ClientesView.as_view(), name="clientes"),
    path("proveedor/", views.ProveedorView.as_view(), name="proveedor"),
    path("compras/", views.ComprasView.as_view(), name="compras"),
    path("cobros/", views.CobrosView.as_view(), name="cobros"),
    path("cobros/abonos/registrar/", views.registrar_abono_credito_api, name="registrar_abono_credito_api"),
    path("cobros/pagos-tardios/registrar/", views.registrar_pago_tardio_credito_api, name="registrar_pago_tardio_credito_api"),
    path("otros/", views.OtrosView.as_view(), name="otros"),
    path("otros/reportes/", views.ReportesView.as_view(), name="reportes"),
    path("otros/gastos/", views.GastosView.as_view(), name="gastos"),
    path("otros/usuarios/", views.UsuariosView.as_view(), name="usuarios"),
    path("otros/configuracion/", views.ConfiguracionView.as_view(), name="configuracion"),
]
