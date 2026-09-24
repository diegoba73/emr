# Generated manually for LabWin micro catalogs

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("laboratorio", "0051_merge_modo_entrada_ref_comercial"),
    ]

    operations = [
        migrations.AddField(
            model_name="microorganismo",
            name="nombre_original",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Texto legado sin alterar (LabWin u otra fuente).",
                max_length=200,
                verbose_name="Nombre original",
            ),
        ),
        migrations.AddField(
            model_name="microorganismo",
            name="tipo_registro",
            field=models.CharField(
                choices=[
                    ("MICROORGANISMO", "Microorganismo"),
                    ("HALLAZGO", "Hallazgo"),
                    ("MORFOLOGIA", "Morfología"),
                    ("FLORA", "Flora"),
                    ("NEGATIVO", "Resultado negativo"),
                    ("OTRO", "Otro"),
                ],
                default="MICROORGANISMO",
                max_length=20,
                verbose_name="Tipo de registro",
            ),
        ),
        migrations.AddField(
            model_name="microorganismo",
            name="origen",
            field=models.CharField(
                choices=[
                    ("MANUAL", "Manual"),
                    ("REFERENCIA", "Referencia"),
                    ("LABWIN_BACTE", "LabWin BACTE"),
                ],
                default="MANUAL",
                max_length=20,
                verbose_name="Origen",
            ),
        ),
        migrations.AddField(
            model_name="microorganismo",
            name="correccion_estado",
            field=models.CharField(
                choices=[
                    ("NINGUNA", "Sin corrección"),
                    ("ORTOGRAFIA_AUTO", "Ortografía automática"),
                    ("PENDIENTE_REVISION", "Pendiente revisión profesional"),
                ],
                default="NINGUNA",
                max_length=24,
                verbose_name="Estado de corrección",
            ),
        ),
        migrations.AddField(
            model_name="microorganismo",
            name="requiere_revision",
            field=models.BooleanField(default=False, verbose_name="Requiere revisión"),
        ),
        migrations.AddField(
            model_name="microorganismo",
            name="motivo_revision",
            field=models.TextField(blank=True, default="", verbose_name="Motivo de revisión"),
        ),
        migrations.AddField(
            model_name="microorganismo",
            name="archivo_origen",
            field=models.CharField(blank=True, default="", max_length=255, verbose_name="Archivo origen"),
        ),
        migrations.AddField(
            model_name="microorganismo",
            name="importado_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Importado en"),
        ),
        migrations.AddField(
            model_name="microorganismo",
            name="editado_manualmente",
            field=models.BooleanField(
                default=False,
                help_text="Si es True, reimportaciones no pisan nombre/activo.",
                verbose_name="Editado manualmente",
            ),
        ),
        migrations.AlterField(
            model_name="microorganismo",
            name="nombre",
            field=models.CharField(max_length=200, verbose_name="Nombre para mostrar"),
        ),
        migrations.AddIndex(
            model_name="microorganismo",
            index=models.Index(fields=["origen", "codigo"], name="laboratorio_origen_7c1a01_idx"),
        ),
        migrations.AddIndex(
            model_name="microorganismo",
            index=models.Index(
                fields=["requiere_revision", "activo"], name="laboratorio_requier_8a2b01_idx"
            ),
        ),
        migrations.AddField(
            model_name="antibiotico",
            name="nombre_original",
            field=models.CharField(blank=True, default="", max_length=200, verbose_name="Nombre original"),
        ),
        migrations.AddField(
            model_name="antibiotico",
            name="origen",
            field=models.CharField(
                choices=[
                    ("MANUAL", "Manual"),
                    ("REFERENCIA", "Referencia"),
                    ("LABWIN_ANTIB", "LabWin ANTIB"),
                ],
                default="MANUAL",
                max_length=20,
                verbose_name="Origen",
            ),
        ),
        migrations.AddField(
            model_name="antibiotico",
            name="correccion_estado",
            field=models.CharField(
                choices=[
                    ("NINGUNA", "Sin corrección"),
                    ("ORTOGRAFIA_AUTO", "Ortografía automática"),
                    ("PENDIENTE_REVISION", "Pendiente revisión profesional"),
                ],
                default="NINGUNA",
                max_length=24,
                verbose_name="Estado de corrección",
            ),
        ),
        migrations.AddField(
            model_name="antibiotico",
            name="requiere_revision",
            field=models.BooleanField(default=False, verbose_name="Requiere revisión"),
        ),
        migrations.AddField(
            model_name="antibiotico",
            name="motivo_revision",
            field=models.TextField(blank=True, default="", verbose_name="Motivo de revisión"),
        ),
        migrations.AddField(
            model_name="antibiotico",
            name="archivo_origen",
            field=models.CharField(blank=True, default="", max_length=255, verbose_name="Archivo origen"),
        ),
        migrations.AddField(
            model_name="antibiotico",
            name="importado_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Importado en"),
        ),
        migrations.AddField(
            model_name="antibiotico",
            name="editado_manualmente",
            field=models.BooleanField(default=False, verbose_name="Editado manualmente"),
        ),
        migrations.AddField(
            model_name="antibiotico",
            name="labwin_d1",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Valor crudo de exportación; no interpretar como grupo clínico.",
                max_length=40,
                verbose_name="LabWin D1_FLD",
            ),
        ),
        migrations.AddField(
            model_name="antibiotico",
            name="labwin_d2",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Valor crudo de exportación; no interpretar como grupo clínico.",
                max_length=40,
                verbose_name="LabWin D2_FLD",
            ),
        ),
        migrations.AlterField(
            model_name="antibiotico",
            name="nombre",
            field=models.CharField(max_length=200, verbose_name="Nombre para mostrar"),
        ),
        migrations.AddIndex(
            model_name="antibiotico",
            index=models.Index(fields=["origen", "codigo"], name="laboratorio_origen_ab01_idx"),
        ),
        migrations.AddIndex(
            model_name="antibiotico",
            index=models.Index(
                fields=["requiere_revision", "activo"], name="laboratorio_requier_ab02_idx"
            ),
        ),
        migrations.AddField(
            model_name="resultadoantibiotico",
            name="unidad_halo",
            field=models.CharField(blank=True, default="mm", max_length=16, verbose_name="Unidad halo"),
        ),
        migrations.AddField(
            model_name="resultadoantibiotico",
            name="unidad_mic",
            field=models.CharField(blank=True, default="", max_length=24, verbose_name="Unidad MIC/CIM"),
        ),
        migrations.AddField(
            model_name="resultadoantibiotico",
            name="metodo",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Difusión, microdilución, etc. Opcional si ya figura en el antibiograma.",
                max_length=120,
                verbose_name="Método",
            ),
        ),
        migrations.AddField(
            model_name="resultadoantibiotico",
            name="estandar_version",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Ej. CLSI M100 2024, EUCAST 2024; texto libre del laboratorio.",
                max_length=80,
                verbose_name="Estándar / versión",
            ),
        ),
        migrations.AlterField(
            model_name="resultadoantibiotico",
            name="mic",
            field=models.CharField(blank=True, default="", max_length=40, verbose_name="MIC/CIM"),
        ),
        migrations.AlterField(
            model_name="resultadoantibiotico",
            name="interpretacion",
            field=models.CharField(
                choices=[
                    ("S", "Sensible"),
                    ("I", "Intermedio"),
                    ("R", "Resistente"),
                    ("SDD", "Sensible dosis-dependiente"),
                    ("NO_APLICA", "No aplica"),
                ],
                help_text="Interpretación validada por el laboratorio; no se calcula S/I/R automáticamente.",
                max_length=10,
                verbose_name="Interpretación",
            ),
        ),
        migrations.CreateModel(
            name="FraseRapidaMicrobiologia",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("abreviatura", models.CharField(max_length=40, unique=True, verbose_name="Abreviatura original")),
                ("texto", models.TextField(verbose_name="Texto para mostrar")),
                ("texto_original", models.TextField(blank=True, default="", verbose_name="Texto original")),
                (
                    "categoria",
                    models.CharField(
                        choices=[
                            ("GENERAL", "General"),
                            ("HALLAZGO", "Hallazgo"),
                            ("INTERPRETACION", "Interpretación clínica"),
                            ("UMBRAL", "Umbral histórico"),
                            ("FENOTIPO", "Fenotipo"),
                            ("OTRO", "Otro"),
                        ],
                        default="GENERAL",
                        max_length=20,
                        verbose_name="Categoría",
                    ),
                ),
                (
                    "origen",
                    models.CharField(
                        choices=[
                            ("MANUAL", "Manual"),
                            ("LABWIN_NEMOTEC", "LabWin NEMOTEC"),
                        ],
                        default="MANUAL",
                        max_length=20,
                        verbose_name="Origen",
                    ),
                ),
                (
                    "correccion_estado",
                    models.CharField(
                        choices=[
                            ("NINGUNA", "Sin corrección"),
                            ("ORTOGRAFIA_AUTO", "Ortografía automática"),
                            ("PENDIENTE_REVISION", "Pendiente revisión profesional"),
                        ],
                        default="NINGUNA",
                        max_length=24,
                        verbose_name="Estado de corrección",
                    ),
                ),
                ("requiere_revision", models.BooleanField(default=False, verbose_name="Requiere revisión")),
                ("motivo_revision", models.TextField(blank=True, default="", verbose_name="Motivo de revisión")),
                ("archivo_origen", models.CharField(blank=True, default="", max_length=255, verbose_name="Archivo origen")),
                ("importado_at", models.DateTimeField(blank=True, null=True, verbose_name="Importado en")),
                ("editado_manualmente", models.BooleanField(default=False, verbose_name="Editado manualmente")),
                ("activo", models.BooleanField(default=True, verbose_name="Activo")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Frase rápida microbiológica",
                "verbose_name_plural": "Frases rápidas microbiológicas",
                "ordering": ["abreviatura"],
            },
        ),
        migrations.CreateModel(
            name="LabwinMicroCatalogImportBatch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fuente_dir", models.CharField(max_length=512, verbose_name="Directorio fuente")),
                ("dry_run", models.BooleanField(default=False)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("counts", models.JSONField(blank=True, default=dict)),
                ("errores", models.JSONField(blank=True, default=list)),
                ("revision_pendiente", models.JSONField(blank=True, default=list)),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="labwin_micro_catalog_imports",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Importación catálogo micro LabWin",
                "verbose_name_plural": "Importaciones catálogo micro LabWin",
                "ordering": ["-started_at"],
            },
        ),
        migrations.CreateModel(
            name="FraseRapidaAsociacionAnalisis",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("analisis_abrev_labwin", models.CharField(max_length=40, verbose_name="Análisis LabWin (ABREV_FLD)")),
                ("posicion", models.PositiveIntegerField(verbose_name="Posición (POSICION_FLD)")),
                ("nemotec_abrev", models.CharField(max_length=40, verbose_name="Abreviatura NEMOTEC")),
                ("numrec_labwin", models.CharField(blank=True, default="", max_length=40, verbose_name="NUMREC_FLD")),
                ("archivo_origen", models.CharField(blank=True, default="", max_length=255, verbose_name="Archivo origen")),
                ("importado_at", models.DateTimeField(blank=True, null=True, verbose_name="Importado en")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "frase",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="asociaciones_analisis",
                        to="laboratorio.fraserapidamicrobiologia",
                        verbose_name="Frase rápida",
                    ),
                ),
                (
                    "tipo_examen",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="frases_rapidas_labwin",
                        to="laboratorio.tipoexamen",
                        verbose_name="Tipo examen SYNESIS (pendiente de mapeo)",
                    ),
                ),
            ],
            options={
                "verbose_name": "Asociación frase–análisis LabWin",
                "verbose_name_plural": "Asociaciones frase–análisis LabWin",
                "ordering": ["analisis_abrev_labwin", "posicion", "nemotec_abrev"],
            },
        ),
        migrations.AddIndex(
            model_name="fraserapidamicrobiologia",
            index=models.Index(fields=["activo", "abreviatura"], name="laboratorio_activo_fr01_idx"),
        ),
        migrations.AddIndex(
            model_name="fraserapidamicrobiologia",
            index=models.Index(fields=["origen", "abreviatura"], name="laboratorio_origen_fr02_idx"),
        ),
        migrations.AddIndex(
            model_name="fraserapidamicrobiologia",
            index=models.Index(fields=["categoria", "activo"], name="laboratorio_catego_fr03_idx"),
        ),
        migrations.AddIndex(
            model_name="fraserapidamicrobiologia",
            index=models.Index(fields=["requiere_revision"], name="laboratorio_requier_fr04_idx"),
        ),
        migrations.AddIndex(
            model_name="fraserapidaasociacionanalisis",
            index=models.Index(
                fields=["analisis_abrev_labwin", "posicion"], name="laboratorio_analis_ne01_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="fraserapidaasociacionanalisis",
            index=models.Index(fields=["nemotec_abrev"], name="laboratorio_nemote_ne02_idx"),
        ),
        migrations.AddConstraint(
            model_name="fraserapidaasociacionanalisis",
            constraint=models.UniqueConstraint(
                fields=("analisis_abrev_labwin", "posicion", "nemotec_abrev"),
                name="uniq_labwin_nemoespe_analisis_pos_nemo",
            ),
        ),
    ]
