"""EAB arterial y venoso: muestras distintas (2 jeringas / 2 etiquetas)."""

from django.db import migrations


def alinear_eab_jeringas(apps, schema_editor):
    TipoExamen = apps.get_model("laboratorio", "TipoExamen")
    TipoContenedor = apps.get_model("laboratorio", "TipoContenedor")
    TipoMuestra = apps.get_model("laboratorio", "TipoMuestra")

    hep = TipoContenedor.objects.filter(codigo="HEPARINA", activo=True).first()
    if hep is None:
        return

    art, _ = TipoMuestra.objects.get_or_create(
        codigo="SANGRE_HEPARINA_ART",
        defaults={"nombre": "Sangre heparina arterial", "color_tubo": "Verde", "activo": True},
    )
    ven, _ = TipoMuestra.objects.get_or_create(
        codigo="SANGRE_HEPARINA_VEN",
        defaults={"nombre": "Sangre heparina venosa", "color_tubo": "Verde", "activo": True},
    )
    for tm in (art, ven):
        if not tm.activo:
            tm.activo = True
            tm.save(update_fields=["activo"])

    TipoExamen.objects.filter(codigo="EAB_ART").update(
        tipo_contenedor_id=hep.pk,
        tipo_muestra_requerida_id=art.pk,
    )
    TipoExamen.objects.filter(codigo="EAB_VEN").update(
        tipo_contenedor_id=hep.pk,
        tipo_muestra_requerida_id=ven.pk,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0032_bidon_orina_24h"),
    ]

    operations = [
        migrations.RunPython(alinear_eab_jeringas, migrations.RunPython.noop),
    ]
