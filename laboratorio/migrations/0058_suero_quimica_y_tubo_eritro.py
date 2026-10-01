"""Química rutina → SUERO; VSG → tubo ERITRO (distinto de CITRATO coagulación)."""

from django.db import migrations

from laboratorio.tubos_catalogo import (
    CONTENEDORES_TODOS,
    ERITRO,
    HEPARINA,
    MUESTRA_CANONICA_POR_ANALITO,
    MUESTRA_ERITRO,
    SUERO,
    _HEPARINA_GASES,
    _QUIMICA_RUTINA,
    tubo_codigo_para_examen,
)


def aplicar_suero_y_eritro(apps, schema_editor):
    TipoExamen = apps.get_model("laboratorio", "TipoExamen")
    TipoContenedor = apps.get_model("laboratorio", "TipoContenedor")
    TipoMuestra = apps.get_model("laboratorio", "TipoMuestra")
    Muestra = apps.get_model("laboratorio", "Muestra")

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

    eritro, _ = TipoContenedor.objects.get_or_create(
        codigo=ERITRO,
        defaults={
            "nombre": "Tubo Eritro (VSG)",
            "color": "Negro",
            "aditivo": "Citrato de sodio trisódico 3,8%",
            "activo": True,
            "descripcion": "",
        },
    )
    TipoContenedor.objects.filter(codigo=ERITRO).update(
        nombre="Tubo Eritro (VSG)",
        color="Negro",
        aditivo="Citrato de sodio trisódico 3,8%",
        activo=True,
    )
    eritro.refresh_from_db()

    legacy_vsg = TipoContenedor.objects.filter(codigo="CITRATO_VSG").exclude(pk=eritro.pk).first()
    if legacy_vsg is not None:
        TipoExamen.objects.filter(tipo_contenedor_id=legacy_vsg.pk).update(
            tipo_contenedor_id=eritro.pk
        )
        Muestra.objects.filter(tipo_contenedor_id=legacy_vsg.pk).update(
            tipo_contenedor_id=eritro.pk
        )
        legacy_vsg.activo = False
        legacy_vsg.nombre = "Tubo Citrato VSG (legacy → ERITRO)"
        legacy_vsg.save(update_fields=["activo", "nombre"])

    suero_tm, _ = TipoMuestra.objects.get_or_create(
        codigo=SUERO,
        defaults={"nombre": "Suero", "color_tubo": "Rojo", "activo": True},
    )
    if not suero_tm.activo or suero_tm.nombre.lower() != "suero":
        suero_tm.nombre = "Suero"
        suero_tm.color_tubo = suero_tm.color_tubo or "Rojo"
        suero_tm.activo = True
        suero_tm.save(update_fields=["nombre", "color_tubo", "activo"])

    eritro_tm, _ = TipoMuestra.objects.get_or_create(
        codigo=MUESTRA_ERITRO,
        defaults={"nombre": "Sangre eritro (VSG)", "color_tubo": "Negro", "activo": True},
    )
    if not eritro_tm.activo:
        eritro_tm.activo = True
        eritro_tm.save(update_fields=["activo"])

    legacy_muestra_vsg = TipoMuestra.objects.filter(codigo="SANGRE_CITRATO_VSG").first()
    if legacy_muestra_vsg is not None and legacy_muestra_vsg.pk != eritro_tm.pk:
        TipoExamen.objects.filter(tipo_muestra_requerida_id=legacy_muestra_vsg.pk).update(
            tipo_muestra_requerida_id=eritro_tm.pk
        )
        Muestra.objects.filter(tipo_muestra_id=legacy_muestra_vsg.pk).update(
            tipo_muestra_id=eritro_tm.pk
        )
        legacy_muestra_vsg.activo = False
        legacy_muestra_vsg.nombre = "Sangre citrato VSG (legacy → SANGRE_ERITRO)"
        legacy_muestra_vsg.save(update_fields=["activo", "nombre"])

    tubos = {tc.codigo: tc for tc in TipoContenedor.objects.filter(activo=True)}
    suero_tc = tubos.get(SUERO)
    hep_tc = tubos.get(HEPARINA)

    # Química de rutina: HEPARINA/PLASMA_HEPARINA → SUERO
    if suero_tc is not None:
        TipoExamen.objects.filter(codigo__in=_QUIMICA_RUTINA).update(
            tipo_contenedor_id=suero_tc.pk,
            tipo_muestra_requerida_id=suero_tm.pk,
        )
        plasma_hep = TipoMuestra.objects.filter(codigo="PLASMA_HEPARINA").first()
        if plasma_hep is not None and hep_tc is not None:
            # Solo exámenes de química que aún apunten a heparina + plasma
            TipoExamen.objects.filter(
                tipo_contenedor_id=hep_tc.pk,
                tipo_muestra_requerida_id=plasma_hep.pk,
            ).exclude(codigo__in=_HEPARINA_GASES).update(
                tipo_contenedor_id=suero_tc.pk,
                tipo_muestra_requerida_id=suero_tm.pk,
            )
            plasma_hep.activo = False
            plasma_hep.nombre = "Plasma heparina (legacy → SUERO)"
            plasma_hep.save(update_fields=["activo", "nombre"])

    # VSG → ERITRO + SANGRE_ERITRO
    TipoExamen.objects.filter(codigo="VSG").update(
        tipo_contenedor_id=eritro.pk,
        tipo_muestra_requerida_id=eritro_tm.pk,
    )

    # Realinear canónicos (incluye gases en HEPARINA)
    muestras = {}
    for codigo, muestra_codigo in MUESTRA_CANONICA_POR_ANALITO.items():
        if muestra_codigo not in muestras:
            tm = TipoMuestra.objects.filter(codigo=muestra_codigo).first()
            if tm is None:
                continue
            muestras[muestra_codigo] = tm
        tm = muestras[muestra_codigo]
        tubo_codigo = tubo_codigo_para_examen(codigo, muestra_codigo)
        tc = tubos.get(tubo_codigo)
        if tc is None:
            continue
        TipoExamen.objects.filter(codigo=codigo).update(
            tipo_contenedor_id=tc.pk,
            tipo_muestra_requerida_id=tm.pk,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0057_orden_por_numero"),
    ]

    operations = [
        migrations.RunPython(aplicar_suero_y_eritro, migrations.RunPython.noop),
    ]
