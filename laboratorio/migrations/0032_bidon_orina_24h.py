"""Alta de bidón orina 24 hs y realineación de exámenes de recolección diaria."""

from django.db import migrations

from laboratorio.tubos_catalogo import (
    BIDON_ORINA_24H,
    CONTENEDORES_TODOS,
    MUESTRA_ORINA_24H,
    _ORINA_24H,
    es_muestra_orina_24h,
    tubo_codigo_para_examen,
)


def alinear_orina_24h(apps, schema_editor):
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
    TipoContenedor.objects.filter(codigo=BIDON_ORINA_24H).update(
        nombre="Bidón orina 24 hs",
        color="Ámbar",
        aditivo="Recolección 24 hs (sin aditivo / según protocolo)",
        activo=True,
    )

    orina_24, _ = TipoMuestra.objects.get_or_create(
        codigo=MUESTRA_ORINA_24H,
        defaults={"nombre": "Orina 24 hs", "color_tubo": "Ámbar", "activo": True},
    )
    if not orina_24.activo:
        orina_24.activo = True
        orina_24.save(update_fields=["activo"])

    bidon = TipoContenedor.objects.get(codigo=BIDON_ORINA_24H)
    for codigo in _ORINA_24H:
        TipoExamen.objects.filter(codigo=codigo).update(
            tipo_contenedor_id=bidon.pk,
            tipo_muestra_requerida_id=orina_24.pk,
        )

    # Materiales IACA con orina 24 hs → bidón (conserva su TipoMuestra)
    for ex in TipoExamen.objects.select_related("tipo_muestra_requerida").iterator():
        tm = ex.tipo_muestra_requerida
        if tm is None:
            continue
        if not es_muestra_orina_24h(tm.codigo, getattr(tm, "nombre", None)):
            continue
        tubo = tubo_codigo_para_examen(ex.codigo, tm.codigo, muestra_nombre=tm.nombre)
        if tubo != BIDON_ORINA_24H:
            continue
        if ex.tipo_contenedor_id != bidon.pk:
            TipoExamen.objects.filter(pk=ex.pk).update(tipo_contenedor_id=bidon.pk)


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0031_citrato_vsg_y_quimica_heparina"),
    ]

    operations = [
        migrations.RunPython(alinear_orina_24h, migrations.RunPython.noop),
    ]
