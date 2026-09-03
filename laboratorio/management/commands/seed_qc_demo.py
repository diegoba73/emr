"""Seed QC: equipos reales + productos multiparámetro + materiales VIDAS/Finecare."""
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from laboratorio.equipos_lab import (
    EQUIPOS_LAB,
    EQUIPOS_MULTIPARAM,
    EXAMEN_A_EQUIPO,
    IQC_MATERIALES_POR_EQUIPO,
    PRODUCTOS_MULTIPARAM,
    TARGETS_POR_PRODUCTO,
)
from laboratorio.models import TipoExamen, TipoMuestra
from laboratorio.models_qc import (
    Calibracion,
    EquipoAnalizador,
    LoteControl,
    LoteProductoControl,
    MaterialControl,
    ProductoControl,
    TargetLoteControl,
)

STANDATROL_MARCA = "Wiener"
LOTE_DEMO = "QC-DEMO"
CALIBRADOR_A_PLUS = "Calibrador A Plus"

TARGET_S1 = (Decimal("100.0000"), Decimal("5.0000"))
TARGET_S2 = (Decimal("200.0000"), Decimal("10.0000"))

CURVA_PCR_DEMO = [
    {"orden": 1, "concentracion": "0", "senal": "0.010", "unidad": "mg/L"},
    {"orden": 2, "concentracion": "5", "senal": "0.120", "unidad": "mg/L"},
    {"orden": 3, "concentracion": "20", "senal": "0.380", "unidad": "mg/L"},
    {"orden": 4, "concentracion": "80", "senal": "0.920", "unidad": "mg/L"},
    {"orden": 5, "concentracion": "160", "senal": "1.450", "unidad": "mg/L"},
]

PRODUCTO_POR_EQUIPO_ENSAYO = {
    "VIDAS_KUBE": "Control VIDAS",
    "FINECARE": "Control Finecare",
}


class Command(BaseCommand):
    help = (
        "Crea equipos, productos multiparámetro (Standatrol/Sysmex/etc.) + lote/targets, "
        "materiales IQC solo VIDAS/Finecare, y calibraciones CM260."
    )

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

    def _ensure_equipos(self) -> dict[str, EquipoAnalizador]:
        out: dict[str, EquipoAnalizador] = {}
        for codigo, meta in EQUIPOS_LAB.items():
            eq, created = EquipoAnalizador.objects.get_or_create(
                codigo=codigo,
                defaults={
                    "nombre": meta["nombre"],
                    "marca_modelo": meta["marca_modelo"],
                    "activo": True,
                },
            )
            updates = []
            if not created:
                if eq.nombre != meta["nombre"]:
                    eq.nombre = meta["nombre"]
                    updates.append("nombre")
                if eq.marca_modelo != meta["marca_modelo"]:
                    eq.marca_modelo = meta["marca_modelo"]
                    updates.append("marca_modelo")
                if not eq.activo:
                    eq.activo = True
                    updates.append("activo")
                if updates:
                    eq.save(update_fields=[*updates, "updated_at"])
            out[codigo] = eq
        EquipoAnalizador.objects.filter(codigo="ANALIZADOR-DEMO").update(activo=False)
        return out

    def _asignar_examenes_a_equipos(self, equipos: dict[str, EquipoAnalizador]) -> int:
        updated = 0
        for codigo_ex, codigo_eq in EXAMEN_A_EQUIPO.items():
            eq = equipos.get(codigo_eq)
            if not eq:
                continue
            n = TipoExamen.objects.filter(codigo=codigo_ex).exclude(equipo_analizador=eq).update(
                equipo_analizador=eq
            )
            updated += n
        return updated

    def _ensure_productos_multiparam(
        self, equipos: dict[str, EquipoAnalizador], venc
    ) -> tuple[int, int, int]:
        prods = 0
        lotes = 0
        targets = 0
        for codigo, meta in PRODUCTOS_MULTIPARAM.items():
            eq = equipos.get(meta["equipo"])
            if not eq:
                continue
            prod, created = ProductoControl.objects.get_or_create(
                codigo=codigo,
                defaults={
                    "nombre": meta["nombre"],
                    "marca": meta["marca"],
                    "equipo": eq,
                    "modo": ProductoControl.Modo.MULTIPARAM,
                    "activo": True,
                },
            )
            if created:
                prods += 1
            else:
                updates = []
                if prod.nombre != meta["nombre"]:
                    prod.nombre = meta["nombre"]
                    updates.append("nombre")
                if prod.equipo_id != eq.id:
                    prod.equipo = eq
                    updates.append("equipo")
                if prod.modo != ProductoControl.Modo.MULTIPARAM:
                    prod.modo = ProductoControl.Modo.MULTIPARAM
                    updates.append("modo")
                if not prod.activo:
                    prod.activo = True
                    updates.append("activo")
                if updates:
                    prod.save(update_fields=[*updates, "updated_at"])

            lote, lot_created = LoteProductoControl.objects.get_or_create(
                producto=prod,
                codigo_lote=f"{LOTE_DEMO}-{codigo}",
                defaults={"vencimiento": venc, "activo": True},
            )
            if lot_created:
                lotes += 1
            elif not lote.activo:
                lote.activo = True
                lote.save(update_fields=["activo", "updated_at"])

            codigos_ex = TARGETS_POR_PRODUCTO.get(codigo, frozenset())
            examenes = list(TipoExamen.objects.filter(codigo__in=codigos_ex, activo=True))
            for examen in examenes:
                for nivel, (media, de) in (
                    (TargetLoteControl.Nivel.N1, TARGET_S1),
                    (TargetLoteControl.Nivel.N2, TARGET_S2),
                ):
                    _, t_created = TargetLoteControl.objects.get_or_create(
                        lote=lote,
                        tipo_examen=examen,
                        nivel=nivel,
                        defaults={"media_target": media, "de_target": de},
                    )
                    if t_created:
                        targets += 1
        return prods, lotes, targets

    def _desactivar_materiales_multiparam(self) -> int:
        qs = MaterialControl.objects.filter(activo=True).filter(
            equipo__codigo__in=EQUIPOS_MULTIPARAM
        )
        n = qs.update(activo=False)
        # Materiales sin equipo cuyo examen ahora es de equipo multiparam
        extra = 0
        for mat in MaterialControl.objects.filter(activo=True, equipo__isnull=True).select_related(
            "tipo_examen"
        ):
            dest = EXAMEN_A_EQUIPO.get((mat.tipo_examen.codigo or "").strip().upper())
            if dest in EQUIPOS_MULTIPARAM:
                mat.activo = False
                mat.save(update_fields=["activo", "updated_at"])
                extra += 1
        return n + extra

    def _ensure_materiales_por_ensayo(
        self, equipos: dict[str, EquipoAnalizador], venc
    ) -> tuple[int, int, int]:
        mats_creados = 0
        mats_actualizados = 0
        lotes_creados = 0
        for codigo_eq, codigos_ex in IQC_MATERIALES_POR_EQUIPO.items():
            eq = equipos.get(codigo_eq)
            if not eq:
                continue
            producto = PRODUCTO_POR_EQUIPO_ENSAYO.get(codigo_eq, "Control IQC")
            examenes = list(TipoExamen.objects.filter(codigo__in=codigos_ex, activo=True))
            for examen in examenes:
                if examen.equipo_analizador_id != eq.id:
                    examen.equipo_analizador = eq
                    examen.save(update_fields=["equipo_analizador"])
                for nivel, (media, de) in (
                    (MaterialControl.Nivel.N1, TARGET_S1),
                    (MaterialControl.Nivel.N2, TARGET_S2),
                ):
                    material = MaterialControl.objects.filter(
                        tipo_examen=examen, nivel=nivel
                    ).first()
                    if not material:
                        material = MaterialControl.objects.create(
                            tipo_examen=examen,
                            nivel=nivel,
                            equipo=eq,
                            nombre=f"{producto} {examen.codigo} {nivel}",
                            marca=eq.marca_modelo,
                            producto=producto,
                            media_target=media,
                            de_target=de,
                            activo=True,
                        )
                        mats_creados += 1
                    else:
                        updates = []
                        if material.equipo_id != eq.id:
                            material.equipo = eq
                            updates.append("equipo")
                        if not material.producto:
                            material.producto = producto
                            updates.append("producto")
                        if not material.activo:
                            material.activo = True
                            updates.append("activo")
                        if updates:
                            material.save(update_fields=[*updates, "updated_at"])
                            mats_actualizados += 1

                    _, lot_created = LoteControl.objects.get_or_create(
                        material=material,
                        codigo_lote=f"{LOTE_DEMO}-{codigo_eq}",
                        defaults={"vencimiento": venc, "activo": True},
                    )
                    if lot_created:
                        lotes_creados += 1
        return mats_creados, mats_actualizados, lotes_creados

    def handle(self, *args, **options):
        hoy = timezone.localdate()
        venc = hoy + timedelta(days=365)

        equipos = self._ensure_equipos()
        n_map = self._asignar_examenes_a_equipos(equipos)
        prods, lotes_prod, targets = self._ensure_productos_multiparam(equipos, venc)
        desact = self._desactivar_materiales_multiparam()
        mats_creados, mats_act, lotes_mat = self._ensure_materiales_por_ensayo(equipos, venc)

        cm260 = equipos["CM260"]
        cal_a_plus, _ = Calibracion.objects.get_or_create(
            equipo=cm260,
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
        if pcr and pcr.equipo_analizador_id != cm260.id:
            pcr.equipo_analizador = cm260
            pcr.save(update_fields=["equipo_analizador"])
        pcr_us = TipoExamen.objects.filter(codigo="PCR_US").first()
        curvas = 0
        for exam in (pcr, pcr_us):
            if not exam:
                continue
            _, created_curva = Calibracion.objects.get_or_create(
                equipo=cm260,
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
                f"QC seed OK equipos={len(equipos)} examenes_mapeados={n_map} "
                f"productos={prods} lotes_prod={lotes_prod} targets={targets} "
                f"mats_multiparam_off={desact} materiales_nuevos={mats_creados} "
                f"materiales_act={mats_act} lotes_mat={lotes_mat} "
                f"cal_a_plus_id={cal_a_plus.id} curvas_nuevas={curvas}"
            )
        )
