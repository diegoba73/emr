# Panel PAN_CTOG: basal (GLU_0) + 120 min (GLU120). Desactiva CTOG/PTOG/GLU60 sueltos.

from decimal import Decimal

from django.db import migrations

from laboratorio.catalogo_entrada_default import entrada_defaults_dict
from laboratorio.catalogo_referencias_clinicas import REFERENCIAS_POR_CODIGO


def _aplicar_ref(te, codigo: str) -> None:
    ref = REFERENCIAS_POR_CODIGO.get(codigo) or {}
    update = {}
    if ref.get("metodo"):
        update["metodo"] = ref["metodo"]
    if ref.get("unidad_default"):
        update["unidad_default"] = ref["unidad_default"]
    if ref.get("rango_referencia_texto"):
        update["rango_referencia_texto"] = ref["rango_referencia_texto"]
    for field in ("rango_min", "rango_max", "valor_critico_min", "valor_critico_max"):
        if field in ref:
            update[field] = ref[field]
    update.update(entrada_defaults_dict(codigo))
    if update:
        for k, v in update.items():
            setattr(te, k, v)


def aplicar_ctog(apps, schema_editor):
    TipoExamen = apps.get_model("laboratorio", "TipoExamen")
    TipoMuestra = apps.get_model("laboratorio", "TipoMuestra")
    TipoContenedor = apps.get_model("laboratorio", "TipoContenedor")
    PanelExamen = apps.get_model("laboratorio", "PanelExamen")

    suero, _ = TipoMuestra.objects.get_or_create(
        codigo="SUERO",
        defaults={"nombre": "Suero", "color_tubo": "Rojo", "activo": True},
    )
    tubo = TipoContenedor.objects.filter(codigo="SUERO").first()

    componentes = []
    for codigo, nombre, abrev in (
        ("GLU_0", "Basal (0 min)", "Basal"),
        ("GLU120", "120 minutos", "120'"),
    ):
        te, _ = TipoExamen.objects.update_or_create(
            codigo=codigo,
            defaults={
                "nombre": nombre,
                "abreviatura": abrev,
                "tipo_muestra_requerida": suero,
                "tipo_contenedor": tubo,
                "tipo_resultado": "NUMERICO",
                "requiere_muestra": True,
                "activo": True,
                "precio": Decimal("0"),
            },
        )
        _aplicar_ref(te, codigo)
        te.tipo_muestra_requerida = suero
        te.tipo_contenedor = tubo
        te.nombre = nombre
        te.abreviatura = abrev
        te.tipo_resultado = "NUMERICO"
        te.requiere_muestra = True
        te.activo = True
        te.save()
        componentes.append(te)

    panel, _ = PanelExamen.objects.update_or_create(
        codigo="PAN_CTOG",
        defaults={
            "nombre": "Curva de tolerancia a la glucosa (CTOG)",
            "activo": True,
        },
    )
    panel.tipos_examen.set(componentes)

    TipoExamen.objects.filter(codigo__in=("CTOG", "PTOG", "GLU60"), activo=True).update(
        activo=False
    )


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0073_tfg_ckd_epi_calculado"),
    ]

    operations = [
        migrations.RunPython(aplicar_ctog, migrations.RunPython.noop),
    ]
