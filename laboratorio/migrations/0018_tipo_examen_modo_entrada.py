# Modo de entrada de resultados por TipoExamen (ticket analizador / fórmula %)

from decimal import Decimal

from django.db import migrations, models

from laboratorio.catalogo_entrada_default import ENTRADA_DEFAULTS_POR_CODIGO


def aplicar_entrada_hemograma(apps, schema_editor):
    TipoExamen = apps.get_model("laboratorio", "TipoExamen")
    for codigo, row in ENTRADA_DEFAULTS_POR_CODIGO.items():
        modo, dec, mult, fmt = row
        TipoExamen.objects.filter(codigo=codigo).update(
            modo_entrada=modo,
            ticket_decimales=dec,
            multiplicador_clinico=Decimal(mult),
            formato_informe_entrada=fmt,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0017_tipo_examen_metodo"),
    ]

    operations = [
        migrations.AddField(
            model_name="tipoexamen",
            name="formato_informe_entrada",
            field=models.CharField(
                blank=True,
                choices=[
                    ("decimal1", "Un decimal (ej. 7.3)"),
                    ("integer", "Entero directo (ej. 70)"),
                    ("absolute_int", "Entero absoluto (ej. 9300)"),
                    ("absolute_millions", "Millones (ej. 2.370.000)"),
                ],
                default="",
                max_length=32,
                verbose_name="Formato en informe (entrada ticket)",
            ),
        ),
        migrations.AddField(
            model_name="tipoexamen",
            name="modo_entrada",
            field=models.CharField(
                choices=[
                    ("ESTANDAR", "Estándar (texto o número)"),
                    ("TICKET_ENTERO", "Ticket analizador (entero sin decimal)"),
                    ("FORMULA_PORCENTAJE", "Fórmula leucocitaria (% directo, suma 100)"),
                ],
                default="ESTANDAR",
                help_text="Define cómo el operador tipea el valor en carga de resultados.",
                max_length=32,
                verbose_name="Modo de entrada de resultado",
            ),
        ),
        migrations.AddField(
            model_name="tipoexamen",
            name="multiplicador_clinico",
            field=models.DecimalField(
                decimal_places=6,
                default=1,
                help_text="Valor ticket × multiplicador = valor numérico en unidad del catálogo.",
                max_digits=16,
                verbose_name="Multiplicador clínico",
            ),
        ),
        migrations.AddField(
            model_name="tipoexamen",
            name="ticket_decimales",
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text="Solo TICKET_ENTERO: cuántos decimales omite el operador (9.3 → 93 = 1).",
                verbose_name="Decimales implícitos del ticket",
            ),
        ),
        migrations.RunPython(aplicar_entrada_hemograma, migrations.RunPython.noop),
    ]
