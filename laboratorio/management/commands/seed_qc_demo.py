"""Seed QC demo: CM260 + Standatrol S-E + Calibrador A Plus + curva PCR."""
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from laboratorio.models import TipoExamen, TipoMuestra
from laboratorio.models_qc import Calibracion, EquipoAnalizador, LoteControl, MaterialControl

# Química típica de autoanalizador (excluye VSG, EAB, orinas, etc.)
QUIMICA_CM260 = [
    "GLU",
    "UREA",
    "CREA",
    "AU",
    "CA",
    "MG",
    "P",
    "CA_ION",
    "PROT_T",
    "ALB",
    "AMIL",
    "LIP",
    "GGT",
    "LDH",
    "CPK",
    "CPK_MB",
    "HBA1C",
    "LACT",
    "PCR_US",
]

STANDATROL_PRODUCTO = "Standatrol S-E 2 Niveles"
STANDATROL_MARCA = "Wiener"
LOTE_DEMO = "STANDATROL-DEMO"
CALIBRADOR_A_PLUS = "Calibrador A Plus"

# Targets placeholder (reemplazar con inserto real)
TARGET_S1 = (Decimal("100.0000"), Decimal("5.0000"))
TARGET_S2 = (Decimal("200.0000"), Decimal("10.0000"))

CURVA_PCR_DEMO = [
    {"orden": 1, "concentracion": "0", "senal": "0.010", "unidad": "mg/L"},
    {"orden": 2, "concentracion": "5", "senal": "0.120", "unidad": "mg/L"},
    {"orden": 3, "concentracion": "20", "senal": "0.380", "unidad": "mg/L"},
    {"orden": 4, "concentracion": "80", "senal": "0.920", "unidad": "mg/L"},
    {"orden": 5, "concentracion": "160", "senal": "1.450", "unidad": "mg/L"},
]


class Command(BaseCommand):
    help = "Crea CM260, Standatrol S1/S2, Calibrador A Plus y curva PCR demo."

    def _ensure_examen_pcr(self) -> TipoExamen | None:
        existing = TipoExamen.objects.filter(codigo="PCR").first()
        if existing:
            return existing
        ref = TipoExamen.objects.filter(codigo="PCR_US").first()
        muestra_obj = ref.tipo_muestra_requerida if ref else None
        if not muestra_obj:
            muestra_obj = (
                TipoMuestra.objects.filter(codigo__iexact="SANGRE").first()
                or TipoMuestra.objects.first()
            )
        if not muestra_obj:
            return None
        return TipoExamen.objects.create(
            codigo="PCR",
            nombre="Proteína C reactiva",
            abreviatura="PCR",
            tipo_muestra_requerida=muestra_obj,
            tipo_contenedor=ref.tipo_contenedor if ref else None,
            seccion=ref.seccion if ref else None,
            tipo_resultado="NUMERICO",
            activo=True,
        )

    def handle(self, *args, **options):
        hoy = timezone.localdate()
        venc = hoy + timedelta(days=365)

        equipo, created_eq = EquipoAnalizador.objects.get_or_create(
            codigo="CM260",
            defaults={
                "nombre": "Autoanalizador CM260",
                "marca_modelo": "CM260",
                "activo": True,
            },
        )
        if not created_eq and not equipo.marca_modelo:
            equipo.marca_modelo = "CM260"
            equipo.save(update_fields=["marca_modelo", "updated_at"])

        # Migrar equipo demo viejo si existía solo ese
        EquipoAnalizador.objects.filter(codigo="ANALIZADOR-DEMO").update(activo=False)

        examenes = list(TipoExamen.objects.filter(codigo__in=QUIMICA_CM260, activo=True))
        if not examenes:
            fallback = (
                TipoExamen.objects.filter(codigo__icontains="GLU").first()
                or TipoExamen.objects.filter(activo=True).first()
            )
            if not fallback:
                self.stdout.write(self.style.WARNING("No hay TipoExamen; skip QC seed."))
                return
            examenes = [fallback]

        mats_creados = 0
        lotes_creados = 0
        for examen in examenes:
            for nivel, (media, de) in (
                (MaterialControl.Nivel.N1, TARGET_S1),
                (MaterialControl.Nivel.N2, TARGET_S2),
            ):
                material = MaterialControl.objects.filter(
                    tipo_examen=examen, nivel=nivel
                ).first()
                created = False
                if not material:
                    material = MaterialControl.objects.create(
                        tipo_examen=examen,
                        nivel=nivel,
                        nombre=f"Standatrol {examen.codigo} {nivel}",
                        marca=STANDATROL_MARCA,
                        producto=STANDATROL_PRODUCTO,
                        media_target=media,
                        de_target=de,
                        activo=True,
                    )
                    created = True
                if created:
                    mats_creados += 1
                else:
                    updates = []
                    if not material.marca:
                        material.marca = STANDATROL_MARCA
                        updates.append("marca")
                    if not material.producto:
                        material.producto = STANDATROL_PRODUCTO
                        updates.append("producto")
                    if updates:
                        material.save(update_fields=[*updates, "updated_at"])

                _, lot_created = LoteControl.objects.get_or_create(
                    material=material,
                    codigo_lote=LOTE_DEMO,
                    defaults={"vencimiento": venc, "activo": True},
                )
                if lot_created:
                    lotes_creados += 1

        cal_a_plus, _ = Calibracion.objects.get_or_create(
            equipo=equipo,
            calibrador_nombre=CALIBRADOR_A_PLUS,
            codigo_lote="CAL-APLUS-DEMO",
            fecha=hoy,
            defaults={
                "vigente_hasta": hoy + timedelta(days=30),
                "marca": STANDATROL_MARCA,
                "tipo": Calibracion.Tipo.PUNTO_UNICO,
                "puntos_curva": [],
                "observaciones": "Seed demo Calibrador A Plus (química CM260).",
            },
        )

        pcr = self._ensure_examen_pcr()
        pcr_us = TipoExamen.objects.filter(codigo="PCR_US").first()
        curvas = 0
        for exam in (pcr, pcr_us):
            if not exam:
                continue
            _, created_curva = Calibracion.objects.get_or_create(
                equipo=equipo,
                tipo_examen=exam,
                tipo=Calibracion.Tipo.CURVA_MULTIPUNTO,
                codigo_lote=f"CURVA-{exam.codigo}-DEMO",
                fecha=hoy,
                defaults={
                    "vigente_hasta": hoy + timedelta(days=30),
                    "calibrador_nombre": f"Curva aglutinación {exam.codigo}",
                    "marca": STANDATROL_MARCA,
                    "puntos_curva": CURVA_PCR_DEMO,
                    "observaciones": "Seed demo curva multipunto PCR (aglutinación).",
                },
            )
            if created_curva:
                curvas += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"QC seed OK equipo={equipo.codigo} materiales_nuevos={mats_creados} "
                f"lotes_nuevos={lotes_creados} cal_a_plus_id={cal_a_plus.id} curvas_nuevas={curvas}"
            )
        )
