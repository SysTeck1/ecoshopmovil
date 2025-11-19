from __future__ import annotations

from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="siteconfiguration",
            name="global_tax_enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="siteconfiguration",
            name="global_tax_rate",
            field=models.DecimalField(
                default=Decimal("18.00"),
                decimal_places=2,
                max_digits=5,
            ),
        ),
    ]
