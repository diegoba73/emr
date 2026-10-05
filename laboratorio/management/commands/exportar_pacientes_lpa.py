"""
Exporta a Excel pacientes con al menos un resultado LPA (Lipoproteína A)
y todos los exámenes de laboratorio de esos pacientes.

No usa MedGemma: filtro determinístico por código de examen en BD.
Salida con PHI (DNI) — solo uso local/operativo; no versionar el archivo.
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils import timezone

from laboratorio.models import ResultadoExamen


CODIGO_LPA = "LPA"


def _fecha_analisis(resultado: ResultadoExamen) -> datetime | None:
    return resultado.fecha_validacion or getattr(resultado.solicitud, "fecha_solicitud", None)


def _fmt_fecha(dt: datetime | date | None) -> str:
    if dt is None:
        return ""
    if isinstance(dt, datetime):
        if timezone.is_aware(dt):
            dt = timezone.localtime(dt)
        return dt.strftime("%Y-%m-%d %H:%M")
    return dt.isoformat()


def pacientes_con_lpa_ids(
    *,
    desde: date | None = None,
    hasta: date | None = None,
    solo_con_valor: bool = True,
) -> set[int]:
    qs = ResultadoExamen.objects.filter(tipo_examen__codigo__iexact=CODIGO_LPA)
    if solo_con_valor:
        qs = qs.exclude(valor_obtenido="").exclude(valor_obtenido__isnull=True)
    if desde is not None:
        qs = qs.filter(
            Q(fecha_validacion__date__gte=desde)
            | Q(fecha_validacion__isnull=True, solicitud__fecha_solicitud__date__gte=desde)
        )
    if hasta is not None:
        qs = qs.filter(
            Q(fecha_validacion__date__lte=hasta)
            | Q(fecha_validacion__isnull=True, solicitud__fecha_solicitud__date__lte=hasta)
        )
    return set(qs.values_list("solicitud__paciente_id", flat=True).distinct())


def filas_export(
    paciente_ids: set[int],
    *,
    desde: date | None = None,
    hasta: date | None = None,
) -> tuple[list[dict], list[dict]]:
    """
    Returns (filas_todos_examenes, filas_solo_lpa).
    """
    if not paciente_ids:
        return [], []

    res_qs = (
        ResultadoExamen.objects.filter(solicitud__paciente_id__in=paciente_ids)
        .exclude(valor_obtenido="")
        .select_related("solicitud", "solicitud__paciente", "tipo_examen")
        .order_by(
            "solicitud__paciente__dni",
            "solicitud__fecha_solicitud",
            "tipo_examen__codigo",
        )
    )
    if desde is not None:
        res_qs = res_qs.filter(solicitud__fecha_solicitud__date__gte=desde)
    if hasta is not None:
        res_qs = res_qs.filter(solicitud__fecha_solicitud__date__lte=hasta)

    todos: list[dict] = []
    solo_lpa: list[dict] = []
    for r in res_qs.iterator(chunk_size=2000):
        pac = r.solicitud.paciente
        codigo = (r.tipo_examen.codigo or "").strip().upper()
        row = {
            "dni": pac.dni or "",
            "apellido": pac.apellido or "",
            "nombre": pac.nombre or "",
            "fecha_analisis": _fmt_fecha(_fecha_analisis(r)),
            "protocolo": r.solicitud.numero or "",
            "estado_orden": r.solicitud.estado or "",
            "codigo_examen": codigo,
            "nombre_examen": (r.tipo_examen.nombre or "").strip(),
            "valor": r.valor_obtenido or "",
            "unidad": r.unidad or "",
            "es_patologico": "si" if r.es_patologico else "no",
            "es_lpa": "si" if codigo == CODIGO_LPA else "no",
        }
        todos.append(row)
        if codigo == CODIGO_LPA:
            solo_lpa.append(row)
    return todos, solo_lpa


def escribir_xlsx(path: Path, todos: list[dict], solo_lpa: list[dict], meta: dict) -> None:
    try:
        import openpyxl
        from openpyxl.styles import Font
    except ImportError as exc:
        raise CommandError("Falta openpyxl. pip install openpyxl") from exc

    path.parent.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.Workbook()

    ws_meta = wb.active
    ws_meta.title = "resumen"
    ws_meta["A1"] = "Export pacientes con LPA + todos sus exámenes"
    ws_meta["A1"].font = Font(bold=True)
    ws_meta["A2"] = "Nota"
    ws_meta["B2"] = (
        "Filtro por código LPA en BD (no MedGemma). Contiene DNI — uso local."
    )
    row_i = 3
    for k, v in meta.items():
        ws_meta.cell(row=row_i, column=1, value=k)
        ws_meta.cell(row=row_i, column=2, value=v)
        row_i += 1

    headers = [
        "dni",
        "apellido",
        "nombre",
        "fecha_analisis",
        "protocolo",
        "estado_orden",
        "codigo_examen",
        "nombre_examen",
        "valor",
        "unidad",
        "es_patologico",
        "es_lpa",
    ]

    def _write_sheet(title: str, rows: list[dict]) -> None:
        ws = wb.create_sheet(title)
        for col, h in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col, value=h)
            cell.font = Font(bold=True)
        for i, row in enumerate(rows, start=2):
            for col, h in enumerate(headers, start=1):
                ws.cell(row=i, column=col, value=row.get(h, ""))

    _write_sheet("todos_examenes", todos)
    _write_sheet("solo_lpa", solo_lpa)
    wb.save(path)


class Command(BaseCommand):
    help = (
        "Excel: pacientes con resultado LPA y todos sus exámenes (DNI + fecha). "
        "No usa MedGemma."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default="",
            help="Ruta .xlsx (default: reportes/export_pacientes_lpa_<fecha>.xlsx)",
        )
        parser.add_argument("--desde", default="", help="YYYY-MM-DD (fecha orden)")
        parser.add_argument("--hasta", default="", help="YYYY-MM-DD (fecha orden)")
        parser.add_argument(
            "--incluir-lpa-vacio",
            action="store_true",
            help="Incluye pedidos LPA sin valor cargado al definir el set de pacientes",
        )

    def handle(self, *args, **options):
        desde = date.fromisoformat(options["desde"]) if options["desde"] else None
        hasta = date.fromisoformat(options["hasta"]) if options["hasta"] else None
        out = options["output"].strip()
        if not out:
            stamp = timezone.localtime().strftime("%Y%m%d_%H%M")
            out = f"reportes/export_pacientes_lpa_{stamp}.xlsx"
        path = Path(out).expanduser().resolve()

        ids = pacientes_con_lpa_ids(
            desde=desde,
            hasta=hasta,
            solo_con_valor=not options["incluir_lpa_vacio"],
        )
        todos, solo_lpa = filas_export(ids, desde=desde, hasta=hasta)
        dnis = {r["dni"] for r in todos if r["dni"]}

        meta = {
            "generado": _fmt_fecha(timezone.now()),
            "codigo_filtro": CODIGO_LPA,
            "desde": desde.isoformat() if desde else "(sin piso)",
            "hasta": hasta.isoformat() if hasta else "(sin techo)",
            "pacientes": len(ids),
            "dnis_distintos": len(dnis),
            "filas_todos_examenes": len(todos),
            "filas_solo_lpa": len(solo_lpa),
        }
        escribir_xlsx(path, todos, solo_lpa, meta)

        self.stdout.write(self.style.SUCCESS(f"Escrito: {path}"))
        for k, v in meta.items():
            self.stdout.write(f"  {k}: {v}")
