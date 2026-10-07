# Generated manually for PacienteAfiliacion + backfill from Paciente fields.

from django.db import migrations, models
import django.db.models.deletion


def backfill_afiliaciones(apps, schema_editor):
    Paciente = apps.get_model("pacientes", "Paciente")
    PacienteAfiliacion = apps.get_model("pacientes", "PacienteAfiliacion")
    for p in Paciente.objects.all().iterator():
        os_val = (p.obra_social or "").strip()
        if not os_val:
            continue
        if PacienteAfiliacion.objects.filter(paciente_id=p.pk, activo=True).exists():
            continue
        PacienteAfiliacion.objects.create(
            paciente_id=p.pk,
            obra_social=os_val.upper(),
            numero_afiliado=(p.numero_afiliado or "").strip().upper(),
            es_principal=True,
            activo=True,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("pacientes", "0011_paciente_estado_civil_familiar"),
    ]

    operations = [
        migrations.CreateModel(
            name="PacienteAfiliacion",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("obra_social", models.CharField(max_length=100, verbose_name="Obra Social")),
                (
                    "numero_afiliado",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=50,
                        verbose_name="Número de Afiliado",
                    ),
                ),
                ("es_principal", models.BooleanField(default=False, verbose_name="Principal")),
                ("activo", models.BooleanField(default=True, verbose_name="Activo")),
                ("creado_en", models.DateTimeField(auto_now_add=True, verbose_name="Creado en")),
                (
                    "actualizado_en",
                    models.DateTimeField(auto_now=True, verbose_name="Actualizado en"),
                ),
                (
                    "paciente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="afiliaciones",
                        to="pacientes.paciente",
                        verbose_name="Paciente",
                    ),
                ),
            ],
            options={
                "verbose_name": "Afiliación de paciente",
                "verbose_name_plural": "Afiliaciones de paciente",
                "ordering": ["-es_principal", "obra_social", "id"],
            },
        ),
        migrations.AddIndex(
            model_name="pacienteafiliacion",
            index=models.Index(
                fields=["paciente", "activo"], name="pac_afil_pac_act_idx"
            ),
        ),
        migrations.AddConstraint(
            model_name="pacienteafiliacion",
            constraint=models.UniqueConstraint(
                condition=models.Q(activo=True, es_principal=True),
                fields=("paciente",),
                name="pac_afil_una_principal_activa",
            ),
        ),
        migrations.RunPython(backfill_afiliaciones, migrations.RunPython.noop),
    ]
