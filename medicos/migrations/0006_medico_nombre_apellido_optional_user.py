from django.db import migrations, models
import django.conf


def populate_nombre_apellido(apps, schema_editor):
    Medico = apps.get_model("medicos", "Medico")
    medicos = Medico.objects.select_related("user").all()
    for medico in medicos:
        updated_fields = []
        if medico.user:
            first_name = (medico.user.first_name or "").strip()
            last_name = (medico.user.last_name or "").strip()
            if first_name and not medico.nombre:
                medico.nombre = first_name
                updated_fields.append("nombre")
            if last_name and not medico.apellido:
                medico.apellido = last_name
                updated_fields.append("apellido")
        if updated_fields:
            if "ultima_actualizacion" not in updated_fields:
                updated_fields.append("ultima_actualizacion")
            medico.save(update_fields=updated_fields)


class Migration(migrations.Migration):

    dependencies = [
        ("medicos", "0005_disponibilidadmedico_excepcionmedico"),
        migrations.swappable_dependency(django.conf.settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="medico",
            name="apellido",
            field=models.CharField(
                blank=True,
                max_length=100,
                null=True,
                verbose_name="Apellido",
            ),
        ),
        migrations.AddField(
            model_name="medico",
            name="nombre",
            field=models.CharField(
                blank=True,
                max_length=100,
                null=True,
                verbose_name="Nombre",
            ),
        ),
        migrations.AlterField(
            model_name="medico",
            name="user",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=models.CASCADE,
                related_name="medico",
                to=django.conf.settings.AUTH_USER_MODEL,
                verbose_name="Usuario del Sistema",
            ),
        ),
        migrations.AlterModelOptions(
            name="medico",
            options={
                "ordering": [
                    "apellido",
                    "nombre",
                    "user__last_name",
                    "user__first_name",
                ],
                "verbose_name": "Médico",
                "verbose_name_plural": "Médicos",
            },
        ),
        migrations.RunPython(populate_nombre_apellido, migrations.RunPython.noop),
    ]

