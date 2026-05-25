from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from catalogos.models import EstudioDiagnostico
from pacientes.models import Paciente


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TipoEstudioComplementario(TimestampedModel):
    class Modalidad(models.TextChoices):
        IMAGEN_RX = 'IMAGEN_RX', 'Imagen — Rayos X'
        IMAGEN_TC = 'IMAGEN_TC', 'Imagen — Tomografía'
        IMAGEN_RM = 'IMAGEN_RM', 'Imagen — Resonancia'
        IMAGEN_US = 'IMAGEN_US', 'Imagen — Ultrasonido'
        PDF_INFORME_EXTERNO = 'PDF_INFORME_EXTERNO', 'PDF / informe externo'
        OTRO = 'OTRO', 'Otro'

    codigo = models.CharField(max_length=50, blank=True, null=True, unique=True)
    nombre = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True)
    modalidad = models.CharField(max_length=40, choices=Modalidad.choices)
    requiere_informe = models.BooleanField(default=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Tipo de estudio complementario'
        verbose_name_plural = 'Tipos de estudio complementario'
        ordering = ['nombre']

    def __str__(self) -> str:
        return self.nombre


class EstudioComplementario(TimestampedModel):
    class Estado(models.TextChoices):
        SOLICITADO = 'SOLICITADO', 'Solicitado'
        REALIZADO = 'REALIZADO', 'Realizado'
        INFORMADO = 'INFORMADO', 'Informado'
        VALIDADO = 'VALIDADO', 'Validado'
        ENTREGADO = 'ENTREGADO', 'Entregado'
        ANULADO = 'ANULADO', 'Anulado'

    class Origen(models.TextChoices):
        INTERNO = 'INTERNO', 'Interno'
        EXTERNO = 'EXTERNO', 'Externo'
        IMPORTADO_HISTORICO = 'IMPORTADO_HISTORICO', 'Importado histórico'

    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.PROTECT,
        related_name='estudios_complementarios',
    )
    tipo_estudio = models.ForeignKey(
        TipoEstudioComplementario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='estudios',
    )
    estudio_diagnostico = models.ForeignKey(
        EstudioDiagnostico,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='estudios_complementarios',
    )
    modalidad = models.CharField(
        max_length=40,
        choices=TipoEstudioComplementario.Modalidad.choices,
    )
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.SOLICITADO,
        db_index=True,
    )
    medico_solicitante = models.ForeignKey(
        'medicos.Medico',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='estudios_solicitados',
    )
    atencion = models.ForeignKey(
        'turnos.Atencion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='estudios_complementarios',
    )
    consulta_hc = models.ForeignKey(
        'historias_clinicas.Consulta',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='estudios_complementarios',
    )
    solicitud_emr = models.ForeignKey(
        'solicitudes.Solicitud',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='estudios_complementarios',
    )
    fecha_solicitud = models.DateTimeField(null=True, blank=True)
    fecha_realizacion = models.DateTimeField(null=True, blank=True)
    centro_realizador = models.CharField(max_length=255, blank=True)
    origen = models.CharField(
        max_length=30,
        choices=Origen.choices,
        default=Origen.INTERNO,
    )
    descripcion_clinica = models.TextField(blank=True)
    accession_number = models.CharField(max_length=64, blank=True)
    study_instance_uid = models.CharField(max_length=128, blank=True, db_index=True)
    pacs_metadata = models.JSONField(default=dict, blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='estudios_complementarios_creados',
    )
    modificado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='estudios_complementarios_modificados',
    )
    motivo_anulacion = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Estudio complementario'
        verbose_name_plural = 'Estudios complementarios'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'EstudioComplementario:{self.pk}'

    def clean(self) -> None:
        if self.atencion_id and self.atencion.paciente_id != self.paciente_id:
            raise ValidationError({'atencion': 'La atención no pertenece al paciente.'})
        if self.consulta_hc_id and self.consulta_hc.historia_clinica_id != self.paciente_id:
            raise ValidationError({'consulta_hc': 'La consulta no pertenece al paciente.'})
        if self.solicitud_emr_id and self.solicitud_emr.paciente_id != self.paciente_id:
            raise ValidationError({'solicitud_emr': 'La solicitud no pertenece al paciente.'})
        if self.fecha_realizacion and self.fecha_realizacion > timezone.now():
            raise ValidationError({'fecha_realizacion': 'La fecha de realización no puede ser futura.'})

    @property
    def es_terminal(self) -> bool:
        return self.estado in (self.Estado.ANULADO, self.Estado.ENTREGADO)


class ArchivoEstudioComplementario(TimestampedModel):
    class TipoRol(models.TextChoices):
        IMAGEN = 'IMAGEN', 'Imagen'
        INFORME_ESCANEADO = 'INFORME_ESCANEADO', 'Informe escaneado'
        DICOM_ZIP = 'DICOM_ZIP', 'DICOM / ZIP'
        OTRO = 'OTRO', 'Otro'

    estudio = models.ForeignKey(
        EstudioComplementario,
        on_delete=models.CASCADE,
        related_name='archivos_estudio',
    )
    archivo_medico = models.ForeignKey(
        'archivos_medicos.ArchivoMedico',
        on_delete=models.PROTECT,
        related_name='vinculos_estudio',
    )
    tipo_rol = models.CharField(max_length=30, choices=TipoRol.choices, default=TipoRol.OTRO)
    descripcion = models.CharField(max_length=500, blank=True)
    orden = models.PositiveIntegerField(default=0)
    es_principal = models.BooleanField(default=False)
    subido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='archivos_estudio_subidos',
    )

    class Meta:
        verbose_name = 'Archivo de estudio complementario'
        verbose_name_plural = 'Archivos de estudio complementario'
        ordering = ['orden', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['estudio', 'archivo_medico'],
                name='uniq_archivo_medico_por_estudio',
            ),
        ]

    def __str__(self) -> str:
        return f'ArchivoEstudioComplementario:{self.pk}'

    def clean(self) -> None:
        if self.archivo_medico.paciente_id != self.estudio.paciente_id:
            raise ValidationError(
                {'archivo_medico': 'El archivo médico pertenece a otro paciente.'}
            )

    def save(self, *args, **kwargs):
        if self.estudio_id and self.archivo_medico_id:
            self.full_clean()
        return super().save(*args, **kwargs)


class InformeEstudioComplementario(TimestampedModel):
    class EstadoInforme(models.TextChoices):
        BORRADOR = 'BORRADOR', 'Borrador'
        EMITIDO = 'EMITIDO', 'Emitido'
        VALIDADO = 'VALIDADO', 'Validado'
        ANULADO = 'ANULADO', 'Anulado'

    class TipoInforme(models.TextChoices):
        PRELIMINAR = 'PRELIMINAR', 'Preliminar'
        FINAL = 'FINAL', 'Final'

    estudio = models.ForeignKey(
        EstudioComplementario,
        on_delete=models.CASCADE,
        related_name='informes',
    )
    version = models.PositiveIntegerField(default=1)
    estado = models.CharField(
        max_length=20,
        choices=EstadoInforme.choices,
        default=EstadoInforme.BORRADOR,
    )
    tipo = models.CharField(
        max_length=20,
        choices=TipoInforme.choices,
        default=TipoInforme.FINAL,
    )
    texto = models.TextField(blank=True)
    archivo_pdf = models.FileField(
        upload_to='estudios/informes/%Y/%m/',
        blank=True,
        null=True,
    )
    es_vigente = models.BooleanField(default=False)
    informado_por = models.ForeignKey(
        'medicos.Medico',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='informes_estudio_emitidos',
    )
    fecha_informe = models.DateTimeField(null=True, blank=True)
    validado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='informes_estudio_validados',
    )
    fecha_validacion = models.DateTimeField(null=True, blank=True)
    reemplaza_a = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='versiones_siguientes',
    )
    motivo_rectificacion = models.TextField(blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='informes_estudio_creados',
    )

    class Meta:
        verbose_name = 'Informe de estudio complementario'
        verbose_name_plural = 'Informes de estudio complementario'
        ordering = ['-version', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['estudio'],
                condition=Q(es_vigente=True),
                name='uniq_informe_vigente_por_estudio',
            ),
        ]

    def __str__(self) -> str:
        return f'InformeEstudioComplementario:{self.pk}'

    def clean(self) -> None:
        if self.estado == self.EstadoInforme.VALIDADO and not self.validado_por_id:
            pass  # validado en servicio al validar
