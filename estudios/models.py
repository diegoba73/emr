from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from catalogos.models import (
    CirugiaAbordaje,
    CirugiaEspecialidad,
    CirugiaProcedimiento,
    EstudioDiagnostico,
    ProcedimientoCatalogo,
)
from pacientes.models import Paciente
from estudios.practicas_cehta import PRACTICA_CHOICES
from estudios.actividad_rules import validar_correspondencia_actividad


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TipoEstudioComplementario(TimestampedModel):
    """``practica`` reemplaza el antiguo campo ``modalidad`` (códigos legacy + CEHTA)."""

    # Alias de compatibilidad para tests/imports antiguos.
    class Modalidad(models.TextChoices):
        IMAGEN_RX = 'IMAGEN_RX', 'Imagen — Rayos X'
        IMAGEN_TC = 'IMAGEN_TC', 'Imagen — Tomografía'
        IMAGEN_RM = 'IMAGEN_RM', 'Imagen — Resonancia'
        IMAGEN_US = 'IMAGEN_US', 'Imagen — Ultrasonido'
        PDF_INFORME_EXTERNO = 'PDF_INFORME_EXTERNO', 'PDF / informe externo'
        OTRO = 'OTRO', 'Otro'

    Practica = Modalidad  # nombre canónico en docs; choices reales = PRACTICA_CHOICES

    codigo = models.CharField(max_length=50, blank=True, null=True, unique=True)
    nombre = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True)
    practica = models.CharField(max_length=80, choices=PRACTICA_CHOICES)
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
        CONFIRMADO = 'CONFIRMADO', 'Confirmado'
        REALIZADO = 'REALIZADO', 'Realizado'
        INFORMADO = 'INFORMADO', 'Informado'
        VALIDADO = 'VALIDADO', 'Validado'
        ENTREGADO = 'ENTREGADO', 'Entregado'
        ANULADO = 'ANULADO', 'Anulado'

    class Origen(models.TextChoices):
        INTERNO = 'INTERNO', 'Interno'
        EXTERNO = 'EXTERNO', 'Externo'
        IMPORTADO_HISTORICO = 'IMPORTADO_HISTORICO', 'Importado histórico'

    class TipoActividad(models.TextChoices):
        ESTUDIO = 'ESTUDIO', 'Estudio'
        PROCEDIMIENTO = 'PROCEDIMIENTO', 'Procedimiento'
        CIRUGIA = 'CIRUGIA', 'Cirugía'

    class ClasificacionQuirurgicaSnapshot(models.TextChoices):
        NO_QUIRURGICO = 'NO_QUIRURGICO', 'No quirúrgico'
        QUIRURGICO = 'QUIRURGICO', 'Quirúrgico'

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
    # Nullable para futuros PROCEDIMIENTO/CIRUGIA; ESTUDIO sigue exigiendo
    # tipo_estudio y/o practica en clean()/serializers.
    practica = models.CharField(
        max_length=80,
        choices=PRACTICA_CHOICES,
        blank=True,
        null=True,
    )
    tipo_actividad = models.CharField(
        max_length=20,
        choices=TipoActividad.choices,
        default=TipoActividad.ESTUDIO,
        db_index=True,
    )
    procedimiento_catalogo = models.ForeignKey(
        ProcedimientoCatalogo,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='estudios_complementarios',
    )
    # Catálogo quirúrgico jerárquico (CIRUGIA nuevas). Legacy puede tener solo procedimiento_catalogo.
    cirugia_especialidad = models.ForeignKey(
        CirugiaEspecialidad,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='estudios_complementarios',
    )
    cirugia_procedimiento = models.ForeignKey(
        CirugiaProcedimiento,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='estudios_complementarios',
    )
    cirugia_abordaje = models.ForeignKey(
        CirugiaAbordaje,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='estudios_complementarios',
    )
    cirugia_especialidad_snapshot = models.CharField(max_length=200, blank=True, default='')
    cirugia_procedimiento_snapshot = models.CharField(max_length=255, blank=True, default='')
    cirugia_abordaje_snapshot = models.CharField(max_length=200, blank=True, default='')
    clasificacion_quirurgica_snapshot = models.CharField(
        max_length=20,
        choices=ClasificacionQuirurgicaSnapshot.choices,
        blank=True,
        null=True,
        default=None,
    )
    permite_multi_sesion = models.BooleanField(default=False)
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
        help_text='Profesional previsto (estudio/procedimiento) o cirujano (CIRUGIA).',
    )
    anestesista_previsto = models.ForeignKey(
        'medicos.Medico',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='estudios_anestesista_previsto',
        help_text='Solo CIRUGIA: anestesista previsto en el alta (confirmable al realizar).',
    )
    realizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='estudios_complementarios_realizados',
        verbose_name='Realizado / informado por',
        help_text='Profesional que realizó el estudio; tras VALIDADO solo este usuario (o admin) puede editar.',
    )
    turno = models.OneToOneField(
        'turnos.Turno',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='estudio_complementario',
    )
    atencion = models.ForeignKey(
        'turnos.Atencion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='estudios_complementarios',
    )
    # D: cierre administrativo vinculado a versión exacta del protocolo validado.
    cerrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='estudios_complementarios_cerrados',
    )
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    protocolo_cierre_informe = models.ForeignKey(
        'estudios.InformeEstudioComplementario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='estudios_cerrados_con_esta_version',
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
        if self.turno_id and self.turno.paciente_id != self.paciente_id:
            raise ValidationError({'turno': 'El turno no pertenece al paciente.'})
        if self.atencion_id and self.atencion.paciente_id != self.paciente_id:
            raise ValidationError({'atencion': 'La atención no pertenece al paciente.'})
        if self.consulta_hc_id and self.consulta_hc.historia_clinica_id != self.paciente_id:
            raise ValidationError({'consulta_hc': 'La consulta no pertenece al paciente.'})
        if self.solicitud_emr_id and self.solicitud_emr.paciente_id != self.paciente_id:
            raise ValidationError({'solicitud_emr': 'La solicitud no pertenece al paciente.'})
        if self.fecha_realizacion and self.fecha_realizacion > timezone.now():
            raise ValidationError({'fecha_realizacion': 'La fecha de realización no puede ser futura.'})

        tipo = self.tipo_actividad or self.TipoActividad.ESTUDIO
        if tipo == self.TipoActividad.ESTUDIO:
            if not self.tipo_estudio_id and not (self.practica or '').strip():
                raise ValidationError(
                    'ESTUDIO requiere tipo_estudio o practica.'
                )

        proc = None
        if self.procedimiento_catalogo_id:
            proc = self.procedimiento_catalogo
        validar_correspondencia_actividad(
            tipo_actividad=tipo,
            procedimiento_catalogo=proc,
            clasificacion_quirurgica_snapshot=self.clasificacion_quirurgica_snapshot,
            permite_multi_sesion=bool(self.permite_multi_sesion),
            cirugia_especialidad=self.cirugia_especialidad if self.cirugia_especialidad_id else None,
            cirugia_procedimiento=self.cirugia_procedimiento if self.cirugia_procedimiento_id else None,
            cirugia_abordaje=self.cirugia_abordaje if self.cirugia_abordaje_id else None,
        )

    @property
    def es_terminal(self) -> bool:
        return self.estado in (self.Estado.ANULADO, self.Estado.ENTREGADO)


class SesionActividad(TimestampedModel):
    """Unidad canónica de reserva/realización por sesión (A3). SoT de turno: este modelo."""

    class EstadoSesion(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        PROGRAMADA = 'PROGRAMADA', 'Programada'
        REALIZADA = 'REALIZADA', 'Realizada'
        CANCELADA = 'CANCELADA', 'Cancelada'

    estudio = models.ForeignKey(
        EstudioComplementario,
        on_delete=models.CASCADE,
        related_name='sesiones',
    )
    numero_sesion = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    turno = models.ForeignKey(
        'turnos.Turno',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sesiones_actividad',
    )
    atencion = models.ForeignKey(
        'turnos.Atencion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sesiones_actividad',
    )
    fecha_realizacion = models.DateTimeField(null=True, blank=True)
    realizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sesiones_actividad_realizadas',
    )
    estado_sesion = models.CharField(
        max_length=20,
        choices=EstadoSesion.choices,
        default=EstadoSesion.PENDIENTE,
        db_index=True,
    )

    class Meta:
        verbose_name = 'Sesión de actividad'
        verbose_name_plural = 'Sesiones de actividad'
        ordering = ['estudio_id', 'numero_sesion']
        constraints = [
            models.UniqueConstraint(
                fields=['estudio', 'numero_sesion'],
                name='uniq_sesion_actividad_estudio_numero',
            ),
            models.UniqueConstraint(
                fields=['turno'],
                condition=Q(turno__isnull=False),
                name='uniq_sesion_actividad_turno',
            ),
        ]

    def __str__(self) -> str:
        return f'SesionActividad:{self.pk} estudio={self.estudio_id}#{self.numero_sesion}'


class HistorialTurnoSesionActividad(TimestampedModel):
    """Trazabilidad de reprogramaciones (B). Sin campos nuevos en Turno."""

    sesion = models.ForeignKey(
        SesionActividad,
        on_delete=models.PROTECT,
        related_name='historial_turnos',
    )
    turno_anterior = models.ForeignKey(
        'turnos.Turno',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='+',
    )
    turno_nuevo = models.ForeignKey(
        'turnos.Turno',
        on_delete=models.PROTECT,
        related_name='+',
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historial_turnos_sesion_actividad',
    )
    motivo = models.TextField()

    class Meta:
        verbose_name = 'Historial de turno de sesión'
        verbose_name_plural = 'Historiales de turno de sesión'
        ordering = ['-created_at', '-id']

    def __str__(self) -> str:
        return f'HistorialTurnoSesion:{self.pk} sesion={self.sesion_id}'


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
    registro_procedimiento = models.ForeignKey(
        'turnos.RegistroProcedimiento',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='informes_estudio_complementario',
    )
    registro_quirurgico = models.ForeignKey(
        'turnos.RegistroQuirurgico',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='informes_estudio_complementario',
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

class HistorialCierreEstudioComplementario(TimestampedModel):
    """D: historial de cierres administrativos (conserva cierres previos tras rectificación)."""

    estudio = models.ForeignKey(
        EstudioComplementario,
        on_delete=models.CASCADE,
        related_name='historial_cierres',
    )
    informe = models.ForeignKey(
        InformeEstudioComplementario,
        on_delete=models.PROTECT,
        related_name='historial_cierres',
    )
    version_protocolo = models.PositiveIntegerField()
    cerrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historial_cierres_estudio',
    )
    fecha_cierre = models.DateTimeField()

    class Meta:
        verbose_name = 'Historial de cierre de estudio/cirugía'
        verbose_name_plural = 'Historiales de cierre de estudio/cirugía'
        ordering = ['-fecha_cierre', '-id']

    def __str__(self) -> str:
        return f'Cierre estudio={self.estudio_id} v={self.version_protocolo}'


class HistorialEntregaEstudioComplementario(TimestampedModel):
    """D: historial de entregas (conserva entregas previas tras rectificación)."""

    estudio = models.ForeignKey(
        EstudioComplementario,
        on_delete=models.CASCADE,
        related_name='historial_entregas',
    )
    informe = models.ForeignKey(
        InformeEstudioComplementario,
        on_delete=models.PROTECT,
        related_name='historial_entregas',
    )
    version_protocolo = models.PositiveIntegerField()
    entregado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historial_entregas_estudio',
    )
    fecha_entrega = models.DateTimeField()
    cierre = models.ForeignKey(
        HistorialCierreEstudioComplementario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='entregas',
    )

    class Meta:
        verbose_name = 'Historial de entrega de estudio/cirugía'
        verbose_name_plural = 'Historiales de entrega de estudio/cirugía'
        ordering = ['-fecha_entrega', '-id']

    def __str__(self) -> str:
        return f'Entrega estudio={self.estudio_id} v={self.version_protocolo}'

