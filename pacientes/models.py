from django.db import models
from django.conf import settings

class Paciente(models.Model):
    # Relación con el usuario del sistema (opcional)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='paciente',
        verbose_name="Usuario del Sistema",
        null=True,
        blank=True
    )
    
    # Información personal básica
    nombre = models.CharField(max_length=100, verbose_name="Nombre", default="")
    apellido = models.CharField(max_length=100, verbose_name="Apellido", default="")
    dni = models.CharField(max_length=20, unique=True, verbose_name="DNI / Documento")
    fecha_nacimiento = models.DateField(null=True, blank=True, verbose_name="Fecha de Nacimiento")
    sexo = models.CharField(
        max_length=1,
        choices=[('M', 'Masculino'), ('F', 'Femenino')],
        null=True,
        blank=True,
        verbose_name="Sexo"
    )
    
    # Información de contacto
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    direccion = models.TextField(blank=True, null=True, verbose_name="Dirección")
    
    # Información de obra social
    obra_social = models.CharField(max_length=100, blank=True, null=True, verbose_name="Obra Social")
    numero_afiliado = models.CharField(max_length=50, blank=True, null=True, verbose_name="Número de Afiliado")
    
    # Información médica
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")
    antecedentes_personales = models.TextField(blank=True, null=True, verbose_name="Antecedentes Personales Relevantes")
    antecedentes_familiares = models.TextField(blank=True, null=True, verbose_name="Antecedentes Familiares Relevantes")
    
    # Metadatos del registro
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Registro")
    ultima_actualizacion = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")

    class Meta:
        verbose_name = "Paciente"
        verbose_name_plural = "Pacientes"
        ordering = ['user__last_name', 'user__first_name']

    def __str__(self):
        return f"{self.apellido}, {self.nombre} ({self.dni})"
    
    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"
    
    @property
    def edad(self):
        if self.fecha_nacimiento:
            from datetime import date
            today = date.today()
            return today.year - self.fecha_nacimiento.year - ((today.month, today.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day))
        return None
