"""Reemplaza el analizador Diestro por ERBA EC90 y el producto de control asociado."""

from django.db import migrations


NOMBRE_EC90 = "Analizador de electrolitos ERBA EC90"
MARCA_EC90 = "ERBA EC90"
NOMBRE_CTRL = "Control electrolitos ERBA EC90"


def _retirar_diestro(apps, schema_editor):
    EquipoAnalizador = apps.get_model("laboratorio", "EquipoAnalizador")
    TipoExamen = apps.get_model("laboratorio", "TipoExamen")
    ProductoControl = apps.get_model("laboratorio", "ProductoControl")
    MaterialControl = apps.get_model("laboratorio", "MaterialControl")
    CorridaQC = apps.get_model("laboratorio", "CorridaQC")
    Calibracion = apps.get_model("laboratorio", "Calibracion")

    diestro = EquipoAnalizador.objects.filter(codigo="DIESTRO").first()
    ec90 = EquipoAnalizador.objects.filter(codigo="ERBA_EC90").first()

    if diestro and not ec90:
        diestro.codigo = "ERBA_EC90"
        diestro.nombre = NOMBRE_EC90
        diestro.marca_modelo = MARCA_EC90
        diestro.activo = True
        diestro.save(update_fields=["codigo", "nombre", "marca_modelo", "activo", "updated_at"])
        ec90 = diestro
    elif diestro and ec90 and diestro.id != ec90.id:
        TipoExamen.objects.filter(equipo_analizador=diestro).update(equipo_analizador=ec90)
        ProductoControl.objects.filter(equipo=diestro).update(equipo=ec90)
        MaterialControl.objects.filter(equipo=diestro).update(equipo=ec90)
        CorridaQC.objects.filter(equipo=diestro).update(equipo=ec90)
        Calibracion.objects.filter(equipo=diestro).update(equipo=ec90)
        diestro.activo = False
        diestro.save(update_fields=["activo", "updated_at"])
    elif not ec90:
        ec90 = EquipoAnalizador.objects.create(
            codigo="ERBA_EC90",
            nombre=NOMBRE_EC90,
            marca_modelo=MARCA_EC90,
            activo=True,
        )
    else:
        updates = []
        if ec90.nombre != NOMBRE_EC90:
            ec90.nombre = NOMBRE_EC90
            updates.append("nombre")
        if ec90.marca_modelo != MARCA_EC90:
            ec90.marca_modelo = MARCA_EC90
            updates.append("marca_modelo")
        if not ec90.activo:
            ec90.activo = True
            updates.append("activo")
        if updates:
            ec90.save(update_fields=[*updates, "updated_at"])

    prod_old = ProductoControl.objects.filter(codigo="CTRL_DIESTRO").first()
    prod_new = ProductoControl.objects.filter(codigo="CTRL_ERBA_EC90").first()
    if prod_old and not prod_new:
        prod_old.codigo = "CTRL_ERBA_EC90"
        prod_old.nombre = NOMBRE_CTRL
        prod_old.marca = "ERBA"
        if ec90:
            prod_old.equipo = ec90
        prod_old.activo = True
        prod_old.save(update_fields=["codigo", "nombre", "marca", "equipo", "activo", "updated_at"])
    elif prod_old and prod_new and prod_old.id != prod_new.id:
        prod_old.activo = False
        prod_old.save(update_fields=["activo", "updated_at"])
        if ec90 and prod_new.equipo_id != ec90.id:
            prod_new.equipo = ec90
            prod_new.save(update_fields=["equipo", "updated_at"])


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0047_panelexamen_codigo_nbu"),
    ]

    operations = [
        migrations.RunPython(_retirar_diestro, migrations.RunPython.noop),
    ]
