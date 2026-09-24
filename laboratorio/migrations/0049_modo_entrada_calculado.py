# Modo CALCULADO + seed de parametros derivados (lipidico / bilirrubina)

from decimal import Decimal

from django.db import migrations, models

from laboratorio.catalogo_entrada_default import ENTRADA_DEFAULTS_POR_CODIGO


def aplicar_modo_calculado(apps, schema_editor):
    TipoExamen = apps.get_model("laboratorio", "TipoExamen")
    for codigo, row in ENTRADA_DEFAULTS_POR_CODIGO.items():
        modo, dec, mult, fmt = row
        if modo != "CALCULADO":
            continue
        TipoExamen.objects.filter(codigo=codigo).update(
            modo_entrada=modo,
            ticket_decimales=dec,
            multiplicador_clinico=Decimal(mult),
            formato_informe_entrada=fmt or "",
        )


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0048_diestro_a_erba_ec90"),
    ]

    operations = [
        migrations.AlterField(
            model_name="tipoexamen",
            name="modo_entrada",
            field=models.CharField(
                choices=[
                    ("ESTANDAR", "Estándar (texto o número)"),
                    ("TICKET_ENTERO", "Ticket analizador (entero sin decimal)"),
                    (
                        "FORMULA_PORCENTAJE",
                        "Fórmula leucocitaria (% directo, suma 100)",
                    ),
                    ("CALCULADO", "Calculado (no editable)"),
                ],
                default="ESTANDAR",
                help_text="Define cómo el operador tipea el valor en carga de resultados.",
                max_length=32,
                verbose_name="Modo de entrada de resultado",
            ),
        ),
        migrations.RunPython(aplicar_modo_calculado, migrations.RunPython.noop),
    ]
