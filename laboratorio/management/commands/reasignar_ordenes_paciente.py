"""
Reasigna órdenes LIMS (y vínculos directos) de un paciente a otro.

Por defecto solo dry-run. No modifica fichas ``Paciente`` ni DNIs.

Caso Piu / Arevalo (prod)::

    # Dry-run (recomendado primero)
    python manage.py reasignar_ordenes_paciente \\
      --origen-id 638 --destino-id 1331 \\
      --confirm-origen-dni 13622071 --confirm-destino-dni 4749363

    # Persistir
    python manage.py reasignar_ordenes_paciente \\
      --origen-id 638 --destino-id 1331 \\
      --confirm-origen-dni 13622071 --confirm-destino-dni 4749363 \\
      --apply

Qué mueve (solo FK ``paciente_id``):
  - ``laboratorio.SolicitudExamen`` (+ resultados cuelgan de la solicitud)
  - ``laboratorio.Muestra``
  - ``laboratorio.EstudioMicrobiologia``
  - ``integracion_lims.SolicitudExamenLims`` (legado, si hay filas)

Qué NO toca:
  - ``pacientes.Paciente`` (apellido, DNI, demografía)
  - turnos, atenciones, archivos médicos, estudios complementarios
    (el dry-run los cuenta como referencia; usar ``--incluir-emr`` para moverlos)
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Count

from pacientes.models import Paciente


def _fmt_pac(p: Paciente) -> str:
    return (
        f"id={p.pk} dni={p.dni!r} "
        f"{(p.apellido or '').strip()}, {(p.nombre or '').strip()}"
    )


class Command(BaseCommand):
    help = (
        "Reasigna órdenes LIMS de un paciente a otro "
        "(dry-run por defecto; no altera fichas/DNI)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--origen-id",
            type=int,
            required=True,
            help="PK paciente origen (donde están hoy las órdenes mal vinculadas).",
        )
        parser.add_argument(
            "--destino-id",
            type=int,
            required=True,
            help="PK paciente destino (DNI correcto).",
        )
        parser.add_argument(
            "--confirm-origen-dni",
            required=True,
            help="DNI esperado en la ficha origen (doble check de seguridad).",
        )
        parser.add_argument(
            "--confirm-destino-dni",
            required=True,
            help="DNI esperado en la ficha destino (doble check de seguridad).",
        )
        parser.add_argument(
            "--incluir-emr",
            action="store_true",
            help=(
                "Además reasigna turnos, atenciones, archivos médicos, "
                "estudios complementarios e internaciones del origen. "
                "Sin este flag solo LIMS."
            ),
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Persiste. Sin este flag solo lista el plan (dry-run).",
        )

    def handle(self, *args, **options):
        origen_id = int(options["origen_id"])
        destino_id = int(options["destino_id"])
        dni_origen = str(options["confirm_origen_dni"]).strip()
        dni_destino = str(options["confirm_destino_dni"]).strip()
        incluir_emr = bool(options["incluir_emr"])
        apply = bool(options["apply"])

        if origen_id == destino_id:
            raise CommandError("origen y destino deben ser distintos.")

        origen = Paciente.objects.filter(pk=origen_id).first()
        destino = Paciente.objects.filter(pk=destino_id).first()
        if origen is None:
            raise CommandError(f"Paciente origen id={origen_id} no existe.")
        if destino is None:
            raise CommandError(f"Paciente destino id={destino_id} no existe.")

        if str(origen.dni).strip() != dni_origen:
            raise CommandError(
                f"DNI origen no coincide: ficha tiene {origen.dni!r}, "
                f"confirmaste {dni_origen!r}. Abortado."
            )
        if str(destino.dni).strip() != dni_destino:
            raise CommandError(
                f"DNI destino no coincide: ficha tiene {destino.dni!r}, "
                f"confirmaste {dni_destino!r}. Abortado."
            )

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "Reasignar órdenes paciente "
                + ("(APPLY)" if apply else "(dry-run, no escribe)")
            )
        )
        self.stdout.write(f"Origen:  {_fmt_pac(origen)}")
        self.stdout.write(f"Destino: {_fmt_pac(destino)}")
        self.stdout.write(
            "Fichas Paciente / DNIs: NO se modifican.\n"
        )

        plan = self._build_plan(origen_id, destino_id, incluir_emr)
        self._print_plan(plan)

        if not apply:
            self.stdout.write(
                self.style.WARNING(
                    "\nDry-run OK. Para persistir, repetí con --apply "
                    "(backup previo en prod)."
                )
            )
            return

        with transaction.atomic():
            self._apply_plan(plan, origen_id, destino_id)

        self.stdout.write(self.style.SUCCESS("\nAPPLY completado."))
        self._print_post_counts(origen_id, destino_id, incluir_emr)

    def _build_plan(self, origen_id: int, destino_id: int, incluir_emr: bool) -> dict:
        from laboratorio.models import ResultadoExamen, SolicitudExamen
        from laboratorio.models_catalog import Muestra
        from laboratorio.models_microbiologia import EstudioMicrobiologia

        sols = list(
            SolicitudExamen.objects.filter(paciente_id=origen_id)
            .order_by("numero", "id")
            .values(
                "id",
                "numero",
                "estado",
                "fecha_programada_toma",
                "material_pedido",
                "consulta_hc_id",
            )
        )
        sol_ids = [s["id"] for s in sols]
        n_resultados = (
            ResultadoExamen.objects.filter(solicitud_id__in=sol_ids).count()
            if sol_ids
            else 0
        )
        muestras = list(
            Muestra.objects.filter(paciente_id=origen_id)
            .order_by("id")
            .values("id", "codigo_barra", "estado", "solicitud_id")
        )
        estudios_micro = list(
            EstudioMicrobiologia.objects.filter(paciente_id=origen_id)
            .order_by("id")
            .values("id", "numero", "estado", "solicitud_id", "consulta_hc_id")
        )

        # consulta_hc de otra HC quedaría inconsistente tras el cambio de paciente
        sols_con_hc = [s for s in sols if s["consulta_hc_id"]]
        micro_con_hc = [e for e in estudios_micro if e["consulta_hc_id"]]

        # Choques potenciales de cupo activo mismo día/material en destino
        estados_bloqueantes = ("PENDIENTE", "EN_PROCESO", "LISTO_PARA_VALIDAR")
        choques = []
        if sols:
            dest_abiertas = (
                SolicitudExamen.objects.filter(
                    paciente_id=destino_id,
                    estado__in=estados_bloqueantes,
                )
                .values("fecha_programada_toma", "material_pedido")
                .annotate(n=Count("id"))
            )
            dest_keys = {
                (r["fecha_programada_toma"], r["material_pedido"] or "")
                for r in dest_abiertas
            }
            for s in sols:
                if s["estado"] not in estados_bloqueantes:
                    continue
                key = (s["fecha_programada_toma"], s["material_pedido"] or "")
                if key in dest_keys:
                    choques.append(s)

        lims_legado_n = 0
        try:
            from integracion_lims.models import SolicitudExamenLims

            lims_legado_n = SolicitudExamenLims.objects.filter(
                paciente_id=origen_id
            ).count()
        except Exception:
            lims_legado_n = 0

        emr = {}
        if True:  # siempre contar EMR en el reporte
            emr = self._count_emr(origen_id)

        return {
            "sols": sols,
            "n_resultados": n_resultados,
            "muestras": muestras,
            "estudios_micro": estudios_micro,
            "sols_con_hc": sols_con_hc,
            "micro_con_hc": micro_con_hc,
            "choques": choques,
            "lims_legado_n": lims_legado_n,
            "emr": emr,
            "incluir_emr": incluir_emr,
        }

    def _count_emr(self, origen_id: int) -> dict:
        out: dict[str, int] = {}
        try:
            from turnos.models import Turno, Atencion

            out["turnos"] = Turno.objects.filter(paciente_id=origen_id).count()
            out["atenciones"] = Atencion.objects.filter(paciente_id=origen_id).count()
        except Exception:
            out["turnos"] = out["atenciones"] = -1
        try:
            from archivos_medicos.models import ArchivoMedico

            out["archivos_medicos"] = ArchivoMedico.objects.filter(
                paciente_id=origen_id
            ).count()
        except Exception:
            out["archivos_medicos"] = -1
        try:
            from estudios.models import EstudioComplementario

            out["estudios_complementarios"] = EstudioComplementario.objects.filter(
                paciente_id=origen_id
            ).count()
        except Exception:
            out["estudios_complementarios"] = -1
        try:
            from internacion.models import Internacion

            out["internaciones"] = Internacion.objects.filter(
                paciente_id=origen_id
            ).count()
        except Exception:
            out["internaciones"] = -1
        return out

    def _print_plan(self, plan: dict) -> None:
        sols = plan["sols"]
        self.stdout.write(
            self.style.NOTICE(
                f"\nLIMS SolicitudExamen a mover: {len(sols)} "
                f"(ResultadoExamen vinculados: {plan['n_resultados']})"
            )
        )
        for s in sols:
            self.stdout.write(
                f"  · {s['numero'] or '(sin número)'} pk={s['id']} "
                f"estado={s['estado']} fpt={s['fecha_programada_toma']} "
                f"mat={s['material_pedido'] or '-'} "
                f"consulta_hc={s['consulta_hc_id'] or '-'}"
            )

        self.stdout.write(
            self.style.NOTICE(f"\nLIMS Muestra a mover: {len(plan['muestras'])}")
        )
        for m in plan["muestras"][:50]:
            self.stdout.write(
                f"  · pk={m['id']} barra={m['codigo_barra'] or '-'} "
                f"estado={m['estado']} solicitud_id={m['solicitud_id']}"
            )
        if len(plan["muestras"]) > 50:
            self.stdout.write(f"  … +{len(plan['muestras']) - 50} más")

        self.stdout.write(
            self.style.NOTICE(
                f"\nLIMS EstudioMicrobiologia a mover: {len(plan['estudios_micro'])}"
            )
        )
        for e in plan["estudios_micro"]:
            self.stdout.write(
                f"  · {e['numero'] or '(sin número)'} pk={e['id']} "
                f"estado={e['estado']} solicitud_id={e['solicitud_id']}"
            )

        if plan["lims_legado_n"]:
            self.stdout.write(
                self.style.NOTICE(
                    f"\nintegracion_lims.SolicitudExamenLims: {plan['lims_legado_n']}"
                )
            )

        if plan["sols_con_hc"] or plan["micro_con_hc"]:
            self.stdout.write(
                self.style.WARNING(
                    f"\nAl APPLY se limpiará consulta_hc en "
                    f"{len(plan['sols_con_hc'])} orden(es) y "
                    f"{len(plan['micro_con_hc'])} estudio(s) micro "
                    f"(evitar inconsistencia HC↔paciente)."
                )
            )

        if plan["choques"]:
            self.stdout.write(
                self.style.WARNING(
                    "\nAviso: hay órdenes ABIERTAS origen que chocan día/material "
                    "con abiertas del destino (anti-dup LIMS). Se mueven igual; "
                    "revisá cupos después:"
                )
            )
            for s in plan["choques"]:
                self.stdout.write(
                    f"  ! {s['numero']} estado={s['estado']} "
                    f"fpt={s['fecha_programada_toma']} mat={s['material_pedido'] or '-'}"
                )

        emr = plan["emr"]
        self.stdout.write(self.style.NOTICE("\nOtros vínculos EMR en origen (referencia):"))
        for k, v in emr.items():
            self.stdout.write(f"  · {k}: {v}")
        if plan["incluir_emr"]:
            self.stdout.write(
                self.style.WARNING(
                    "  → --incluir-emr activo: esos vínculos SÍ se reasignarán."
                )
            )
        else:
            self.stdout.write(
                "  → no se mueven (solo LIMS). Pasá --incluir-emr si también deben ir."
            )

    def _apply_plan(self, plan: dict, origen_id: int, destino_id: int) -> None:
        from laboratorio.models import SolicitudExamen
        from laboratorio.models_catalog import Muestra
        from laboratorio.models_microbiologia import EstudioMicrobiologia

        n_sol = SolicitudExamen.objects.filter(paciente_id=origen_id).update(
            paciente_id=destino_id,
            consulta_hc_id=None,
        )
        n_mue = Muestra.objects.filter(paciente_id=origen_id).update(
            paciente_id=destino_id,
        )
        n_micro = EstudioMicrobiologia.objects.filter(paciente_id=origen_id).update(
            paciente_id=destino_id,
            consulta_hc_id=None,
        )
        self.stdout.write(f"Updated SolicitudExamen: {n_sol}")
        self.stdout.write(f"Updated Muestra: {n_mue}")
        self.stdout.write(f"Updated EstudioMicrobiologia: {n_micro}")

        try:
            from integracion_lims.models import SolicitudExamenLims

            n_leg = SolicitudExamenLims.objects.filter(paciente_id=origen_id).update(
                paciente_id=destino_id,
            )
            self.stdout.write(f"Updated SolicitudExamenLims: {n_leg}")
        except Exception as exc:
            self.stdout.write(f"SolicitudExamenLims omitido: {exc}")

        if plan["incluir_emr"]:
            self._apply_emr(origen_id, destino_id)

        # Verificación mínima: no deben quedar LIMS en origen
        left = SolicitudExamen.objects.filter(paciente_id=origen_id).count()
        if left:
            raise CommandError(
                f"Quedaron {left} SolicitudExamen en origen tras UPDATE; rollback."
            )

    def _apply_emr(self, origen_id: int, destino_id: int) -> None:
        from turnos.models import Turno, Atencion
        from archivos_medicos.models import ArchivoMedico
        from estudios.models import EstudioComplementario
        from internacion.models import Internacion

        for label, model in (
            ("Turno", Turno),
            ("Atencion", Atencion),
            ("ArchivoMedico", ArchivoMedico),
            ("EstudioComplementario", EstudioComplementario),
            ("Internacion", Internacion),
        ):
            n = model.objects.filter(paciente_id=origen_id).update(
                paciente_id=destino_id
            )
            self.stdout.write(f"Updated {label}: {n}")

    def _print_post_counts(
        self, origen_id: int, destino_id: int, incluir_emr: bool
    ) -> None:
        from laboratorio.models import SolicitudExamen
        from laboratorio.models_catalog import Muestra
        from laboratorio.models_microbiologia import EstudioMicrobiologia

        self.stdout.write("\nConteos post-APPLY:")
        for label, pid in (("origen", origen_id), ("destino", destino_id)):
            ns = SolicitudExamen.objects.filter(paciente_id=pid).count()
            nm = Muestra.objects.filter(paciente_id=pid).count()
            ne = EstudioMicrobiologia.objects.filter(paciente_id=pid).count()
            self.stdout.write(
                f"  {label} id={pid}: solicitudes={ns} muestras={nm} micro={ne}"
            )
        # Fichas intactas
        o = Paciente.objects.get(pk=origen_id)
        d = Paciente.objects.get(pk=destino_id)
        self.stdout.write(f"Ficha origen intacta:  {_fmt_pac(o)}")
        self.stdout.write(f"Ficha destino intacta: {_fmt_pac(d)}")
        if not incluir_emr:
            self.stdout.write("(EMR no incluido en este APPLY)")
