"""
Unifica TipoMuestra SANGRE (Sangre Suero) → SUERO y asigna tubos a todos los exámenes.

Uso:
  python manage.py unificar_suero_y_asignar_tubos
  python manage.py unificar_suero_y_asignar_tubos --dry-run
"""

from __future__ import annotations

from collections import Counter

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from laboratorio.models import TipoExamen, TipoMuestra
from laboratorio.models_catalog import Muestra, TipoContenedor
from laboratorio.tubos_catalogo import CONTENEDORES_TODOS, tubo_codigo_para_examen


class Command(BaseCommand):
    help = "Unifica muestras suero duplicadas y asigna tipo_contenedor a todos los exámenes."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        dry = options["dry_run"]
        if dry:
            self.stdout.write(self.style.WARNING("dry-run: sin persistir"))

        with transaction.atomic():
            canon = self._unificar_suero(dry)
            self._ensure_contenedores()
            stats = self._asignar_tubos(dry)
            stats.update(self._alinear_muestra_con_tubo_por_analito(dry))
            if dry:
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS("Listo."))
        self.stdout.write(f"  muestra canónica: {canon.codigo} — {canon.nombre} (id={canon.id})")
        for k, v in stats.items():
            self.stdout.write(f"  {k}: {v}")

    def _unificar_suero(self, dry: bool) -> TipoMuestra:
        suero = TipoMuestra.objects.filter(codigo__iexact="SUERO").first()
        sangre = TipoMuestra.objects.filter(codigo__iexact="SANGRE").first()

        if suero is None and sangre is None:
            raise CommandError("No existe TipoMuestra SUERO ni SANGRE.")

        if suero is None:
            # Renombrar SANGRE → SUERO
            sangre.codigo = "SUERO"
            sangre.nombre = "Suero"
            sangre.color_tubo = sangre.color_tubo or "Rojo"
            sangre.activo = True
            if not dry:
                sangre.save()
            self.stdout.write("  Renombrado SANGRE → SUERO")
            return sangre

        # Asegurar nombre canónico
        if suero.nombre.lower() != "suero" or not suero.activo:
            suero.nombre = "Suero"
            suero.color_tubo = suero.color_tubo or "Rojo"
            suero.activo = True
            if not dry:
                suero.save(update_fields=["nombre", "color_tubo", "activo"])

        if sangre is None or sangre.id == suero.id:
            return suero

        n_ex = TipoExamen.objects.filter(tipo_muestra_requerida=sangre).count()
        n_mu = Muestra.objects.filter(tipo_muestra=sangre).count()
        self.stdout.write(
            f"  Fusionando SANGRE(id={sangre.id}) → SUERO(id={suero.id}): "
            f"{n_ex} exámenes, {n_mu} muestras transaccionales"
        )
        if not dry:
            TipoExamen.objects.filter(tipo_muestra_requerida=sangre).update(
                tipo_muestra_requerida=suero
            )
            Muestra.objects.filter(tipo_muestra=sangre).update(tipo_muestra=suero)
            sangre.activo = False
            sangre.nombre = f"{sangre.nombre} (fusionado → SUERO)"
            sangre.save(update_fields=["activo", "nombre"])

        return suero

    def _ensure_contenedores(self) -> None:
        for codigo, nombre, color, aditivo in CONTENEDORES_TODOS:
            obj, created = TipoContenedor.objects.get_or_create(
                codigo=codigo,
                defaults={
                    "nombre": nombre,
                    "color": color,
                    "aditivo": aditivo,
                    "activo": True,
                    "descripcion": "",
                },
            )
            if not created:
                # Mantener metadatos canónicos (VSG negro, coag celeste, etc.)
                updates = []
                if obj.nombre != nombre:
                    obj.nombre = nombre
                    updates.append("nombre")
                if obj.color != color:
                    obj.color = color
                    updates.append("color")
                if obj.aditivo != aditivo:
                    obj.aditivo = aditivo
                    updates.append("aditivo")
                if not obj.activo:
                    obj.activo = True
                    updates.append("activo")
                if updates:
                    obj.save(update_fields=updates)

    def _asignar_tubos(self, dry: bool) -> dict:
        by_codigo = {tc.codigo: tc for tc in TipoContenedor.objects.filter(activo=True)}
        updated = 0
        already = 0
        missing = 0
        dist: Counter[str] = Counter()

        qs = TipoExamen.objects.select_related("tipo_muestra_requerida", "tipo_contenedor")
        for ex in qs.iterator():
            m = ex.tipo_muestra_requerida
            tubo = tubo_codigo_para_examen(
                ex.codigo,
                m.codigo if m else None,
                muestra_nombre=m.nombre if m else None,
            )
            dist[tubo] += 1
            tc = by_codigo.get(tubo)
            if tc is None:
                missing += 1
                continue
            if ex.tipo_contenedor_id == tc.pk:
                already += 1
                continue
            if not dry:
                TipoExamen.objects.filter(pk=ex.pk).update(tipo_contenedor_id=tc.pk)
            updated += 1

        sin_tubo = TipoExamen.objects.filter(activo=True, tipo_contenedor_id__isnull=True).count()
        return {
            "examenes_tubo_actualizados": updated,
            "examenes_tubo_ya_ok": already,
            "examenes_sin_contenedor_catalogo": missing,
            "activos_sin_tubo_tras_sync": sin_tubo if not dry else "n/a (dry-run)",
            "distribucion": dict(dist),
        }

    def _alinear_muestra_con_tubo_por_analito(self, dry: bool) -> dict:
        """
        Fuerza tubo + muestra canónica para analitos con regla fija:
        EDTA / coagulación / VSG / gases / química rutina.
        SUERO (rojo) queda solo para analitos fuera de esas familias.
        """
        from laboratorio.tubos_catalogo import (
            BIDON_ORINA_24H,
            CITRATO,
            CITRATO_VSG,
            EDTA,
            FRASCO_ORINA,
            HEPARINA,
            MUESTRA_CANONICA_POR_ANALITO,
            MUESTRA_ORINA,
            MUESTRA_ORINA_24H,
            _CITRATO,
            _CITRATO_VSG,
            _EAB_ART,
            _EAB_JERINGA_INDIVIDUAL,
            _EAB_VEN,
            _EDTA,
            _FRASCO_ORINA,
            _HEPARINA_GASES,
            _ORINA_24H,
            _QUIMICA_RUTINA,
            es_muestra_orina_24h,
        )

        defaults_muestra = {
            "SANGRE_EDTA": ("Sangre EDTA", "Morado"),
            "PLASMA_CITRATO": ("Plasma citrato", "Celeste"),
            "SANGRE_CITRATO_VSG": ("Sangre citrato VSG", "Negro"),
            "SANGRE_HEPARINA": ("Sangre heparina", "Verde"),
            "SANGRE_HEPARINA_ART": ("Sangre heparina arterial", "Verde"),
            "SANGRE_HEPARINA_VEN": ("Sangre heparina venosa", "Verde"),
            "PLASMA_HEPARINA": ("Plasma heparina", "Verde"),
            MUESTRA_ORINA: ("Orina", "Ámbar"),
            MUESTRA_ORINA_24H: ("Orina 24 hs", "Ámbar"),
        }
        muestras: dict[str, TipoMuestra] = {}
        for codigo, (nombre, color) in defaults_muestra.items():
            tm, _ = TipoMuestra.objects.get_or_create(
                codigo=codigo,
                defaults={"nombre": nombre, "color_tubo": color, "activo": True},
            )
            if not tm.activo:
                tm.activo = True
                if not dry:
                    tm.save(update_fields=["activo"])
            muestras[codigo] = tm

        tubos = {
            tc.codigo: tc
            for tc in TipoContenedor.objects.filter(
                codigo__in=[EDTA, CITRATO, CITRATO_VSG, HEPARINA, FRASCO_ORINA, BIDON_ORINA_24H],
                activo=True,
            )
        }

        gases_sin_eab = _HEPARINA_GASES - _EAB_JERINGA_INDIVIDUAL
        grupos = (
            (_EDTA, EDTA, "SANGRE_EDTA"),
            (_CITRATO, CITRATO, "PLASMA_CITRATO"),
            (_CITRATO_VSG, CITRATO_VSG, "SANGRE_CITRATO_VSG"),
            (gases_sin_eab, HEPARINA, "SANGRE_HEPARINA"),
            (_EAB_ART, HEPARINA, "SANGRE_HEPARINA_ART"),
            (_EAB_VEN, HEPARINA, "SANGRE_HEPARINA_VEN"),
            (_QUIMICA_RUTINA, HEPARINA, "PLASMA_HEPARINA"),
            (_FRASCO_ORINA, FRASCO_ORINA, MUESTRA_ORINA),
            (_ORINA_24H, BIDON_ORINA_24H, MUESTRA_ORINA_24H),
        )
        stats: dict[str, int] = {}
        for codigos, tubo_codigo, muestra_codigo in grupos:
            tc = tubos.get(tubo_codigo)
            tm = muestras[muestra_codigo]
            key = f"alineados_{muestra_codigo.lower()}"
            if tc is None:
                stats[key] = 0
                continue
            n = 0
            for ex in TipoExamen.objects.filter(codigo__in=codigos).select_related(
                "tipo_contenedor", "tipo_muestra_requerida"
            ):
                needs = (
                    ex.tipo_contenedor_id != tc.pk
                    or ex.tipo_muestra_requerida_id != tm.pk
                )
                if not needs:
                    continue
                n += 1
                if not dry:
                    TipoExamen.objects.filter(pk=ex.pk).update(
                        tipo_contenedor_id=tc.pk,
                        tipo_muestra_requerida_id=tm.pk,
                    )
            if n:
                self.stdout.write(
                    f"  Alineados {n}: {tubo_codigo} + {muestra_codigo} "
                    f"({len(codigos)} códigos familia)"
                )
            stats[key] = n
            assert all(
                MUESTRA_CANONICA_POR_ANALITO[c] == muestra_codigo for c in codigos
            )

        # IACA / materiales con orina 24 hs en el nombre → bidón (sin tocar su muestra)
        bidon = tubos.get(BIDON_ORINA_24H)
        n_iaca = 0
        if bidon is not None:
            for ex in TipoExamen.objects.filter(activo=True).select_related(
                "tipo_muestra_requerida", "tipo_contenedor"
            ):
                tm = ex.tipo_muestra_requerida
                if tm is None or not es_muestra_orina_24h(tm.codigo, tm.nombre):
                    continue
                if ex.tipo_contenedor_id == bidon.pk:
                    continue
                n_iaca += 1
                if not dry:
                    TipoExamen.objects.filter(pk=ex.pk).update(tipo_contenedor_id=bidon.pk)
        if n_iaca:
            self.stdout.write(f"  Alineados {n_iaca}: material orina 24h → BIDON_ORINA_24H")
        stats["alineados_iaca_orina_24h_tubo"] = n_iaca
        return stats
