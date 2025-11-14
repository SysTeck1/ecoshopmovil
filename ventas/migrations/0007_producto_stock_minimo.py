from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ventas", "0006_productimage"),
    ]

    operations = [
        migrations.AddField(
            model_name="producto",
            name="stock_minimo",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
