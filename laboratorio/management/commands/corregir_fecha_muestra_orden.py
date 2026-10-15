"""
Corrige fecha_toma / fecha_recepcion de tubos de una orden.

Por defecto dry-run. Solo toca muestras cuya toma o recepción cae en
``--desde-fecha`` (default: hoy local).

Uso (prod):
  docker compose -f docker-compose.server.yml exec -T backend \\
    python manage.py corregir_fecha_muestra_orden LAB-2026-00138 --a-fecha 2026-10-05

  docker compose -f docker-compose.server.yml exec -T backend \\
    python manage.py corregir_fecha_muestra_orden LAB-2026-00138 --a-fecha 2026-10-05 --apply
"""
from __future__ import annotations

from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date

from laboratorio.models import SolicitudExamen
from laboratorio.models_catalog import Muestra


class Command(BaseCommand):
    help = (
        "Corrige fecha_toma/fecha_recepcion de tubos (dry-run por defecto). "
        "Solo muestras con toma/recepción en --desde-fecha."
    )

    def add_arguments(self, parser):
        parser.add_argument("numero", type=str, help="Número de orden (ej. LAB-2026-00138)")
        parser.add_argument(
            "--a-fecha",
            required=True,
            help="Nueva fecha de extracción/recepción (YYYY-MM-DD)",
        )
        parser.add_argument(
            "--desde-fecha",
            default=None,
            help="Solo tubos con toma/recepción ese día (default: hoy local)",
        )
        parser.add_argument(
            "--hora",
            default=None,
            help="Hora local HH:MM a aplicar (default: conserva la hora original de cada campo)",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Persiste. Sin este flag solo muestra el plan.",
        )

    def handle(self, *args, **options):
        numero = (options["numero"] or "").strip()
        a_fecha = parse_date(options["a_fecha"])
        if a_fecha is None:
            raise CommandError("--a-fecha inválida (usar YYYY-MM-DD)")

        desde_raw = options["desde_fecha"]
        desde_fecha = parse_date(desde_raw) if desde_raw else timezone.localdate()
        if desde_fecha is None:
            raise CommandError("--desde-fecha inválida (usar YYYY-MM-DD)")

        hora_fija = None
        if options["hora"]:
            try:
                hh, mm = options["hora"].split(":")
                hora_fija = time(int(hh), int(mm))
            except Exception as exc:
                raise CommandError("--hora inválida (usar HH:MM)") from exc

        apply = bool(options["apply"])
        tz = timezone.get_current_timezone()

        sol = (
            SolicitudExamen.objects.filter(numero=numero)
            .select_related("paciente")
            .prefetch_related("muestras__tipo_muestra")
            .first()
        )
        if sol is None:
            raise CommandError(f"No se encontró la orden {numero}")

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"Corregir fechas tubos {numero} "
                + ("(APPLY)" if apply else "(dry-run, no escribe)")
            )
        )
        pac = sol.paciente
        self.stdout.write(
            f"Orden pk={sol.pk} estado={sol.estado} "
            f"paciente={getattr(pac, 'apellido', '')}, {getattr(pac, 'nombre', '')} "
            f"programada={sol.fecha_programada_toma}"
        )
        self.stdout.write(f"Filtro origen: toma/recepción el {desde_fecha.isoformat()}")
        self.stdout.write(f"Nueva fecha: {a_fecha.isoformat()}")

        inicio = timezone.make_aware(datetime.combine(desde_fecha, time.min), tz)
        fin = inicio + timedelta(days=1)

        candidatas: list[Muestra] = []
        for m in sol.muestras.all().order_by("id"):
            toma_ok = m.fecha_toma is not None and inicio <= m.fecha_toma < fin
            recep_ok = m.fecha_recepcion is not None and inicio <= m.fecha_recepcion < fin
            if toma_ok or recep_ok:
                candidatas.append(m)

        if not candidatas:
            self.stdout.write(
                self.style.WARNING(
                    "No hay tubos con toma/recepción en esa fecha. Nada que hacer."
                )
            )
            return

        def _refecha(dt_orig):
            if dt_orig is None:
                return None
            local = timezone.localtime(dt_orig, tz)
            t = hora_fija if hora_fija is not None else local.timetz().replace(tzinfo=None)
            naive = datetime.combine(a_fecha, t)
            return timezone.make_aware(naive, tz)

        plan = []
        for m in candidatas:
            tipo = getattr(getattr(m, "tipo_muestra", None), "codigo", None) or "?"
            nueva_toma = _refecha(m.fecha_toma) if m.fecha_toma and inicio <= m.fecha_toma < fin else m.fecha_toma
            nueva_recep = (
                _refecha(m.fecha_recepcion)
                if m.fecha_recepcion and inicio <= m.fecha_recepcion < fin
                else m.fecha_recepcion
            )
            plan.append((m, tipo, nueva_toma, nueva_recep))
            self.stdout.write(
                f"  muestra id={m.pk} tipo={tipo} estado={m.estado}\n"
                f"    toma:  {m.fecha_toma} -> {nueva_toma}\n"
                f"    recep: {m.fecha_recepcion} -> {nueva_recep}"
            )

        if not apply:
            self.stdout.write(
                self.style.NOTICE("Dry-run OK. Relanzá con --apply para persistir.")
            )
            return

        with transaction.atomic():
            for m, _tipo, nueva_toma, nueva_recep in plan:
                fields = []
                if nueva_toma != m.fecha_toma:
                    m.fecha_toma = nueva_toma
                    fields.append("fecha_toma")
                if nueva_recep != m.fecha_recepcion:
                    m.fecha_recepcion = nueva_recep
                    fields.append("fecha_recepcion")
                if fields:
                    if hasattr(m, "updated_at"):
                        m.updated_at = timezone.now()
                        fields.append("updated_at")
                    m.save(update_fields=fields)

        self.stdout.write(
            self.style.SUCCESS(f"Actualizadas {len(plan)} muestra(s) en {numero}.")
        )
