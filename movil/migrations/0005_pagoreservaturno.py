from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pacientes', '0014_obrasocial_catalogo'),
        ('turnos', '0016_turno_requiere_aceptacion_paciente'),
        ('movil', '0004_recordatorio_tipo_estoy_en_sala'),
    ]

    operations = [
        migrations.CreateModel(
            name='PagoReservaTurno',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('CONSULTA', 'Pago de consulta (particular)'), ('GARANTIA_OS', 'Garantía de asistencia (obra social)')], max_length=20)),
                ('estado', models.CharField(choices=[('PENDIENTE', 'Pendiente'), ('PAGADO', 'Pagado'), ('ANULADO', 'Anulado')], db_index=True, default='PENDIENTE', max_length=15)),
                ('medio', models.CharField(blank=True, choices=[('MERCADOPAGO', 'Mercado Pago'), ('TRANSFERENCIA', 'Transferencia'), ('OTRO', 'Otro')], default='', max_length=20)),
                ('monto', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('referencia', models.CharField(blank=True, default='', max_length=120)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('paciente', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pagos_reserva_movil', to='pacientes.paciente')),
                ('turno', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pagos_reserva_movil', to='turnos.turno')),
            ],
            options={
                'verbose_name': 'Pago reserva turno (móvil)',
                'verbose_name_plural': 'Pagos reserva turno (móvil)',
                'ordering': ['-creado_en', '-id'],
            },
        ),
    ]
