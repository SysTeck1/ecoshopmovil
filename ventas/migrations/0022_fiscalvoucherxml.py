from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ventas", "0021_fiscalvoucher_dgii_enviado_at_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="FiscalVoucherXML",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("nombre", models.CharField(max_length=160)),
                ("archivo", models.FileField(upload_to="dgii/xml/")),
                (
                    "estado_conexion",
                    models.CharField(
                        choices=[
                            ("sin_conexion", "Sin conexión"),
                            ("buscando", "Buscando conexión"),
                            ("conectado", "Conectado"),
                        ],
                        default="sin_conexion",
                        max_length=20,
                    ),
                ),
                ("ultimo_intento", models.DateTimeField(blank=True, null=True)),
                ("mensaje", models.CharField(blank=True, max_length=255)),
                (
                    "configuracion",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.CASCADE,
                        related_name="xml_templates",
                        to="ventas.fiscalvoucherconfig",
                    ),
                ),
            ],
            options={
                "verbose_name": "XML DGII",
                "verbose_name_plural": "XML DGII",
                "ordering": ("-created_at",),
            },
        ),
    ]
