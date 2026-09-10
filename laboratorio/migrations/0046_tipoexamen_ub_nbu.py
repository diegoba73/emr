from decimal import Decimal, InvalidOperation

from django.db import migrations, models


def _parse_ub(value):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value).strip().replace(",", "."))
    except (InvalidOperation, ValueError):
        return None


def backfill_ub_nbu(apps, schema_editor):
    """Completa U.B. de exámenes que ya tienen codigo_nbu, usando el CSV NBU."""
    from pathlib import Path
    import csv

    TipoExamen = apps.get_model("laboratorio", "TipoExamen")
    csv_path = Path(__file__).resolve().parents[1] / "data" / "nbu_2012.csv"
    if not csv_path.is_file():
        return
    ub_by_code = {}
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            code = (row.get("codigo_nbu") or "").strip()
            ub = _parse_ub(row.get("ub"))
            if code and ub is not None:
                ub_by_code[code] = ub
    for exam in TipoExamen.objects.exclude(codigo_nbu__isnull=True).exclude(codigo_nbu=""):
        ub = ub_by_code.get(exam.codigo_nbu)
        if ub is not None:
            exam.ub_nbu = ub
            exam.save(update_fields=["ub_nbu"])


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0045_tipoexamen_codigo_nbu"),
    ]

    operations = [
        migrations.AddField(
            model_name="tipoexamen",
            name="ub_nbu",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text=(
                    "Unidades bioquímicas del nomenclador para ese código NBU. "
                    "No confundir con la unidad analítica (mg/dL, g/L, etc.)."
                ),
                max_digits=8,
                null=True,
                verbose_name="U.B. (NBU)",
            ),
        ),
        migrations.RunPython(backfill_ub_nbu, migrations.RunPython.noop),
    ]
