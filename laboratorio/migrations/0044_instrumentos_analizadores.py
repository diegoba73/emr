"""Interfaces ASTM, mapeos de analito, mensajes y alias compacto de tubo."""

from django.db import migrations, models
import django.db.models.deletion
import re


def backfill_codigo_instrumento(apps, schema_editor):
    Muestra = apps.get_model("laboratorio", "Muestra")
    re_tubo = re.compile(r"^LAB-(\d{4})-(\d{5})-(\d{2})$", re.IGNORECASE)
    seen = set()
    for m in Muestra.objects.exclude(codigo_barra__isnull=True).iterator():
        raw = (m.codigo_barra or "").strip()
        if not raw:
            continue
        match = re_tubo.match(raw.upper())
        if match:
            compact = f"{match.group(1)}{match.group(2)}{match.group(3)}"
        else:
            compact = re.sub(r"[^A-Z0-9]", "", raw.upper())[:15]
        if not compact or compact in seen:
            continue
        if Muestra.objects.filter(codigo_instrumento=compact).exclude(pk=m.pk).exists():
            continue
        seen.add(compact)
        Muestra.objects.filter(pk=m.pk).update(codigo_instrumento=compact)


class Migration(migrations.Migration):

    dependencies = [
        ("laboratorio", "0043_muestra_lugar_extraccion"),
    ]

    operations = [
        migrations.AddField(
            model_name="muestra",
            name="codigo_instrumento",
            field=models.CharField(
                blank=True,
                help_text="Alias corto para sample ID del equipo (año+secuencia+tubo, sin LAB- ni guiones).",
                max_length=16,
                null=True,
                unique=True,
                verbose_name="ID compacto analizador",
            ),
        ),
        migrations.CreateModel(
            name="InterfazInstrumento",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=120)),
                (
                    "driver",
                    models.CharField(
                        choices=[("CM260", "Wiener CM260"), ("SYSMEX_XP300", "Sysmex XP-300")],
                        max_length=20,
                    ),
                ),
                (
                    "transporte",
                    models.CharField(
                        choices=[
                            ("TCP", "TCP/IP"),
                            ("SERIAL", "RS-232"),
                            ("SIMULADOR", "Simulador"),
                        ],
                        default="SIMULADOR",
                        max_length=16,
                    ),
                ),
                ("host", models.CharField(blank=True, default="", max_length=120)),
                ("puerto", models.PositiveIntegerField(blank=True, null=True)),
                (
                    "puerto_serie",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="COM3, /dev/ttyUSB0, etc. Solo transporte SERIAL.",
                        max_length=40,
                    ),
                ),
                ("activo", models.BooleanField(default=True)),
                ("ultimo_contacto", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "equipo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="interfaces_instrumento",
                        to="laboratorio.equipoanalizador",
                    ),
                ),
            ],
            options={
                "verbose_name": "Interfaz de analizador",
                "verbose_name_plural": "Interfaces de analizador",
                "ordering": ["driver", "nombre"],
            },
        ),
        migrations.CreateModel(
            name="MapeoAnalitoInstrumento",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("codigo_instrumento", models.CharField(max_length=32)),
                ("activo", models.BooleanField(default=True)),
                (
                    "interfaz",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="mapeos",
                        to="laboratorio.interfazinstrumento",
                    ),
                ),
                (
                    "tipo_examen",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="mapeos_instrumento",
                        to="laboratorio.tipoexamen",
                    ),
                ),
            ],
            options={
                "verbose_name": "Mapeo de analito",
                "verbose_name_plural": "Mapeos de analito",
                "ordering": ["interfaz", "codigo_instrumento"],
                "unique_together": {("interfaz", "codigo_instrumento")},
            },
        ),
        migrations.CreateModel(
            name="MensajeInstrumento",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "direccion",
                    models.CharField(choices=[("IN", "Entrante"), ("OUT", "Saliente")], max_length=8),
                ),
                (
                    "estado",
                    models.CharField(
                        choices=[
                            ("OK", "OK"),
                            ("SIN_MATCH", "Sin match"),
                            ("IQC_BLOQUEADO", "IQC bloqueado"),
                            ("ERROR", "Error"),
                        ],
                        default="OK",
                        max_length=20,
                    ),
                ),
                ("sample_id", models.CharField(blank=True, default="", max_length=32)),
                (
                    "crudo",
                    models.TextField(blank=True, default="", help_text="ASTM truncado; sin PHI extra."),
                ),
                ("detalle", models.CharField(blank=True, default="", max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "interfaz",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="mensajes",
                        to="laboratorio.interfazinstrumento",
                    ),
                ),
                (
                    "muestra",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="mensajes_instrumento",
                        to="laboratorio.muestra",
                    ),
                ),
                (
                    "solicitud",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="mensajes_instrumento",
                        to="laboratorio.solicitudexamen",
                    ),
                ),
            ],
            options={
                "verbose_name": "Mensaje de analizador",
                "verbose_name_plural": "Mensajes de analizador",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="mensajeinstrumento",
            index=models.Index(fields=["estado", "created_at"], name="lab_msg_estado_idx"),
        ),
        migrations.AddIndex(
            model_name="mensajeinstrumento",
            index=models.Index(fields=["interfaz", "created_at"], name="lab_msg_interfaz_idx"),
        ),
        migrations.RunPython(backfill_codigo_instrumento, migrations.RunPython.noop),
    ]
