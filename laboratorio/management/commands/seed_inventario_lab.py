"""Seed inventario demo: tubos del catálogo + medios activos."""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from laboratorio.models_catalog import TipoContenedor
from laboratorio.models_inventario import InsumoLab, LoteInsumo
from laboratorio.models_microbiologia import MedioCultivo


class Command(BaseCommand):
    help = "Crea insumos/lotes iniciales para tubos y medios de cultivo."

    def handle(self, *args, **options):
        venc = timezone.localdate() + timedelta(days=180)
        created = 0
        for tubo in TipoContenedor.objects.filter(activo=True):
            codigo = f"TUBO-{tubo.codigo}"
            insumo, was = InsumoLab.objects.get_or_create(
                codigo=codigo,
                defaults={
                    "nombre": f"Tubo {tubo.nombre}",
                    "tipo": InsumoLab.Tipo.TUBO,
                    "tipo_contenedor": tubo,
                    "unidad": "tubo",
                    "stock_min": 20,
                    "activo": True,
                },
            )
            if was:
                created += 1
            LoteInsumo.objects.get_or_create(
                insumo=insumo,
                codigo_lote="SEED-001",
                defaults={
                    "cantidad": 200,
                    "fecha_vencimiento": venc,
                    "ubicacion": "Almacén LIMS",
                    "activo": True,
                },
            )

        for medio in MedioCultivo.objects.filter(activo=True)[:5]:
            codigo = f"MEDIO-{medio.id}"
            insumo, was = InsumoLab.objects.get_or_create(
                codigo=codigo,
                defaults={
                    "nombre": getattr(medio, "nombre", None) or f"Medio {medio.id}",
                    "tipo": InsumoLab.Tipo.MEDIO,
                    "medio_cultivo": medio,
                    "unidad": "placa",
                    "stock_min": 10,
                    "activo": True,
                },
            )
            if was:
                created += 1
            LoteInsumo.objects.get_or_create(
                insumo=insumo,
                codigo_lote="SEED-001",
                defaults={
                    "cantidad": 50,
                    "fecha_vencimiento": venc,
                    "ubicacion": "Micro",
                    "activo": True,
                },
            )

        self.stdout.write(self.style.SUCCESS(f"Inventario seed OK (insumos nuevos={created})"))
