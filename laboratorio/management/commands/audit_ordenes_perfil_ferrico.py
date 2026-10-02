"""
Solo lectura: detecta órdenes con perfil férrico o analitos relacionados.

Uso:
    python manage.py audit_ordenes_perfil_ferrico
    python manage.py audit_ordenes_perfil_ferrico --listar
    python manage.py audit_ordenes_perfil_ferrico --solo-abiertas --listar
    docker exec -it emr_backend python manage.py audit_ordenes_perfil_ferrico --listar
"""
from __future__ import annotations

from collections import Counter

from django.core.management.base import BaseCommand
from django.db.models import Count, Q

from laboratorio.models import ResultadoExamen, SolicitudExamen

PANEL_FERR = "PAN_FERR"
CODIGOS_FERRICO = ("FERR", "UIBC", "FERRIT", "CF", "SAT_FE", "TRANS")


class Command(BaseCommand):
    help = (
        "Audita (solo lectura) órdenes con PAN_FERR o analitos férricos "
        f"({', '.join(CODIGOS_FERRICO)})."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--listar",
            action="store_true",
            help="Lista órdenes (id, número, estado, códigos presentes).",
        )
        parser.add_argument(
            "--solo-abiertas",
            action="store_true",
            help="Excluye FINALIZADO.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=50,
            help="Máximo de filas al listar (default 50).",
        )

    def handle(self, *args, **options):
        listar = options["listar"]
        solo_abiertas = options["solo_abiertas"]
        limit = max(1, int(options["limit"]))

        qs = SolicitudExamen.objects.all()
        if solo_abiertas:
            qs = qs.exclude(estado="FINALIZADO")

        con_panel = qs.filter(paneles__codigo=PANEL_FERR).distinct()
        con_tipo = qs.filter(tipos_examen__codigo__in=CODIGOS_FERRICO).distinct()
        con_resultado = qs.filter(
            resultados__tipo_examen__codigo__in=CODIGOS_FERRICO
        ).distinct()

        union_ids = set(con_panel.values_list("pk", flat=True)) | set(
            con_tipo.values_list("pk", flat=True)
        ) | set(con_resultado.values_list("pk", flat=True))

        self.stdout.write(self.style.MIGRATE_HEADING("Auditoría perfil férrico (solo lectura)"))
        if solo_abiertas:
            self.stdout.write("Filtro: solo órdenes no FINALIZADO")
        self.stdout.write(f"  Con panel {PANEL_FERR}:     {con_panel.count()}")
        self.stdout.write(f"  Con tipo en pedido:         {con_tipo.count()}")
        self.stdout.write(f"  Con resultado férrico:      {con_resultado.count()}")
        self.stdout.write(f"  Órdenes únicas (unión):     {len(union_ids)}")

        # Conteos por código en resultados
        por_codigo = (
            ResultadoExamen.objects.filter(tipo_examen__codigo__in=CODIGOS_FERRICO)
            .values("tipo_examen__codigo")
            .annotate(n=Count("id"))
            .order_by("tipo_examen__codigo")
        )
        if solo_abiertas:
            por_codigo = por_codigo.exclude(solicitud__estado="FINALIZADO")

        self.stdout.write("\nResultados por código:")
        if not por_codigo:
            self.stdout.write("  (ninguno)")
        else:
            for row in por_codigo:
                self.stdout.write(f"  {row['tipo_examen__codigo']}: {row['n']}")

        # Órdenes con panel/analitos pero sin UIBC (relevante post-cambio)
        sin_uibc = (
            qs.filter(
                Q(paneles__codigo=PANEL_FERR)
                | Q(tipos_examen__codigo__in=CODIGOS_FERRICO)
                | Q(resultados__tipo_examen__codigo__in=CODIGOS_FERRICO)
            )
            .exclude(
                Q(tipos_examen__codigo="UIBC") | Q(resultados__tipo_examen__codigo="UIBC")
            )
            .distinct()
        )
        self.stdout.write(
            f"\nÓrdenes con férrico y SIN UIBC (pedido ni resultado): {sin_uibc.count()}"
        )

        if not union_ids:
            self.stdout.write(self.style.SUCCESS("\nNo hay órdenes con perfil/analitos férricos."))
            return

        por_estado = Counter(
            SolicitudExamen.objects.filter(pk__in=union_ids).values_list("estado", flat=True)
        )
        self.stdout.write("\nPor estado (unión):")
        for estado, n in sorted(por_estado.items()):
            self.stdout.write(f"  {estado}: {n}")

        if not listar:
            self.stdout.write(
                self.style.NOTICE("\nTip: agregá --listar para ver id/número/códigos.")
            )
            return

        self.stdout.write(f"\nListado (hasta {limit}):")
        ordenes = (
            SolicitudExamen.objects.filter(pk__in=union_ids)
            .prefetch_related("paneles", "tipos_examen", "resultados__tipo_examen")
            .order_by("-id")[:limit]
        )
        for sol in ordenes:
            paneles = sorted({p.codigo for p in sol.paneles.all() if p.codigo})
            codigos_tipo = sorted(
                {
                    te.codigo
                    for te in sol.tipos_examen.all()
                    if te.codigo in CODIGOS_FERRICO
                }
            )
            codigos_res = sorted(
                {
                    r.tipo_examen.codigo
                    for r in sol.resultados.all()
                    if r.tipo_examen_id and r.tipo_examen.codigo in CODIGOS_FERRICO
                }
            )
            tiene_panel = PANEL_FERR in paneles
            self.stdout.write(
                f"  id={sol.pk} numero={sol.numero or '—'} estado={sol.estado} "
                f"panel_ferr={'sí' if tiene_panel else 'no'} "
                f"tipos=[{', '.join(codigos_tipo) or '—'}] "
                f"resultados=[{', '.join(codigos_res) or '—'}]"
            )
        if len(union_ids) > limit:
            self.stdout.write(f"  … y {len(union_ids) - limit} más (subí --limit).")
