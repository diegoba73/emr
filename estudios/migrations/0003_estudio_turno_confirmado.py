from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("turnos", "0001_initial"),
        ("estudios", "0002_hardening_informes_estudio"),
    ]

    operations = [
        migrations.AddField(
            model_name="estudiocomplementario",
            name="turno",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="estudio_complementario",
                to="turnos.turno",
            ),
        ),
        migrations.AlterField(
            model_name="estudiocomplementario",
            name="estado",
            field=models.CharField(
                choices=[
                    ("SOLICITADO", "Solicitado"),
                    ("CONFIRMADO", "Confirmado"),
                    ("REALIZADO", "Realizado"),
                    ("INFORMADO", "Informado"),
                    ("VALIDADO", "Validado"),
                    ("ENTREGADO", "Entregado"),
                    ("ANULADO", "Anulado"),
                ],
                db_index=True,
                default="SOLICITADO",
                max_length=20,
            ),
        ),
    ]
