"""Alta de tubo CITRATO_VSG y realineación VSG + química de rutina."""

from django.db import migrations

from laboratorio.tubos_catalogo import CONTENEDORES_TODOS, MUESTRA_CANONICA_POR_ANALITO, tubo_codigo_para_examen

_DEFAULTS_MUESTRA = {
    "SANGRE_EDTA": ("Sangre EDTA", "Morado"),
    "PLASMA_CITRATO": ("Plasma citrato", "Celeste"),
    "SANGRE_CITRATO_VSG": ("Sangre citrato VSG", "Negro"),
    "SANGRE_HEPARINA": ("Sangre heparina", "Verde"),
    "PLASMA_HEPARINA": ("Plasma heparina", "Verde"),
}


def alinear_vsg_y_quimica(apps, schema_editor):
    TipoExamen = apps.get_model("laboratorio", "TipoExamen")
    TipoContenedor = apps.get_model("laboratorio", "TipoContenedor")
    TipoMuestra = apps.get_model("laboratorio", "TipoMuestra")

    for codigo, nombre, color, aditivo in CONTENEDORES_TODOS:
        TipoContenedor.objects.get_or_create(
            codigo=codigo,
            defaults={
                "nombre": nombre,
                "color": color,
                "aditivo": aditivo,
                "activo": True,
                "descripcion": "",
            },
        )
    # Actualizar metadatos del citrato coagulación / VSG si ya existían
    TipoContenedor.objects.filter(codigo="CITRATO").update(
        nombre="Tubo Citrato coagulación",
        color="Celeste",
        aditivo="Citrato de sodio",
    )
    TipoContenedor.objects.filter(codigo="CITRATO_VSG").update(
        nombre="Tubo Citrato VSG",
        color="Negro",
        aditivo="Citrato de sodio trisódico 3,8%",
        activo=True,
    )

    muestras = {}
    for codigo, (nombre, color) in _DEFAULTS_MUESTRA.items():
        tm, _ = TipoMuestra.objects.get_or_create(
            codigo=codigo,
            defaults={"nombre": nombre, "color_tubo": color, "activo": True},
        )
        if not tm.activo:
            tm.activo = True
            tm.save(update_fields=["activo"])
        muestras[codigo] = tm

    tubos = {tc.codigo: tc for tc in TipoContenedor.objects.filter(activo=True)}

    for codigo, muestra_codigo in MUESTRA_CANONICA_POR_ANALITO.items():
        tubo_codigo = tubo_codigo_para_examen(codigo, muestra_codigo)
        tc = tubos.get(tubo_codigo)
        tm = muestras.get(muestra_codigo)
        if tc is None or tm is None:
            continue
        TipoExamen.objects.filter(codigo=codigo).update(
            tipo_contenedor_id=tc.pk,
            tipo_muestra_requerida_id=tm.pk,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0030_tipomuestra_codigo_largo"),
    ]

    operations = [
        migrations.RunPython(alinear_vsg_y_quimica, migrations.RunPython.noop),
    ]
