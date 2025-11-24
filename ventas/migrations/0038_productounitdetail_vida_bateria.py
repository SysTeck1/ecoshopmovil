from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ventas", "0037_productounitdetail_tax_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="productounitdetail",
            name="vida_bateria",
            field=models.CharField(
                blank=True,
                help_text="Descripción de la vida útil o estado de la batería",
                max_length=120,
            ),
        ),
    ]
