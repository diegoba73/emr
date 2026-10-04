# Orinas 24 hs: PROT_U_24, NA/K/CL_U24, MICROALB_24 → modo CALCULADO
# (complementa seed_catalogo_solicitud_papel en bases ya sembradas)

from decimal import Decimal

from django.db import migrations

from laboratorio.catalogo_entrada_default import ENTRADA_DEFAULTS_POR_CODIGO

_CODIGOS = ("PROT_U_24", "NA_U24", "K_U24", "CL_U24", "MICROALB_24")


def aplicar_orinas_24h_calculado(apps, schema_editor):
    TipoExamen = apps.get_model("laboratorio", "TipoExamen")
    for codigo in _CODIGOS:
        row = ENTRADA_DEFAULTS_POR_CODIGO.get(codigo)
        if not row:
            continue
        modo, dec, mult, fmt = row
        TipoExamen.objects.filter(codigo=codigo).update(
            modo_entrada=modo,
            ticket_decimales=dec,
            multiplicador_clinico=Decimal(mult),
            formato_informe_entrada=fmt or "",
        )


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0061_hisopado_anal_tipo_cultivo"),
    ]

    operations = [
        migrations.RunPython(aplicar_orinas_24h_calculado, migrations.RunPython.noop),
    ]
