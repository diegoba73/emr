"""Seed laboratorios de derivación LAC/IACA y tipos de examen micro para pedido."""
from django.core.management.base import BaseCommand

from laboratorio.derivacion_service import MICRO_PEDIDO_CODIGOS, asegurar_labs_derivacion
from laboratorio.models import TipoExamen, TipoMuestra


MICRO_NOMBRES = {
    "UROCULTIVO": "Urocultivo",
    "HEMOCULTIVO": "Hemocultivo",
    "COPROCULTIVO": "Coprocultivo",
    "CULTIVO_HERIDA": "Cultivo de herida",
    "CULTIVO_RUTINA": "Cultivo de rutina",
    "HISOPADO": "Hisopado / cultivo de secreción",
    "PUNCION": "Cultivo de punción / líquido",
}


class Command(BaseCommand):
    help = "Crea LAC/IACA y tipos de examen de microbiología para el pedido."

    def handle(self, *args, **options):
        lac, iaca = asegurar_labs_derivacion()
        self.stdout.write(self.style.SUCCESS(f"Labs OK: {lac.codigo}, {iaca.codigo}"))

        muestra = (
            TipoMuestra.objects.filter(codigo__iexact="SANGRE").first()
            or TipoMuestra.objects.filter(activo=True).first()
        )
        if not muestra:
            self.stdout.write(self.style.WARNING("Sin TipoMuestra; skip micro tipos."))
            return

        creados = 0
        for codigo in MICRO_PEDIDO_CODIGOS:
            _, created = TipoExamen.objects.get_or_create(
                codigo=codigo,
                defaults={
                    "nombre": MICRO_NOMBRES.get(codigo, codigo),
                    "abreviatura": codigo[:20],
                    "tipo_muestra_requerida": muestra,
                    "tipo_resultado": "TEXTO",
                    "activo": True,
                    "requiere_muestra": True,
                },
            )
            if created:
                creados += 1
        self.stdout.write(self.style.SUCCESS(f"Tipos micro: {creados} nuevos"))
