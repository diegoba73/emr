from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import time

# Modelo para las Especialidades Médicas
class Especialidad(models.Model):
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre de la Especialidad")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")

    class Meta:
        verbose_name = "Especialidad"
        verbose_name_plural = "Especialidades"
        ordering = ['nombre'] # Ordenar por nombre de especialidad

    def __str__(self):
        return self.nombre

# Modelo para los Médicos
class Medico(models.Model):
    # Relación con el usuario del sistema
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='medico',
        verbose_name="Usuario del Sistema",
        blank=True,
        null=True
    )

    # Información básica independiente del usuario
    nombre = models.CharField(max_length=100, blank=True, null=True, verbose_name="Nombre")
    apellido = models.CharField(max_length=100, blank=True, null=True, verbose_name="Apellido")

    # Información profesional específica
    matricula = models.CharField(max_length=50, unique=True, verbose_name="Matrícula Profesional")

    # Relación con el modelo Especialidad (Un médico tiene una especialidad)
    especialidad = models.ForeignKey(
        Especialidad,
        on_delete=models.SET_NULL, # Si se borra la especialidad, el campo en Médico se pone a NULL
        null=True,
        blank=True,
        related_name='medicos', # Nombre inverso para acceder a los médicos desde la especialidad
        verbose_name="Especialidad"
    )

    # Campos adicionales para futura integración con IA (ej. áreas de interés, datos de rendimiento)
    areas_interes_ia = models.TextField(blank=True, null=True, verbose_name="Áreas de Interés para IA (Ej. Patologías específicas)")
    # Podríamos añadir campos para un "perfil de rendimiento" o "experiencia en diagnósticos" si los datos están disponibles

    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Registro")
    ultima_actualizacion = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")

    class Meta:
        verbose_name = "Médico"
        verbose_name_plural = "Médicos"
        ordering = ['apellido', 'nombre', 'user__last_name', 'user__first_name'] # Ordenar por apellido y luego por nombre

    def __str__(self):
        nombre = self.apellido or (self.user.last_name if self.user else '')
        nombre = nombre.strip() if nombre else ''
        nombre2 = self.nombre or (self.user.first_name if self.user else '')
        nombre2 = nombre2.strip() if nombre2 else ''
        nombre_completo = f"{nombre}, {nombre2}".strip(', ')
        if not nombre_completo:
            nombre_completo = f"Médico {self.id}"
        especialidad = self.especialidad.nombre if self.especialidad else 'Sin Especialidad'
        return f"{nombre_completo} ({especialidad})"

    @property
    def email(self):
        if self.user:
            return self.user.email
        return None
    
    @property
    def telefono(self):
        if self.user:
            return self.user.telefono
        return None

    @property
    def nombre_completo(self):
        primer_nombre = self.nombre or (self.user.first_name if self.user else '')
        apellido = self.apellido or (self.user.last_name if self.user else '')
        nombre_completo = f"{primer_nombre} {apellido}".strip()
        return nombre_completo or f"Médico {self.id}"


# Disponibilidad semanal del médico
class DisponibilidadMedico(models.Model):
    DIAS_SEMANA = [
        (0, 'Lunes'), (1, 'Martes'), (2, 'Miércoles'), (3, 'Jueves'), (4, 'Viernes'), (5, 'Sábado'), (6, 'Domingo')
    ]

    medico = models.ForeignKey(Medico, on_delete=models.CASCADE, related_name='disponibilidades')
    dia_semana = models.IntegerField(choices=DIAS_SEMANA)
    hora_inicio = models.TimeField(default=time(8, 0))
    hora_fin = models.TimeField(default=time(17, 0))
    duracion_slot_min = models.PositiveIntegerField(default=30)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Disponibilidad de Médico'
        verbose_name_plural = 'Disponibilidades de Médico'
        ordering = ['medico', 'dia_semana', 'hora_inicio']
        unique_together = ('medico', 'dia_semana', 'hora_inicio', 'hora_fin')

    def __str__(self):
        return f"{self.medico} - {self.get_dia_semana_display()} {self.hora_inicio}-{self.hora_fin} ({self.duracion_slot_min}m)"


# Excepciones puntuales (bloqueos o cambios de horario por fecha)
class ExcepcionMedico(models.Model):
    TIPO = [
        ('BLOQUEO', 'No atiende'),
        ('AJUSTE', 'Ajuste horario'),
    ]

    medico = models.ForeignKey(Medico, on_delete=models.CASCADE, related_name='excepciones')
    fecha = models.DateField()
    tipo = models.CharField(max_length=10, choices=TIPO, default='BLOQUEO')
    hora_inicio = models.TimeField(null=True, blank=True)
    hora_fin = models.TimeField(null=True, blank=True)
    motivo = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = 'Excepción de Médico'
        verbose_name_plural = 'Excepciones de Médico'
        ordering = ['medico', '-fecha']
        unique_together = ('medico', 'fecha', 'tipo', 'hora_inicio', 'hora_fin')

    def __str__(self):
        rango = f" {self.hora_inicio}-{self.hora_fin}" if self.hora_inicio and self.hora_fin else ''
        return f"{self.medico} - {self.fecha} {self.tipo}{rango}"