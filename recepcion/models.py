"""Puestos de recepción, reglas de ruteo y llegadas del día."""
from django.db import models
from django.core.exceptions import ValidationError


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class PuestoRecepcion(TimestampedModel):
    """Ventanilla física de recepción (no es consultorio clínico)."""

    class Modo(models.TextChoices):
        TODO = 'TODO', 'Atiende cualquier llegada'
        REGLAS = 'REGLAS', 'Solo lo que matchean sus reglas'

    codigo = models.SlugField(max_length=32, unique=True)
    nombre = models.CharField(max_length=120)
    etiqueta_paciente = models.CharField(
        max_length=120,
        blank=True,
        help_text='Texto que ve el paciente (ej. Consultas, Estudios). Si vacío, usa nombre.',
    )
    activo = models.BooleanField(default=True, db_index=True)
    modo = models.CharField(max_length=16, choices=Modo.choices, default=Modo.REGLAS)
    es_fallback = models.BooleanField(
        default=False,
        help_text='Si ninguna regla matchea, usar este puesto (solo uno debería serlo).',
    )
    orden = models.PositiveSmallIntegerField(default=1)
    ubicacion = models.CharField(
        max_length=10,
        choices=[('CEHTA', 'CEHTA'), ('ICPL', 'ICPL')],
        blank=True,
        null=True,
        db_index=True,
        help_text='Sede del puesto. Vacío = visible sin filtro de sede.',
    )

    class Meta:
        ordering = ['orden', 'id']
        verbose_name = 'Puesto de recepción'
        verbose_name_plural = 'Puestos de recepción'

    def __str__(self):
        return f'{self.nombre} ({self.codigo})'

    @property
    def label_publico(self) -> str:
        return (self.etiqueta_paciente or self.nombre or self.codigo).strip()


TIPOS_COBERTURA_SECRETARIA = (
    'CONSULTA',
    'SIN_TURNO',
    'ESTUDIO',
    'PROCEDIMIENTO',
    'CIRUGIA',
)


class CoberturaRecepcion(TimestampedModel):
    """
    Cobertura del día: en qué ventanilla está la secretaria y qué tipos atiende.
    Dinámica (cambia cuando haga falta); independiente de reglas fijas por puesto.
    """

    usuario = models.ForeignKey(
        'usuarios.User',
        on_delete=models.CASCADE,
        related_name='coberturas_recepcion',
    )
    fecha = models.DateField(db_index=True)
    puesto = models.ForeignKey(
        PuestoRecepcion,
        on_delete=models.PROTECT,
        related_name='coberturas',
        help_text='Ventanilla física donde está hoy (Puesto 1 / 2).',
    )
    tipos = models.JSONField(
        default=list,
        blank=True,
        help_text='Lista de tipo_actividad que atiende hoy (CONSULTA, SIN_TURNO, …).',
    )
    sede = models.CharField(
        max_length=10,
        choices=[('CEHTA', 'CEHTA'), ('ICPL', 'ICPL')],
        blank=True,
        null=True,
        db_index=True,
        help_text='Sede opcional. Vacío = aplica sin filtro de sede.',
    )

    class Meta:
        ordering = ['-fecha', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['usuario', 'fecha'],
                name='recepcion_cobertura_user_fecha_uniq',
            ),
        ]
        verbose_name = 'Cobertura de recepción'
        verbose_name_plural = 'Coberturas de recepción'

    def __str__(self):
        return f'Cobertura {self.usuario_id} {self.fecha} → {self.puesto_id}'


class ReglaRuteoRecepcion(TimestampedModel):
    """Regla admin legacy: qué tipo va a qué puesto (solo lab / fallback)."""

    class TipoActividad(models.TextChoices):
        CONSULTA = 'CONSULTA', 'Consulta médica'
        ESTUDIO = 'ESTUDIO', 'Estudio'
        PROCEDIMIENTO = 'PROCEDIMIENTO', 'Procedimiento'
        CIRUGIA = 'CIRUGIA', 'Cirugía'
        EXTRACCION = 'EXTRACCION', 'Extracción / lab'
        SIN_TURNO = 'SIN_TURNO', 'Sin turno (walk-in)'

    puesto = models.ForeignKey(
        PuestoRecepcion,
        on_delete=models.CASCADE,
        related_name='reglas',
    )
    nombre = models.CharField(max_length=120, blank=True)
    prioridad = models.PositiveSmallIntegerField(
        default=100,
        help_text='Menor número = se evalúa primero.',
        db_index=True,
    )
    activo = models.BooleanField(default=True, db_index=True)
    tipo_actividad = models.CharField(
        max_length=20,
        choices=TipoActividad.choices,
        blank=True,
        default='',
        help_text='Vacío = cualquier tipo de actividad.',
    )
    tipo_recurso = models.CharField(
        max_length=30,
        blank=True,
        default='',
        help_text='Ej. CONSULTORIO, SALA_PROCEDIMIENTO, EXTRACCIONES. Vacío = cualquiera.',
    )
    recurso = models.ForeignKey(
        'turnos.Recurso',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reglas_ruteo_recepcion',
    )
    medico = models.ForeignKey(
        'medicos.Medico',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reglas_ruteo_recepcion',
    )

    class Meta:
        ordering = ['prioridad', 'id']
        verbose_name = 'Regla de ruteo de recepción'
        verbose_name_plural = 'Reglas de ruteo de recepción'

    def __str__(self):
        return self.nombre or f'Regla #{self.pk} → {self.puesto_id}'


class LlegadaRecepcion(TimestampedModel):
    """Check-in / ítem de cola de recepción del día."""

    class EstadoFlujo(models.TextChoices):
        PROGRAMADO = 'PROGRAMADO', 'Programado (aún no llegó)'
        EN_ESPERA_RECEPCION = 'EN_ESPERA_RECEPCION', 'En espera en recepción'
        EN_ESPERA = 'EN_ESPERA', 'En espera (destino clínico)'
        LLAMADO = 'LLAMADO', 'Llamado'
        EN_ATENCION = 'EN_ATENCION', 'En atención'
        ATENDIDO = 'ATENDIDO', 'Atendido'
        NO_ASISTIO = 'NO_ASISTIO', 'No asistió'
        CANCELADO = 'CANCELADO', 'Cancelado'

    class TipoActividad(models.TextChoices):
        CONSULTA = 'CONSULTA', 'Consulta médica'
        ESTUDIO = 'ESTUDIO', 'Estudio'
        PROCEDIMIENTO = 'PROCEDIMIENTO', 'Procedimiento'
        CIRUGIA = 'CIRUGIA', 'Cirugía'
        EXTRACCION = 'EXTRACCION', 'Extracción / lab'
        SIN_TURNO = 'SIN_TURNO', 'Sin turno'

    paciente = models.ForeignKey(
        'pacientes.Paciente',
        on_delete=models.CASCADE,
        related_name='llegadas_recepcion',
    )
    puesto = models.ForeignKey(
        PuestoRecepcion,
        on_delete=models.PROTECT,
        related_name='llegadas',
    )
    turno = models.ForeignKey(
        'turnos.Turno',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='llegadas_recepcion',
    )
    tipo_actividad = models.CharField(
        max_length=20,
        choices=TipoActividad.choices,
        default=TipoActividad.SIN_TURNO,
        db_index=True,
    )
    estado_flujo = models.CharField(
        max_length=24,
        choices=EstadoFlujo.choices,
        default=EstadoFlujo.EN_ESPERA_RECEPCION,
        db_index=True,
    )
    fecha = models.DateField(db_index=True)
    checkin_en = models.DateTimeField(null=True, blank=True)
    llamado_en = models.DateTimeField(null=True, blank=True)
    destino_recurso = models.ForeignKey(
        'turnos.Recurso',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='llegadas_destino',
    )
    destino_label = models.CharField(max_length=120, blank=True, default='')
    notas = models.CharField(max_length=255, blank=True, default='')
    numero_orden_dia = models.PositiveIntegerField(null=True, blank=True)
    prefijo_llamado = models.CharField(
        max_length=1,
        blank=True,
        default='',
        db_index=True,
        help_text='T/S/E/P/L según motivo de anuncio.',
    )
    codigo_llamado = models.CharField(
        max_length=8,
        blank=True,
        default='',
        db_index=True,
        help_text='Código público tipo T03, L01.',
    )
    zona_llamado = models.CharField(
        max_length=12,
        blank=True,
        default='',
        db_index=True,
        help_text='RECEPCION o MEDICO: en qué mitad de la TV se muestra el llamado.',
    )
    token_publico = models.CharField(
        max_length=48,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text='Token opaco para página de espera del paciente (QR).',
    )

    class Meta:
        ordering = ['checkin_en', 'id']
        indexes = [
            models.Index(fields=['fecha', 'puesto', 'estado_flujo']),
            models.Index(fields=['fecha', 'estado_flujo']),
        ]
        verbose_name = 'Llegada a recepción'
        verbose_name_plural = 'Llegadas a recepción'

    def clean(self):
        if self.turno_id and self.paciente_id and self.turno.paciente_id:
            if self.turno.paciente_id != self.paciente_id:
                raise ValidationError({'turno': 'El turno no corresponde al paciente.'})

    def __str__(self):
        return f'Llegada #{self.pk} {self.paciente_id} → {self.puesto_id} ({self.estado_flujo})'
