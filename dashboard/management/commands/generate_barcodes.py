from django.core.management.base import BaseCommand
from ventas.models import ProductoUnitDetail


class Command(BaseCommand):
    help = 'Genera códigos de barras para unidades existentes sin código'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Procesar todas las unidades sin código',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Límite de unidades a procesar (default: 100)',
        )

    def handle(self, *args, **options):
        queryset = ProductoUnitDetail.objects.filter(codigo_barras='')
        total_count = queryset.count()
        
        if total_count == 0:
            self.stdout.write(
                self.style.SUCCESS('✅ Todas las unidades ya tienen código de barras')
            )
            return

        self.stdout.write(f'📊 Encontradas {total_count} unidades sin código de barras')
        
        if options['all']:
            units_to_process = queryset
            self.stdout.write('🔄 Procesando todas las unidades...')
        else:
            limit = options['limit']
            units_to_process = queryset[:limit]
            self.stdout.write(f'🔄 Procesando primeras {min(limit, total_count)} unidades...')

        processed = 0
        for unit in units_to_process:
            try:
                unit.save()  # Triggers automatic barcode generation
                processed += 1
                if processed % 10 == 0:
                    self.stdout.write(f'   Procesadas: {processed}')
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Error en unidad {unit.id}: {e}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'✅ Completado: {processed} códigos generados')
        )
        
        remaining = total_count - processed
        if remaining > 0:
            self.stdout.write(f'📋 Quedan {remaining} unidades pendientes')
