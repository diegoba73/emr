"""
Seed LOCAL: N órdenes de rutina (sangre) para hoy — carga de bandeja.

Uso (Docker):
  docker exec emr_backend python manage.py seed_carga_listado_ordenes
  docker exec emr_backend python manage.py seed_carga_listado_ordenes --count 100
  docker exec emr_backend python manage.py seed_carga_listado_ordenes --en-proceso
  docker exec emr_backend python manage.py seed_carga_listado_ordenes --purge
  docker exec emr_backend python manage.py seed_carga_listado_ordenes --purge-only

Prefijo pacientes DNI: 89XXXXXX. Observaciones: SEED_CARGA_LISTADO.
Solo para desarrollo local; no usar en producción.
"""
from __future__ import annotations

from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from laboratorio.models import ResultadoExamen, SolicitudExamen, TipoExamen
from laboratorio.models_catalog import Muestra
from medicos.models import Medico
from pacientes.models import Paciente

MARKER = "SEED_CARGA_LISTADO"
DNI_PREFIX = "89"
CODIGOS_RUTINA = (
    "GLU",
    "UREA",
    "CREATI",
    "COL_TOT",
    "TG",
    "GOT",
    "GPT",
    "NA",
    "K",
    "CL",
)


class Command(BaseCommand):
    help = "Crea N órdenes de rutina para hoy (prueba de carga del listado)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=100,
            help="Cantidad de órdenes a crear (default 100).",
        )
        parser.add_argument(
            "--purge",
            action="store_true",
            help="Borra seeds previos del marker antes de crear.",
        )
        parser.add_argument(
            "--purge-only",
            action="store_true",
            help="Solo borra seeds previos; no crea.",
        )
        parser.add_argument(
            "--en-proceso",
            action="store_true",
            help=(
                "Pasa las órdenes seed a EN_PROCESO con muestra tomada/recibida hoy "
                "(para Órdenes LIMS → vista del día / fecha_muestra)."
            ),
        )

    def handle(self, *args, **options):
        from django.conf import settings

        if not getattr(settings, "DEBUG", False):
            raise CommandError(
                "Rechazado: seed_carga_listado_ordenes solo corre con DEBUG=True (local)."
            )

        if options["purge"] or options["purge_only"]:
            deleted = self._purge()
            self.stdout.write(self.style.WARNING(f"Purge: borradas {deleted} órdenes seed."))
            if options["purge_only"]:
                return

        # Solo avanzar seeds ya creados (sin recrear).
        if options["en_proceso"] and not options["purge"]:
            n = self._pasar_en_proceso()
            self.stdout.write(
                self.style.SUCCESS(
                    f"OK: {n} órdenes seed → EN_PROCESO con fecha_toma=hoy. "
                    "Probar: Laboratorio → Órdenes LIMS (día de hoy)."
                )
            )
            return

        count = int(options["count"])
        if count < 1 or count > 500:
            raise CommandError("--count debe estar entre 1 y 500.")

        tipos = list(
            TipoExamen.objects.filter(codigo__in=CODIGOS_RUTINA, activo=True).order_by(
                "codigo"
            )
        )
        if len(tipos) < 3:
            raise CommandError(
                "Catálogo insuficiente (GLU/UREA/…). Corré ./emrctl seed / poblar catálogo."
            )
        faltan = set(CODIGOS_RUTINA) - {t.codigo for t in tipos}
        if faltan:
            self.stdout.write(
                self.style.WARNING(f"Códigos ausentes (se omite): {sorted(faltan)}")
            )

        medico = Medico.objects.order_by("id").first()
        if medico is None:
            raise CommandError("No hay médicos. Corré seed_data primero.")

        hoy = timezone.localdate()
        creadas = 0
        with transaction.atomic():
            for i in range(1, count + 1):
                dni = f"{DNI_PREFIX}{i:06d}"
                pac, _ = Paciente.objects.update_or_create(
                    dni=dni,
                    defaults={
                        "nombre": f"CARGA{i:03d}",
                        "apellido": "SEEDLISTADO",
                        "sexo": "M" if i % 2 else "F",
                        "fecha_nacimiento": date(1980, 1, 1) + timedelta(days=i % 3650),
                        "obra_social": "OSDE",
                        "numero_afiliado": f"AF-{dni}",
                        "observaciones": MARKER,
                    },
                )
                # Evitar colisión si ya había orden activa mismo material/día.
                SolicitudExamen.objects.filter(
                    paciente=pac,
                    fecha_programada_toma=hoy,
                    material_pedido="SANGRE",
                ).exclude(estado__in=("FINALIZADO", "CANCELADO")).update(
                    estado="CANCELADO",
                    observaciones=f"{MARKER} (cancelada al reseed)",
                )

                sol = SolicitudExamen(
                    paciente=pac,
                    medico_interno=medico,
                    origen_solicitud="AMBULATORIO_CEHTA",
                    estado="PENDIENTE",
                    material_pedido="SANGRE",
                    fecha_programada_toma=hoy,
                    fecha_solicitud=timezone.now(),
                    observaciones=MARKER,
                    obra_social_orden="OSDE",
                    afiliado_orden=f"AF-{dni}",
                    estado_obra_social="AUTORIZADO",
                )
                sol.save()  # asigna LAB-YYYY-XXXXX
                sol.tipos_examen.set(tipos)
                for te in tipos:
                    ResultadoExamen.objects.get_or_create(
                        solicitud=sol,
                        tipo_examen=te,
                        defaults={
                            "valor_obtenido": "",
                            "es_patologico": False,
                        },
                    )
                creadas += 1
                if i % 25 == 0:
                    self.stdout.write(f"  … {i}/{count}")

        self.stdout.write(
            self.style.SUCCESS(
                f"OK: {creadas} órdenes PENDIENTE rutina ({len(tipos)} analitos) "
                f"fecha_programada_toma={hoy}. Marker={MARKER}."
            )
        )
        if options["en_proceso"]:
            n = self._pasar_en_proceso()
            self.stdout.write(self.style.SUCCESS(f"Además: {n} → EN_PROCESO (muestra hoy)."))
        else:
            self.stdout.write(
                "Probar pendientes: Laboratorio → Pendientes (Sin etiquetas). "
                "Para Órdenes del día: seed_carga_listado_ordenes --en-proceso. "
                "Borrar: --purge-only"
            )

    def _pasar_en_proceso(self) -> int:
        """Crea tubo con fecha_toma=hoy y deja la orden en EN_PROCESO."""
        qs = (
            SolicitudExamen.objects.filter(observaciones__icontains=MARKER)
            .exclude(estado__in=("FINALIZADO", "CANCELADO"))
            .select_related("paciente")
            .prefetch_related("tipos_examen__tipo_muestra_requerida", "tipos_examen__tipo_contenedor")
            .order_by("id")
        )
        now = timezone.now()
        hoy = timezone.localdate()
        n = 0
        with transaction.atomic():
            for sol in qs:
                if sol.estado == "EN_PROCESO" and sol.muestras.filter(
                    fecha_toma__date=hoy
                ).exists():
                    n += 1
                    continue

                te = next(
                    (
                        t
                        for t in sol.tipos_examen.all()
                        if t.tipo_muestra_requerida_id
                    ),
                    None,
                )
                if te is None:
                    raise CommandError(
                        f"Orden {sol.numero} sin tipo_muestra en exámenes; no se puede crear tubo."
                    )
                tm = te.tipo_muestra_requerida
                tc = te.tipo_contenedor

                # Un tubo seed por orden (idempotente si ya hay).
                muestra = sol.muestras.filter(observaciones=MARKER).first()
                if muestra is None:
                    muestra = Muestra(
                        solicitud=sol,
                        paciente=sol.paciente,
                        tipo_muestra=tm,
                        tipo_contenedor=tc,
                        estado="EN_PROCESO",
                        fecha_toma=now,
                        fecha_recepcion=now,
                        ubicacion_actual="SEED-BANCO",
                        observaciones=MARKER,
                    )
                    muestra.save()
                else:
                    muestra.estado = "EN_PROCESO"
                    muestra.fecha_toma = now
                    muestra.fecha_recepcion = now
                    muestra.ubicacion_actual = "SEED-BANCO"
                    muestra.save(
                        update_fields=[
                            "estado",
                            "fecha_toma",
                            "fecha_recepcion",
                            "ubicacion_actual",
                            "updated_at",
                        ]
                    )

                ResultadoExamen.objects.filter(solicitud=sol, muestra__isnull=True).update(
                    muestra=muestra
                )
                if sol.estado != "EN_PROCESO":
                    SolicitudExamen.objects.filter(pk=sol.pk).update(estado="EN_PROCESO")
                n += 1
                if n % 25 == 0:
                    self.stdout.write(f"  … en proceso {n}")
        return n

    def _purge(self) -> int:
        qs = SolicitudExamen.objects.filter(observaciones__icontains=MARKER)
        n = qs.count()
        qs.delete()
        Paciente.objects.filter(dni__startswith=DNI_PREFIX, observaciones=MARKER).delete()
        return n

