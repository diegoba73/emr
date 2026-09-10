from decimal import Decimal, InvalidOperation

from django.db import migrations, models


# Copia del mapa IACA → panel (no importar iaca_compat: la migración debe ser estable).
# Orden: primero la práctica NBU canónica del perfil operativo.
IACA_PRODUCTO_A_PANEL = [
    ("HEM", "PAN_HEMO"),
    ("COA", "PAN_COAG"),
    ("IONO", "PAN_IONO"),
    ("IONOO", "PAN_IONO_U"),
    ("IONO24", "PAN_IONO_U24"),
    ("HEPATO", "PAN_HEP"),
    ("OC", "PAN_ORI"),
    ("PLIPI", "PAN_LIP"),
    ("PEL", "PAN_ELP"),
    ("CREAC24", "PAN_CLEAR"),
    ("EABA", "PAN_EAB_ART"),
    ("EABV", "PAN_EAB_VEN"),
    # Aliases IACA: solo si el panel todavía no tiene NBU.
    ("IONOL", "PAN_IONO_U"),
    ("LIPIE", "PAN_LIP"),
    ("PELLCR", "PAN_ELP"),
]

# Perfiles sin producto IACA 1:1 (EAB arterial/venoso = misma práctica NBU).
NBU_PANEL_EXTRA = {
    "PAN_EAB_ART": "660005",
    "PAN_EAB_VEN": "660005",
}


def _parse_ub(value):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value).strip().replace(",", "."))
    except (InvalidOperation, ValueError):
        return None


def _ub_from_csv():
    from pathlib import Path
    import csv

    csv_path = Path(__file__).resolve().parents[1] / "data" / "nbu_2012.csv"
    if not csv_path.is_file():
        return {}
    ub_by_code = {}
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            code = (row.get("codigo_nbu") or "").strip()
            ub = _parse_ub(row.get("ub"))
            if code and ub is not None:
                ub_by_code[code] = ub
    return ub_by_code


def backfill_panel_nbu(apps, schema_editor):
    TipoExamen = apps.get_model("laboratorio", "TipoExamen")
    PanelExamen = apps.get_model("laboratorio", "PanelExamen")
    ub_by_code = _ub_from_csv()

    for iaca_codigo, panel_codigo in IACA_PRODUCTO_A_PANEL:
        panel = PanelExamen.objects.filter(codigo=panel_codigo).first()
        if not panel or panel.codigo_nbu:
            continue
        exam = TipoExamen.objects.filter(codigo=iaca_codigo).exclude(
            codigo_nbu__isnull=True
        ).exclude(codigo_nbu="").first()
        if not exam:
            continue
        panel.codigo_nbu = exam.codigo_nbu
        panel.ub_nbu = exam.ub_nbu if exam.ub_nbu is not None else ub_by_code.get(exam.codigo_nbu)
        panel.save(update_fields=["codigo_nbu", "ub_nbu"])

    for panel_codigo, nbu in NBU_PANEL_EXTRA.items():
        panel = PanelExamen.objects.filter(codigo=panel_codigo).first()
        if not panel or panel.codigo_nbu:
            continue
        panel.codigo_nbu = nbu
        panel.ub_nbu = ub_by_code.get(nbu)
        panel.save(update_fields=["codigo_nbu", "ub_nbu"])


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0046_tipoexamen_ub_nbu"),
    ]

    operations = [
        migrations.AddField(
            model_name="panelexamen",
            name="codigo_nbu",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text=(
                    "Código CUBRA del perfil (p. ej. Hemograma 660475, Ionograma sérico 660546). "
                    "Distinto del código interno PAN_*."
                ),
                max_length=20,
                null=True,
                verbose_name="Código NBU",
            ),
        ),
        migrations.AddField(
            model_name="panelexamen",
            name="ub_nbu",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text=(
                    "Unidades bioquímicas del nomenclador para el perfil. "
                    "No confundir con la unidad analítica de cada componente."
                ),
                max_digits=8,
                null=True,
                verbose_name="U.B. (NBU)",
            ),
        ),
        migrations.RunPython(backfill_panel_nbu, migrations.RunPython.noop),
    ]
