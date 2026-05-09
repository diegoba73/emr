from django.db import models
from django.utils import timezone

from pacientes.models import Paciente
from medicos.models import Medico
from turnos.models import Turno  # Vincula opcionalmente la consulta con el turno que la generó


def _paciente_label(paciente) -> str:
    """Devuelve una etiqueta legible para un ``Paciente``, tolerando ``None``.

    Centraliza la lógica para que ``__str__`` de varios modelos no rompa si
    ``apellido``/``nombre`` están vacíos. Prefiere ``nombre_completo`` (que
    ya tolera ``None`` desde el bloque ``pacientes``) y cae a DNI si todo lo
    demás es vacío.
    """
    if paciente is None:
        return "Paciente desconocido"
    nombre_completo = getattr(paciente, "nombre_completo", "") or ""
    if nombre_completo.strip():
        return nombre_completo.strip()
    apellido = (getattr(paciente, "apellido", "") or "").strip()
    nombre = (getattr(paciente, "nombre", "") or "").strip()
    if apellido or nombre:
        return f"{apellido}, {nombre}".strip(", ")
    dni = getattr(paciente, "dni", None)
    if dni:
        return f"Paciente {dni}"
    return "Paciente sin datos"


# Modelo para la Historia Clínica general de un Paciente
class HistoriaClinica(models.Model):
    paciente = models.OneToOneField(
        Paciente,
        on_delete=models.CASCADE,
        primary_key=True, # La HC se identifica por el paciente
        verbose_name="Paciente"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    ultima_actualizacion = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")
    # Aquí se podrían añadir campos para un resumen inicial, antecedentes generales no capturados en paciente

    class Meta:
        verbose_name = "Historia Clínica"
        verbose_name_plural = "Historias Clínicas"
        ordering = ['paciente__apellido', 'paciente__nombre']

    def __str__(self):
        return f"Historia Clínica de {_paciente_label(self.paciente)}"


# Modelo para cada Consulta (visita médica)
class Consulta(models.Model):
    historia_clinica = models.ForeignKey(
        HistoriaClinica,
        on_delete=models.CASCADE,
        related_name='consultas',
        verbose_name="Historia Clínica"
    )
    medico = models.ForeignKey(
        Medico,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='consultas',
        verbose_name="Médico Responsable"
    )
    turno = models.OneToOneField( # Una consulta puede venir de un turno específico
        Turno,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Turno Asociado"
    )

    fecha_hora_consulta = models.DateTimeField(verbose_name="Fecha y Hora de la Consulta")
    motivo_consulta_detalle = models.TextField(verbose_name="Motivo de Consulta (Detalle)")
    anamnesis = models.TextField(blank=True, null=True, verbose_name="Anamnesis") # Interrogatorio
    examen_fisico = models.TextField(blank=True, null=True, verbose_name="Examen Físico")
    diagnostico_presuntivo = models.TextField(blank=True, null=True, verbose_name="Diagnóstico Presuntivo (Texto Libre)")
    plan_manejo = models.TextField(blank=True, null=True, verbose_name="Plan de Manejo / Conducta")
    notas_medicas = models.TextField(blank=True, null=True, verbose_name="Notas Adicionales del Médico")


    # Campos para IA (Análisis de Texto Clínico, Extracción de Entidades)
    # Aquí la IA podría procesar Anamnesis, Examen Físico, Diagnóstico Presuntivo y Plan de Manejo
    # y guardar insights estructurados en otros modelos o en un campo JSONField si fuera necesario.
    # Por ahora, los dejamos como TextField para la recopilación de datos.

    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Registro")
    ultima_actualizacion = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")


    class Meta:
        verbose_name = "Consulta"
        verbose_name_plural = "Consultas"
        ordering = ['-fecha_hora_consulta']  # Ordenar por fecha de consulta descendente (más reciente primero)
        indexes = [
            models.Index(fields=['-fecha_hora_consulta'], name='hist_consulta_fecha_idx'),
        ]

    def __str__(self):
        paciente_str = (
            _paciente_label(self.historia_clinica.paciente)
            if self.historia_clinica_id
            else "Paciente desconocido"
        )
        medico_str = (
            f"Dr. {self.medico.apellido}" if (self.medico and self.medico.apellido) else "Sin médico"
        )
        fecha_str = self.fecha_hora_consulta.strftime('%Y-%m-%d %H:%M') if self.fecha_hora_consulta else "Sin fecha"
        return f"Consulta de {paciente_str} con {medico_str} - {fecha_str}"


# Modelo para Catálogo de Síntomas (útil para estandarizar datos para IA)
class Sintoma(models.Model):
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre del Síntoma")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    # Campos para IA: taxonomía del síntoma, relación con enfermedades (futuro)

    class Meta:
        verbose_name = "Síntoma"
        verbose_name_plural = "Síntomas"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


# Modelo para Diagnósticos Específicos de una Consulta (MEJORADO)
class Diagnostico(models.Model):
    consulta = models.ForeignKey(
        Consulta,
        on_delete=models.CASCADE,
        related_name='diagnosticos',
        verbose_name="Consulta"
    )
    # Ahora vinculamos con el catálogo CIE-10 estandarizado
    diagnostico_cie = models.ForeignKey(
        'catalogos.DiagnosticoCIE10',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Diagnóstico CIE-10"
    )
    # Mantenemos el texto libre para casos especiales
    nombre_diagnostico = models.CharField(max_length=255, verbose_name="Diagnóstico Principal")
    descripcion_diagnostico = models.TextField(blank=True, null=True, verbose_name="Descripción del Diagnóstico")
    # Posible relación con Sintomas (muchos a muchos)
    sintomas_asociados = models.ManyToManyField(Sintoma, blank=True, verbose_name="Síntomas Asociados")

    # Campos para IA: Confianza del diagnóstico (si lo da una IA), relevancia, etc.
    # Nivel de confianza si es sugerido por IA (Float, blank=True, null=True)
    # Recomendaciones de IA para pruebas adicionales (TextField)

    fecha_diagnostico = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Diagnóstico")

    class Meta:
        verbose_name = "Diagnóstico"
        verbose_name_plural = "Diagnósticos"
        ordering = ['-fecha_diagnostico', 'nombre_diagnostico']

    def __str__(self):
        return f"Diagnóstico: {self.nombre_diagnostico} ({self.consulta.fecha_hora_consulta.strftime('%d-%m-%Y')})"


# Modelo para Tratamientos Asociados a una Consulta
class Tratamiento(models.Model):
    consulta = models.ForeignKey(
        Consulta,
        on_delete=models.CASCADE,
        related_name='tratamientos',
        verbose_name="Consulta"
    )
    tipo_tratamiento = models.CharField(
        max_length=50,
        choices=[
            ('MEDICAMENTOSO', 'Medicamentoso'),
            ('PROCEDIMIENTO', 'Procedimiento'),
            ('TERAPIA', 'Terapia'),
            ('REPOSO', 'Reposo'),
            ('OTROS', 'Otros'),
        ],
        verbose_name="Tipo de Tratamiento"
    )
    descripcion_tratamiento = models.TextField(verbose_name="Descripción del Tratamiento")
    dosis_frecuencia = models.CharField(max_length=255, blank=True, null=True, verbose_name="Dosis / Frecuencia")
    fecha_inicio = models.DateField(blank=True, null=True, verbose_name="Fecha de Inicio")
    fecha_fin_estimada = models.DateField(blank=True, null=True, verbose_name="Fecha de Fin Estimada")
    instrucciones_adicionales = models.TextField(blank=True, null=True, verbose_name="Instrucciones Adicionales")

    # Campos para IA: Efectividad del tratamiento (si hay datos de seguimiento), sugerencias de alternativas
    # Estado de respuesta (ej. 'Mejoría', 'Estable', 'Empeoramiento')
    # Recomendación de IA (TextField)

    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Registro")

    class Meta:
        verbose_name = "Tratamiento"
        verbose_name_plural = "Tratamientos"
        ordering = ['fecha_registro', 'tipo_tratamiento']

    def __str__(self):
        paciente_str = (
            _paciente_label(self.consulta.historia_clinica.paciente)
            if self.consulta and self.consulta.historia_clinica_id
            else "Paciente desconocido"
        )
        fecha_str = self.consulta.fecha_hora_consulta.strftime('%Y-%m-%d') if (self.consulta and self.consulta.fecha_hora_consulta) else "Sin fecha"
        return f"{self.get_tipo_tratamiento_display()} - {paciente_str} ({fecha_str})"


# NUEVO: Modelo para Prescripciones Médicas
class Prescripcion(models.Model):
    """Prescripciones médicas detalladas"""
    consulta = models.ForeignKey(
        Consulta,
        on_delete=models.CASCADE,
        related_name='prescripciones',
        verbose_name="Consulta"
    )
    medicamento = models.ForeignKey(
        'catalogos.Medicamento',
        on_delete=models.PROTECT,  # Integridad histórica: no borrar medicamentos con prescripciones
        verbose_name="Medicamento"
    )
    dosis = models.CharField(max_length=100, verbose_name="Dosis")
    frecuencia = models.CharField(max_length=100, verbose_name="Frecuencia")
    duracion = models.CharField(max_length=100, verbose_name="Duración del Tratamiento")
    instrucciones = models.TextField(blank=True, null=True, verbose_name="Instrucciones Especiales")
    fecha_prescripcion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Prescripción")
    activa = models.BooleanField(default=True, verbose_name="Prescripción Activa")
    
    # Campos para seguimiento
    fecha_inicio = models.DateField(blank=True, null=True, verbose_name="Fecha de Inicio")
    fecha_fin = models.DateField(blank=True, null=True, verbose_name="Fecha de Fin")
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")

    class Meta:
        verbose_name = "Prescripción"
        verbose_name_plural = "Prescripciones"
        ordering = ['-fecha_prescripcion']

    def __str__(self):
        # Formato legible: "Ibuprofeno 600mg - Cada 8hs"
        medicamento_str = self.medicamento.nombre if self.medicamento else "Medicamento desconocido"
        concentracion_str = self.medicamento.concentracion if self.medicamento else ""
        dosis_str = f"{concentracion_str} - {self.dosis}" if concentracion_str else self.dosis
        frecuencia_str = f" - {self.frecuencia}" if self.frecuencia else ""
        return f"{medicamento_str} {dosis_str}{frecuencia_str}"


# NUEVO: Modelo para Internaciones
class Internacion(models.Model):
    """Internaciones de pacientes en áreas específicas"""
    ESTADO_CHOICES = [
        ('ACTIVA', 'Activa'),
        ('ALTA_MEDICA', 'Alta Médica'),
        ('ALTA_VOLUNTARIA', 'Alta Voluntaria'),
        ('TRANSFERENCIA', 'Transferencia a otro centro'),
        ('FALLECIMIENTO', 'Fallecimiento'),
    ]
    
    paciente = models.ForeignKey(
        'pacientes.Paciente',
        on_delete=models.CASCADE,
        related_name='internaciones',
        verbose_name="Paciente"
    )
    medico_responsable = models.ForeignKey(
        'medicos.Medico',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='internaciones_responsable',
        verbose_name="Médico Responsable"
    )
    cama = models.ForeignKey(
        'catalogos.CamaInternacion',
        on_delete=models.CASCADE,
        related_name='internaciones',
        verbose_name="Cama Asignada"
    )
    turno_origen = models.ForeignKey(
        'turnos.Turno',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='internaciones',
        verbose_name="Turno de Origen"
    )
    
    # Fechas importantes
    fecha_ingreso = models.DateTimeField(verbose_name="Fecha y Hora de Ingreso")
    fecha_alta = models.DateTimeField(blank=True, null=True, verbose_name="Fecha y Hora de Alta")
    fecha_estimada_alta = models.DateField(blank=True, null=True, verbose_name="Fecha Estimada de Alta")
    
    # Información clínica
    motivo_ingreso = models.TextField(verbose_name="Motivo de Ingreso")
    diagnostico_ingreso = models.TextField(blank=True, null=True, verbose_name="Diagnóstico de Ingreso")
    plan_tratamiento = models.TextField(blank=True, null=True, verbose_name="Plan de Tratamiento")
    
    # Estado y seguimiento
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='ACTIVA',
        verbose_name="Estado de la Internación"
    )
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")
    
    # Campos administrativos
    numero_internacion = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Número de Internación"
    )
    es_urgencia = models.BooleanField(default=False, verbose_name="Es Urgencia/Emergencia")
    
    # Campos de auditoría
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Registro")
    ultima_actualizacion = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")
    
    class Meta:
        verbose_name = "Internación"
        verbose_name_plural = "Internaciones"
        ordering = ['-fecha_ingreso']
    
    def __str__(self):
        paciente_str = _paciente_label(self.paciente)
        return f"Internación {self.numero_internacion} - {paciente_str} ({self.estado})"

    def save(self, *args, **kwargs):
        # Generar número de internación automáticamente si no existe
        if not self.numero_internacion:
            # ``timezone.now()`` respeta USE_TZ; antes se usaba
            # ``datetime.now()`` (naive) lo cual podía generar warnings y
            # comportamientos inconsistentes según la zona horaria activa.
            fecha_actual = timezone.now()
            prefijo = f"INT-{fecha_actual.strftime('%Y%m%d')}"
            ultima_internacion = Internacion.objects.filter(
                numero_internacion__startswith=prefijo
            ).order_by('-numero_internacion').first()

            if ultima_internacion:
                try:
                    ultimo_numero = int(ultima_internacion.numero_internacion.split('-')[-1])
                    nuevo_numero = ultimo_numero + 1
                except (ValueError, IndexError):
                    nuevo_numero = 1
            else:
                nuevo_numero = 1

            self.numero_internacion = f"{prefijo}-{nuevo_numero:03d}"

        super().save(*args, **kwargs)

    @property
    def duracion_dias(self):
        """Calcula la duración de la internación en días."""
        if self.fecha_alta:
            return (self.fecha_alta - self.fecha_ingreso).days
        return (timezone.now() - self.fecha_ingreso).days
    
    @property
    def centro_fisico(self):
        """Obtiene el centro físico de la cama"""
        return self.cama.area.centro_fisico
    
    @property
    def area_internacion(self):
        """Obtiene el área de internación"""
        return self.cama.area