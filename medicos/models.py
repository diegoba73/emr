from django.db import models
from django.conf import settings

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
        verbose_name="Usuario del Sistema"
    )
    
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
        ordering = ['user__last_name', 'user__first_name'] # Ordenar por apellido y luego por nombre

    def __str__(self):
        return f"{self.user.last_name}, {self.user.first_name} ({self.especialidad.nombre if self.especialidad else 'Sin Especialidad'})"
    
    @property
    def nombre(self):
        return self.user.first_name
    
    @property
    def apellido(self):
        return self.user.last_name
    
    @property
    def email(self):
        return self.user.email
    
    @property
    def telefono(self):
        return self.user.telefono