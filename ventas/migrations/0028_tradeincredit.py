from django.db import migrations, models
import django.db.models.deletion
from django.core.validators import MinValueValidator


class Migration(migrations.Migration):

    dependencies = [
        ("ventas", "0027_add_cuotas_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="TradeInCredit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("codigo", models.CharField(editable=False, max_length=20, unique=True)),
                ("nombre_cliente", models.CharField(max_length=150)),
                ("producto_nombre", models.CharField(max_length=150)),
                ("descripcion", models.TextField(blank=True)),
                ("monto_credito", models.DecimalField(decimal_places=2, max_digits=12, validators=[MinValueValidator(0)])),
                (
                    "estado",
                    models.CharField(
                        choices=[
                            ("pendiente", "Pendiente"),
                            ("usado", "Usado"),
                            ("cancelado", "Cancelado"),
                        ],
                        default="pendiente",
                        max_length=20,
                    ),
                ),
                ("usado_en", models.DateTimeField(blank=True, null=True)),
                (
                    "cliente",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="trade_in_creditos",
                        to="ventas.cliente",
                    ),
                ),
                (
                    "venta_aplicada",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="trade_in_creditos",
                        to="ventas.venta",
                    ),
                ),
            ],
            options={
                "verbose_name": "Crédito por intercambio",
                "verbose_name_plural": "Créditos por intercambio",
                "ordering": ("-created_at",),
            },
        ),
    ]
