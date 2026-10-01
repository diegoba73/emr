# Generated manually for fecha_programada_toma (extracción programada).

from django.db import migrations, models
import django.utils.timezone


def backfill_fecha_programada_toma(apps, schema_editor):
    SolicitudExamen = apps.get_model("laboratorio", "SolicitudExamen")
    EstudioMicrobiologia = apps.get_model("laboratorio", "EstudioMicrobiologia")
    for sol in SolicitudExamen.objects.filter(fecha_programada_toma__isnull=True).iterator():
        dt = sol.fecha_solicitud
        if dt is not None:
            local = django.utils.timezone.localtime(dt) if django.utils.timezone.is_aware(dt) else dt
            sol.fecha_programada_toma = local.date()
        else:
            sol.fecha_programada_toma = django.utils.timezone.localdate()
        sol.save(update_fields=["fecha_programada_toma"])
    for est in EstudioMicrobiologia.objects.filter(fecha_programada_toma__isnull=True).iterator():
        dt = est.created_at
        if dt is not None:
            local = django.utils.timezone.localtime(dt) if django.utils.timezone.is_aware(dt) else dt
            est.fecha_programada_toma = local.date()
        else:
            est.fecha_programada_toma = django.utils.timezone.localdate()
        est.save(update_fields=["fecha_programada_toma"])


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0055_lectura_recuento_bacteriano"),
    ]

    operations = [
        migrations.AddField(
            model_name="solicitudexamen",
            name="fecha_programada_toma",
            field=models.DateField(
                db_index=True,
                null=True,
                verbose_name="Fecha programada de toma",
                help_text="Día en que se debe realizar la extracción de la muestra.",
            ),
        ),
        migrations.AddField(
            model_name="estudiomicrobiologia",
            name="fecha_programada_toma",
            field=models.DateField(
                db_index=True,
                null=True,
                verbose_name="Fecha programada de toma",
                help_text="Día en que se debe realizar la extracción/recepción de la muestra.",
            ),
        ),
        migrations.RunPython(backfill_fecha_programada_toma, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="solicitudexamen",
            name="fecha_programada_toma",
            field=models.DateField(
                db_index=True,
                default=django.utils.timezone.localdate,
                help_text="Día en que se debe realizar la extracción de la muestra.",
                verbose_name="Fecha programada de toma",
            ),
        ),
        migrations.AlterField(
            model_name="estudiomicrobiologia",
            name="fecha_programada_toma",
            field=models.DateField(
                db_index=True,
                default=django.utils.timezone.localdate,
                help_text="Día en que se debe realizar la extracción/recepción de la muestra.",
                verbose_name="Fecha programada de toma",
            ),
        ),
        migrations.AddIndex(
            model_name="solicitudexamen",
            index=models.Index(
                fields=["estado", "fecha_programada_toma"],
                name="laboratorio_estado_fpt_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="estudiomicrobiologia",
            index=models.Index(
                fields=["estado", "fecha_programada_toma"],
                name="laboratorio_micro_fpt_idx",
            ),
        ),
    ]
