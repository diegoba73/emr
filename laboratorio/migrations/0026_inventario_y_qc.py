# Generated manually for inventario + QC modules

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("laboratorio", "0025_asignar_tubos_examenes"),
    ]

    operations = [
        migrations.CreateModel(
            name="InsumoLab",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(choices=[("REACTIVO", "Reactivo"), ("TUBO", "Tubo / contenedor"), ("MEDIO", "Medio de cultivo"), ("OTRO", "Otro")], default="OTRO", max_length=20)),
                ("nombre", models.CharField(max_length=200)),
                ("codigo", models.CharField(max_length=40, unique=True)),
                ("unidad", models.CharField(default="u", max_length=40)),
                ("stock_min", models.PositiveIntegerField(default=0)),
                ("activo", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("medio_cultivo", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="insumos", to="laboratorio.mediocultivo")),
                ("tipo_contenedor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="insumos", to="laboratorio.tipocontenedor")),
            ],
            options={
                "verbose_name": "Insumo de laboratorio",
                "verbose_name_plural": "Insumos de laboratorio",
                "ordering": ["codigo"],
            },
        ),
        migrations.CreateModel(
            name="LoteInsumo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("codigo_lote", models.CharField(max_length=80)),
                ("cantidad", models.PositiveIntegerField(default=0)),
                ("fecha_vencimiento", models.DateField(blank=True, null=True)),
                ("ubicacion", models.CharField(blank=True, default="", max_length=120)),
                ("activo", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("insumo", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lotes", to="laboratorio.insumolab")),
            ],
            options={
                "verbose_name": "Lote de insumo",
                "verbose_name_plural": "Lotes de insumos",
                "ordering": ["fecha_vencimiento", "id"],
                "unique_together": {("insumo", "codigo_lote")},
            },
        ),
        migrations.CreateModel(
            name="MovimientoStock",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(choices=[("INGRESO", "Ingreso"), ("EGRESO", "Egreso"), ("AJUSTE", "Ajuste"), ("DESCARTE", "Descarte")], max_length=20)),
                ("cantidad", models.PositiveIntegerField()),
                ("motivo", models.CharField(blank=True, default="", max_length=255)),
                ("muestra_id", models.IntegerField(blank=True, null=True)),
                ("siembra_id", models.IntegerField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("lote", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="movimientos", to="laboratorio.loteinsumo")),
                ("usuario", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="movimientos_stock_lab", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Movimiento de stock",
                "verbose_name_plural": "Movimientos de stock",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="EquipoAnalizador",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=200)),
                ("codigo", models.CharField(max_length=40, unique=True)),
                ("activo", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("area", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="equipos_qc", to="laboratorio.arealaboratorio")),
                ("seccion", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="equipos_qc", to="laboratorio.seccionlaboratorio")),
            ],
            options={"ordering": ["codigo"]},
        ),
        migrations.CreateModel(
            name="MaterialControl",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=200)),
                ("nivel", models.CharField(choices=[("N1", "Nivel 1"), ("N2", "Nivel 2"), ("N3", "Nivel 3")], default="N1", max_length=5)),
                ("media_target", models.DecimalField(decimal_places=4, max_digits=12)),
                ("de_target", models.DecimalField(decimal_places=4, max_digits=12)),
                ("activo", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tipo_examen", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="materiales_control", to="laboratorio.tipoexamen")),
            ],
            options={"ordering": ["tipo_examen_id", "nivel"]},
        ),
        migrations.CreateModel(
            name="LoteControl",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("codigo_lote", models.CharField(max_length=80)),
                ("vencimiento", models.DateField()),
                ("activo", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("material", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lotes", to="laboratorio.materialcontrol")),
            ],
            options={
                "ordering": ["-vencimiento"],
                "unique_together": {("material", "codigo_lote")},
            },
        ),
        migrations.CreateModel(
            name="CorridaQC",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fecha", models.DateTimeField()),
                ("estado", models.CharField(choices=[("PENDIENTE", "Pendiente"), ("ACEPTADA", "Aceptada"), ("RECHAZADA", "Rechazada")], default="PENDIENTE", max_length=20)),
                ("observaciones", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("equipo", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="corridas_qc", to="laboratorio.equipoanalizador")),
                ("lote_control", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="corridas", to="laboratorio.lotecontrol")),
                ("operador", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="corridas_qc", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-fecha"]},
        ),
        migrations.CreateModel(
            name="PuntoQC",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("valor", models.DecimalField(decimal_places=4, max_digits=14)),
                ("z_score", models.FloatField(blank=True, null=True)),
                ("reglas_disparadas", models.JSONField(blank=True, default=list)),
                ("fuera_control", models.BooleanField(default=False)),
                ("warning", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("corrida", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="puntos", to="laboratorio.corridaqc")),
            ],
            options={"ordering": ["id"]},
        ),
        migrations.CreateModel(
            name="Calibracion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fecha", models.DateField()),
                ("vigente_hasta", models.DateField()),
                ("observaciones", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("equipo", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="calibraciones", to="laboratorio.equipoanalizador")),
                ("realizada_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="calibraciones_qc", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-fecha"]},
        ),
    ]
