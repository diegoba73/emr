"""
Repara orina fantasma por expansión de paneles (solo las órdenes listadas).

Por defecto dry-run. Excluye LAB-2026-00119.

Uso:
  docker exec emr_backend_server python manage.py reparar_orina_fantasma_expansion
  docker exec emr_backend_server python manage.py reparar_orina_fantasma_expansion --apply
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from laboratorio.reparar_orina_fantasma import (
    aplicar_plan,
    numeros_default_reparacion,
    planificar_por_numeros,
)


class Command(BaseCommand):
    help = (
        "Quita prácticas de orina fantasma sin resultado/muestra/validación "
        "(dry-run por defecto; no incluye LAB-2026-00119)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--numeros",
            nargs="+",
            default=None,
            help="Protocolos a reparar (default: 6 órdenes sin 00119).",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Persiste los borrados. Sin este flag solo muestra el plan.",
        )

    def handle(self, *args, **options):
        numeros = options["numeros"] or list(numeros_default_reparacion())
        apply = bool(options["apply"])

        if "LAB-2026-00119" in numeros:
            self.stdout.write(
                self.style.ERROR(
                    "LAB-2026-00119 está excluida a propósito. Sacala de --numeros."
                )
            )
            return

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "Reparar orina fantasma "
                + ("(APPLY)" if apply else "(dry-run, no escribe)")
            )
        )
        self.stdout.write(f"Órdenes: {', '.join(numeros)}")
        self.stdout.write(
            "Solo borra códigos de orina/clearance sin valor clínico, "
            "sin muestra y sin validar. Conserva cualquier resultado real.\n"
        )

        planes = planificar_por_numeros(numeros)
        total_borrar = 0
        total_conservar = 0

        for plan in planes:
            if plan.estado == "NO_ENCONTRADA":
                self.stdout.write(
                    self.style.ERROR(f"\n=== {plan.numero}: NO ENCONTRADA ===")
                )
                continue

            borrar = plan.a_borrar
            conservar = [
                a
                for a in plan.acciones
                if a.accion
                in {"conservar_resultado", "conservar_validado", "conservar_muestra"}
            ]
            total_borrar += len(borrar)
            total_conservar += len(conservar)

            self.stdout.write(
                f"\n=== {plan.numero} (id={plan.id}) estado={plan.estado} ==="
            )
            if borrar:
                self.stdout.write(self.style.WARNING(f"  A borrar ({len(borrar)}):"))
                for a in borrar:
                    valor_txt = repr(a.valor) if a.valor else "''"
                    self.stdout.write(
                        f"    - {a.codigo} id={a.resultado_id} valor={valor_txt}"
                    )
            else:
                self.stdout.write("  A borrar: (ninguno)")

            if plan.tipos_a_quitar:
                self.stdout.write(
                    f"  Desvincular tipos_examen: {', '.join(plan.tipos_a_quitar)}"
                )

            if conservar:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  Conservar orina con resultado/muestra/validación ({len(conservar)}):"
                    )
                )
                for a in conservar:
                    self.stdout.write(
                        f"    ! {a.codigo} id={a.resultado_id} "
                        f"[{a.accion}] valor={repr(a.valor)} — {a.detalle}"
                    )

        self.stdout.write(self.style.MIGRATE_HEADING("\nResumen plan"))
        self.stdout.write(f"  Filas a borrar: {total_borrar}")
        self.stdout.write(f"  Filas orina conservadas: {total_conservar}")

        if not apply:
            self.stdout.write(
                self.style.NOTICE(
                    "\nDry-run OK. Si el plan es correcto, repetí con --apply."
                )
            )
            return

        if total_borrar == 0:
            self.stdout.write(self.style.SUCCESS("Nada para aplicar."))
            return

        stats = aplicar_plan(planes)
        self.stdout.write(self.style.SUCCESS("\nAplicado:"))
        for k, v in stats.items():
            self.stdout.write(f"  {k}: {v}")
