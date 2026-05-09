"""Rediseño de ``Turno`` + introducción de ``Recurso`` y ``Atencion``.

Esta migración originalmente eliminaba columnas legacy de ``Turno`` sin
preservar los datos. La versión actual conserva la información histórica
antes de eliminar las columnas:

- ``fecha_hora`` → ``fecha_hora_inicio`` (cuando ``fecha_hora_inicio`` es NULL).
- ``motivo_consulta`` → ``motivo_reserva`` (truncando a 255 caracteres).
- estados legacy → nuevos choices:
    * ``PENDIENTE``  → ``DISPONIBLE``
    * ``REAGENDADO`` → ``CANCELADO`` (con prefijo ``[REAGENDADO]`` en motivo)
    * resto → idéntico (``DISPONIBLE``, ``RESERVADO``, ``CONFIRMADO``,
      ``CANCELADO``, ``REALIZADO``).

El orden de operaciones es crítico:
1. ``CreateModel Atencion`` y ``CreateModel Recurso`` (sin tocar ``Turno``).
2. ``AlterModelOptions`` y ``AlterField`` para ampliar/relajar choices y
   nullability del ``Turno`` actual.
3. ``AddField`` de ``motivo_reserva`` (necesario para preservar texto).
4. ``RunPython`` que copia los datos legacy hacia los nuevos campos.
5. ``RemoveField`` destructivo recién después de la preservación.
6. Resto de modelos (``ConsultaAmbulatoria``, ``RegistroProcedimiento``,
   ``RegistroQuirurgico``) y ``AddField`` cruzados.

``RunPython.reverse_code`` queda como ``noop`` porque la operación es
unidireccional: una vez eliminadas las columnas legacy no es posible
reconstruirlas exactamente desde los nuevos campos.
"""

import django.db.models.deletion
from django.db import migrations, models


_LEGACY_TO_NEW_ESTADO = {
    "PENDIENTE": "DISPONIBLE",
    "REAGENDADO": "CANCELADO",
}


def _trunc(value, max_length):
    if value is None:
        return None
    text = str(value)
    if len(text) <= max_length:
        return text
    return text[: max_length - 1] + "…"


def migrate_legacy_turno_fields(apps, schema_editor):
    """Preserva ``fecha_hora``, ``motivo_consulta`` y estados legacy.

    Itera con ``.iterator()`` para no cargar toda la tabla en memoria. Solo
    actualiza filas donde haya algo realmente que migrar para minimizar el
    impacto sobre la base de datos.
    """
    Turno = apps.get_model("turnos", "Turno")

    qs = Turno.objects.all()
    for turno in qs.iterator():
        update_fields = []

        legacy_fecha = getattr(turno, "fecha_hora", None)
        if legacy_fecha is not None and turno.fecha_hora_inicio is None:
            turno.fecha_hora_inicio = legacy_fecha
            update_fields.append("fecha_hora_inicio")

        legacy_motivo = getattr(turno, "motivo_consulta", None)
        if legacy_motivo and not getattr(turno, "motivo_reserva", None):
            turno.motivo_reserva = _trunc(legacy_motivo, 255)
            update_fields.append("motivo_reserva")

        legacy_estado = getattr(turno, "estado", None)
        if legacy_estado in _LEGACY_TO_NEW_ESTADO:
            mapped = _LEGACY_TO_NEW_ESTADO[legacy_estado]
            if legacy_estado == "REAGENDADO":
                marker = "[REAGENDADO]"
                base = (turno.motivo_reserva or "").strip()
                combined = f"{marker} {base}".strip() if base else marker
                turno.motivo_reserva = _trunc(combined, 255)
                if "motivo_reserva" not in update_fields:
                    update_fields.append("motivo_reserva")
            turno.estado = mapped
            update_fields.append("estado")

        if update_fields:
            turno.save(update_fields=list(set(update_fields)))


def noop_reverse(apps, schema_editor):  # pragma: no cover - migración unidireccional
    """No reversible: las columnas legacy ya no existen tras el RemoveField."""
    return None


class Migration(migrations.Migration):

    dependencies = [
        ("medicos", "0006_medico_nombre_apellido_optional_user"),
        ("pacientes", "0008_alter_paciente_options_paciente_apellido_and_more"),
        ("turnos", "0004_turno_centro_fisico_turno_tipo_atencion"),
    ]

    operations = [
        # === Paso 1: nuevos modelos sin tocar Turno ====================
        migrations.CreateModel(
            name="Atencion",
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
                (
                    "fecha_admision",
                    models.DateTimeField(auto_now_add=True, db_index=True),
                ),
                ("fecha_cierre", models.DateTimeField(blank=True, null=True)),
                (
                    "tipo_atencion",
                    models.CharField(
                        choices=[
                            ("CONSULTORIO", "Consultorio Ambulatorio"),
                            ("SALA_PROCEDIMIENTO", "Sala de Procedimiento/Estudio"),
                            ("SALA_HEMODINAMIA", "Sala de Hemodinamia"),
                            ("QUIROFANO", "Quirófano"),
                        ],
                        max_length=30,
                    ),
                ),
                (
                    "medico_principal",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="atenciones_lideradas",
                        to="medicos.medico",
                    ),
                ),
                (
                    "paciente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="atenciones",
                        to="pacientes.paciente",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Recurso",
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
                ("nombre", models.CharField(max_length=100, unique=True)),
                (
                    "ubicacion",
                    models.CharField(
                        choices=[("CEHTA", "CEHTA"), ("ICPL", "ICPL")], max_length=10
                    ),
                ),
                (
                    "tipo_recurso",
                    models.CharField(
                        choices=[
                            ("CONSULTORIO", "Consultorio Ambulatorio"),
                            ("SALA_PROCEDIMIENTO", "Sala de Procedimiento/Estudio"),
                            ("SALA_HEMODINAMIA", "Sala de Hemodinamia"),
                            ("QUIROFANO", "Quirófano"),
                        ],
                        db_index=True,
                        max_length=30,
                    ),
                ),
                ("activo", models.BooleanField(default=True)),
            ],
        ),
        # === Paso 2: relajar choices/nullability del Turno actual ======
        migrations.AlterModelOptions(
            name="turno",
            options={"ordering": ["fecha_hora_inicio"]},
        ),
        migrations.AlterField(
            model_name="turno",
            name="estado",
            field=models.CharField(
                choices=[
                    ("DISPONIBLE", "Disponible"),
                    ("RESERVADO", "Reservado"),
                    ("CONFIRMADO", "Confirmado"),
                    ("CANCELADO", "Cancelado"),
                    ("REALIZADO", "Realizado"),
                    # Choices legacy se mantienen temporalmente para que el
                    # ``RunPython`` siguiente pueda leer/escribir cualquier
                    # valor existente sin violar constraints. Se eliminan más
                    # abajo en este mismo bloque.
                    ("PENDIENTE", "Pendiente"),
                    ("REAGENDADO", "Reagendado"),
                ],
                db_index=True,
                default="DISPONIBLE",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="turno",
            name="fecha_hora_fin",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="turno",
            name="fecha_hora_inicio",
            field=models.DateTimeField(blank=True, null=True, db_index=True),
        ),
        migrations.AlterField(
            model_name="turno",
            name="medico",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="turnos",
                to="medicos.medico",
            ),
        ),
        migrations.AlterField(
            model_name="turno",
            name="paciente",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="turnos",
                to="pacientes.paciente",
            ),
        ),
        # === Paso 3: agregar motivo_reserva (necesario para preservar texto) ===
        migrations.AddField(
            model_name="turno",
            name="motivo_reserva",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        # === Paso 4: PRESERVAR datos legacy ANTES de borrar columnas ===
        migrations.RunPython(migrate_legacy_turno_fields, noop_reverse),
        # === Paso 5: ahora sí, eliminar columnas legacy ================
        migrations.RemoveField(model_name="turno", name="centro_fisico"),
        migrations.RemoveField(model_name="turno", name="especialidad"),
        migrations.RemoveField(model_name="turno", name="fecha_creacion"),
        migrations.RemoveField(model_name="turno", name="fecha_hora"),
        migrations.RemoveField(model_name="turno", name="motivo_consulta"),
        migrations.RemoveField(model_name="turno", name="notas_administrativas"),
        migrations.RemoveField(model_name="turno", name="tipo_atencion"),
        migrations.RemoveField(model_name="turno", name="ultima_modificacion"),
        # === Paso 6: ajustar choices definitivos del estado ============
        migrations.AlterField(
            model_name="turno",
            name="estado",
            field=models.CharField(
                choices=[
                    ("DISPONIBLE", "Disponible"),
                    ("RESERVADO", "Reservado"),
                    ("CONFIRMADO", "Confirmado"),
                    ("CANCELADO", "Cancelado"),
                    ("REALIZADO", "Realizado"),
                ],
                db_index=True,
                default="DISPONIBLE",
                max_length=20,
            ),
        ),
        # ``fecha_hora_inicio`` vuelve a NOT NULL ahora que la migración de
        # datos garantizó valores válidos en cada fila preexistente.
        migrations.AlterField(
            model_name="turno",
            name="fecha_hora_inicio",
            field=models.DateTimeField(db_index=True),
        ),
        # === Paso 7: nuevos modelos hijos vinculados a Atencion ========
        migrations.CreateModel(
            name="ConsultaAmbulatoria",
            fields=[
                (
                    "atencion",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="consulta_ambulatoria",
                        serialize=False,
                        to="turnos.atencion",
                    ),
                ),
                ("anamnesis", models.TextField(blank=True, null=True)),
                ("examen_fisico", models.TextField(blank=True, null=True)),
                ("diagnostico_presuntivo", models.TextField(blank=True, null=True)),
                ("plan_manejo", models.TextField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name="RegistroProcedimiento",
            fields=[
                (
                    "atencion",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="registro_procedimiento",
                        serialize=False,
                        to="turnos.atencion",
                    ),
                ),
                ("descripcion_procedimiento", models.CharField(max_length=255)),
                ("informe_medico", models.TextField(blank=True, null=True)),
                ("hallazgos", models.TextField(blank=True, null=True)),
            ],
        ),
        migrations.AddField(
            model_name="atencion",
            name="turno",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="atencion",
                to="turnos.turno",
            ),
        ),
        migrations.AddField(
            model_name="turno",
            name="recurso",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="turnos",
                to="turnos.recurso",
            ),
        ),
        migrations.CreateModel(
            name="RegistroQuirurgico",
            fields=[
                (
                    "atencion",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="registro_quirurgico",
                        serialize=False,
                        to="turnos.atencion",
                    ),
                ),
                ("diagnostico_preoperatorio", models.TextField()),
                ("protocolo_quirurgico", models.TextField()),
                ("recuento_instrumental_ok", models.BooleanField(default=False)),
                (
                    "anestesista",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="anestesias_realizadas",
                        to="medicos.medico",
                    ),
                ),
            ],
        ),
    ]
