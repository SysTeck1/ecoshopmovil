from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ventas", "0029_cashsession_total_trade_in_venta_descuento_total_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="impuesto",
            name="activo",
            field=models.BooleanField(default=True),
        ),
    ]
