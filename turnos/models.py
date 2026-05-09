from django.db import models
from pacientes.models import Paciente
from medicos.models import Medico
from catalogos.models import ProcedimientoCatalogo, EstudioDiagnostico


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        abstract = True


class Recurso(TimestampedModel):
    """
    Representa un recurso físico agendable (consultorio, quirófano, sala de hemodinamia).
    Define la capacidad y el tipo de atención que se puede realizar.
    """

    class Ubicacion(models.TextChoices):
        CEHTA = 'CEHTA', 'CEHTA'
        ICPL = 'ICPL', 'ICPL'

    class TipoRecurso(models.TextChoices):
        CONSULTORIO = 'CONSULTORIO', 'Consultorio Ambulatorio'
        SALA_PROCEDIMIENTO = 'SALA_PROCEDIMIENTO', 'Sala de Procedimiento/Estudio'
        SALA_HEMODINAMIA = 'SALA_HEMODINAMIA', 'Sala de Hemodinamia'
        QUIROFANO = 'QUIROFANO', 'Quirófano'

    nombre = models.CharField(max_length=100, unique=True)
    ubicacion = models.CharField(max_length=10, choices=Ubicacion.choices)
    tipo_recurso = models.CharField(max_length=30, choices=TipoRecurso.choices, db_index=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"Recurso: {self.nombre} ({self.get_ubicacion_display()}) - {self.get_tipo_recurso_display()}"


class Turno(TimestampedModel):
    """
    Representa una reserva logística de tiempo y recursos.
    """
    
    class Estado(models.TextChoices):
        DISPONIBLE = 'DISPONIBLE', 'Disponible'
        RESERVADO = 'RESERVADO', 'Reservado'
        CONFIRMADO = 'CONFIRMADO', 'Confirmado'
        CANCELADO = 'CANCELADO', 'Cancelado'
        REALIZADO = 'REALIZADO', 'Realizado'

    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="turnos"
    )
    medico = models.ForeignKey(
        Medico,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="turnos"
    )
    recurso = models.ForeignKey(
        'Recurso',
        on_delete=models.CASCADE,
        related_name="turnos",
        null=True,
        blank=True
    )
    fecha_hora_inicio = models.DateTimeField(db_index=True)
    fecha_hora_fin = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.DISPONIBLE,
        db_index=True
    )
    motivo_reserva = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ['fecha_hora_inicio']

    def clean(self):
        """
        Validación: Si fecha_hora_fin se provee, debe ser mayor a fecha_hora_inicio.
        """
        from django.core.exceptions import ValidationError
        
        if self.fecha_hora_fin and self.fecha_hora_inicio:
            if self.fecha_hora_fin <= self.fecha_hora_inicio:
                raise ValidationError({
                    'fecha_hora_fin': 'La fecha/hora de fin debe ser posterior a la fecha/hora de inicio.'
                })
    
    def save(self, *args, **kwargs):
        """
        Sobrescribe save() para ejecutar validaciones automáticamente.
        """
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        paciente_str = f"{self.paciente.apellido}, {self.paciente.nombre}" if self.paciente else "Sin paciente"
        recurso_str = self.recurso.nombre if self.recurso else "Sin recurso"
        fecha_str = self.fecha_hora_inicio.strftime('%Y-%m-%d %H:%M') if self.fecha_hora_inicio else "Sin fecha"
        return f"Turno #{self.id} ({paciente_str}) - {recurso_str} - {fecha_str}"


class Atencion(TimestampedModel):
    """
    Contenedor principal para un encuentro clínico. Se crea cuando un turno
    se admite y vincula todos los registros médicos asociados.
    """
    
    class TipoIntervencion(models.TextChoices):
        CONSULTA = 'CONSULTA', 'Consulta'
        ESTUDIO = 'ESTUDIO', 'Estudio'
        PROCEDIMIENTO = 'PROCEDIMIENTO', 'Procedimiento'
        CIRUGIA = 'CIRUGIA', 'Cirugía'

    class EstadoClinico(models.TextChoices):
        ABIERTA = 'ABIERTA', 'Abierta'
        FINALIZADA = 'FINALIZADA', 'Finalizada'
        EN_REVISION = 'EN_REVISION', 'En revisión'

    turno = models.OneToOneField(
        Turno,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="atencion"
    )
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.PROTECT,
        related_name="atenciones"
    )
    medico_principal = models.ForeignKey(
        Medico,
        on_delete=models.PROTECT,
        related_name="atenciones_lideradas"
    )
    fecha_admision = models.DateTimeField(auto_now_add=True, db_index=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    tipo_atencion = models.CharField(max_length=30, choices=Recurso.TipoRecurso.choices)
    tipo_intervencion = models.CharField(
        max_length=20,
        choices=TipoIntervencion.choices,
        default=TipoIntervencion.CONSULTA
    )
    estado_clinico = models.CharField(
        max_length=20,
        choices=EstadoClinico.choices,
        default=EstadoClinico.ABIERTA
    )
    observaciones_generales = models.TextField(blank=True, null=True)

    def __str__(self):
        paciente_str = f"{self.paciente.apellido}, {self.paciente.nombre}" if self.paciente else "Sin paciente"
        medico_str = f"Dr. {self.medico_principal.apellido}" if self.medico_principal else "Sin médico"
        fecha_str = self.fecha_admision.strftime('%Y-%m-%d') if self.fecha_admision else "Sin fecha"
        return f"Atención #{self.id} - {paciente_str} con {medico_str} - {fecha_str} ({self.get_estado_clinico_display()})"


class ConsultaAmbulatoria(TimestampedModel):
    """
    Registro específico para una consulta ambulatoria.
    """

    atencion = models.OneToOneField(Atencion, on_delete=models.CASCADE, primary_key=True, related_name="consulta_ambulatoria")
    anamnesis = models.TextField(blank=True, null=True)
    examen_fisico = models.TextField(blank=True, null=True)
    diagnostico_presuntivo = models.TextField(blank=True, null=True)
    plan_manejo = models.TextField(blank=True, null=True)
    antecedentes_relevantes = models.TextField(blank=True, null=True)
    alergias = models.TextField(blank=True, null=True)
    medicacion_actual = models.TextField(blank=True, null=True)
    diagnostico_definitivo = models.TextField(blank=True, null=True)
    observaciones_medicas = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Consulta de Atención {self.atencion_id}"


class RegistroProcedimiento(TimestampedModel):
    """
    Registro para estudios y procedimientos (ej. Eco Doppler, Estudios).
    """

    atencion = models.OneToOneField(Atencion, on_delete=models.CASCADE, primary_key=True, related_name="registro_procedimiento")
    descripcion_procedimiento = models.CharField(max_length=255)
    informe_medico = models.TextField(blank=True, null=True)
    hallazgos = models.TextField(blank=True, null=True)
    estudio = models.ForeignKey(
        EstudioDiagnostico,
        on_delete=models.SET_NULL,
        related_name='registros_procedimiento',
        null=True,
        blank=True
    )
    procedimiento = models.ForeignKey(
        ProcedimientoCatalogo,
        on_delete=models.SET_NULL,
        related_name='registros_procedimiento',
        null=True,
        blank=True
    )
    profesional_asistente = models.ForeignKey(
        Medico,
        on_delete=models.SET_NULL,
        related_name='procedimientos_asistente',
        null=True,
        blank=True
    )

    class TipoProcedimiento(models.TextChoices):
        DIAGNOSTICO = 'DIAGNOSTICO', 'Diagnóstico'
        TERAPEUTICO = 'TERAPEUTICO', 'Terapéutico'

    tipo_procedimiento = models.CharField(
        max_length=20,
        choices=TipoProcedimiento.choices,
        null=True,
        blank=True
    )
    complicaciones = models.TextField(blank=True, null=True)
    adjunto_resultado = models.FileField(upload_to='emr/procedimientos/', blank=True, null=True)

    def __str__(self):
        return f"Procedimiento de Atención {self.atencion_id}"


class RegistroQuirurgico(TimestampedModel):
    """
    Registro específico para intervenciones de Hemodinamia y Cirugía.
    """

    atencion = models.OneToOneField(Atencion, on_delete=models.CASCADE, primary_key=True, related_name="registro_quirurgico")
    anestesista = models.ForeignKey(Medico, on_delete=models.PROTECT, related_name="anestesias_realizadas")
    diagnostico_preoperatorio = models.TextField()
    protocolo_quirurgico = models.TextField()
    recuento_instrumental_ok = models.BooleanField(default=False)
    procedimiento = models.ForeignKey(
        ProcedimientoCatalogo,
        on_delete=models.SET_NULL,
        related_name='registros_quirurgicos',
        null=True,
        blank=True
    )
    diagnostico_postoperatorio = models.TextField(blank=True, null=True)
    hallazgos_operatorios = models.TextField(blank=True, null=True)
    complicaciones = models.TextField(blank=True, null=True)
    equipo_quirurgico = models.JSONField(default=list, blank=True)
    consentimiento_informado = models.FileField(
        upload_to='emr/consentimientos/',
        blank=True,
        null=True
    )
    documentos_adjuntos = models.ManyToManyField(
        'emr.Documento',
        related_name='registros_quirurgicos',
        blank=True
    )

    def __str__(self):
        return f"Cirugía de Atención {self.atencion_id}"