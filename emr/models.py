from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SignosVitales(TimestampedModel):
    class RolRegistrador(models.TextChoices):
        MEDICO = 'MEDICO', 'Médico'
        ENFERMERIA = 'ENFERMERIA', 'Enfermería'
        ADMINISTRATIVO = 'ADMINISTRATIVO', 'Administrativo'
        OTRO = 'OTRO', 'Otro'

    atencion = models.ForeignKey(
        'turnos.Atencion',
        on_delete=models.CASCADE,
        related_name='signos_vitales'
    )
    registrado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='signos_vitales_registrados',
        null=True,
        blank=True
    )
    rol_registrador = models.CharField(
        max_length=50,
        choices=RolRegistrador.choices,
        default=RolRegistrador.MEDICO
    )
    fecha_registro = models.DateTimeField(default=timezone.now, db_index=True)
    tension_arterial = models.CharField(max_length=15, blank=True, null=True)
    frecuencia_cardiaca = models.PositiveSmallIntegerField(blank=True, null=True)
    frecuencia_respiratoria = models.PositiveSmallIntegerField(blank=True, null=True)
    temperatura = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    saturacion_oxigeno = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    indice_masa_corporal = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    peso = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    talla = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True)

    class Meta:
        app_label = 'emr'
        verbose_name = 'Signos Vitales'
        verbose_name_plural = 'Signos Vitales'
        ordering = ['-fecha_registro', '-created_at']

    def __str__(self) -> str:
        return f"Signos vitales de Atención {self.atencion_id} ({self.fecha_registro:%Y-%m-%d %H:%M})"


class Documento(TimestampedModel):
    class TipoDocumento(models.TextChoices):
        INFORME = 'INFORME', 'Informe'
        ESTUDIO = 'ESTUDIO', 'Estudio'
        ANALISIS = 'ANALISIS', 'Análisis'
        DIAGNOSTICO = 'DIAGNOSTICO', 'Diagnóstico'
        IMAGEN = 'IMAGEN', 'Imagen'
        CONSENTIMIENTO = 'CONSENTIMIENTO', 'Consentimiento'
        OTRO = 'OTRO', 'Otro'

    atencion = models.ForeignKey(
        'turnos.Atencion',
        on_delete=models.CASCADE,
        related_name='documentos'
    )
    tipo_documento = models.CharField(max_length=20, choices=TipoDocumento.choices)
    archivo = models.FileField(upload_to='emr/documentos/')
    descripcion = models.TextField(blank=True, null=True)
    fecha_subida = models.DateTimeField(auto_now_add=True)
    usuario_cargador = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='documentos_emr_cargados',
        null=True,
        blank=True
    )

    class Meta:
        app_label = 'emr'
        verbose_name = 'Documento Clínico'
        verbose_name_plural = 'Documentos Clínicos'
        ordering = ['-fecha_subida']

    def __str__(self) -> str:
        return f"Documento {self.get_tipo_documento_display()} - Atención {self.atencion_id}"
