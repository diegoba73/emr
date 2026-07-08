"""Estados de SolicitudExamen: PENDIENTE, EN_PROCESO, FINALIZADO."""

from django.db import migrations, models


def migrar_estados_solicitud(apps, schema_editor):
    SolicitudExamen = apps.get_model("laboratorio", "SolicitudExamen")
    SolicitudExamen.objects.filter(estado="TOMA_MUESTRA").update(estado="EN_PROCESO")
    SolicitudExamen.objects.filter(estado__in=["VALIDADO", "ENTREGADO", "CANCELADO"]).update(
        estado="FINALIZADO"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0013_solicitudexamen_consulta_hc"),
    ]

    operations = [
        migrations.RunPython(migrar_estados_solicitud, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="solicitudexamen",
            name="estado",
            field=models.CharField(
                choices=[
                    ("PENDIENTE", "Pendiente"),
                    ("EN_PROCESO", "En Proceso"),
                    ("FINALIZADO", "Finalizado"),
                ],
                default="PENDIENTE",
                max_length=20,
                verbose_name="Estado",
            ),
        ),
    ]
