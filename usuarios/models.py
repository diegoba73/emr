from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    """
    Modelo de usuario extendido con roles específicos para el EMR
    """
    ROL_CHOICES = [
        ('paciente', 'Paciente'),
        ('medico', 'Médico'),
        ('secretaria', 'Secretaria'),
        ('enfermeria', 'Enfermería'),
        ('laboratorio', 'Laboratorio'),
        ('bioquimico', 'Bioquímico'),
        ('kinesiologo', 'Kinesiólogo'),
        ('radiologo', 'Radiólogo'),
        ('ecografista', 'Ecografista'),
        ('fonoaudiologo', 'Fonoaudiólogo'),
        ('admin', 'Administrador'),
    ]
    
    rol = models.CharField(max_length=20, choices=ROL_CHOICES, default='paciente')
    telefono = models.CharField(max_length=25, blank=True, null=True)
    
    # Campos de verificación
    email_verificado = models.BooleanField(default=False)
    telefono_verificado = models.BooleanField(default=False)
    
    # Campos de auditoría
    fecha_registro = models.DateTimeField(auto_now_add=True)
    ultima_actividad = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        db_table = 'usuarios'
    
    def __str__(self):
        return f"{self.username} ({self.get_rol_display()})"
    
    @property
    def es_paciente(self):
        return self.rol == 'paciente'
    
    @property
    def es_medico(self):
        return self.rol == 'medico'
    
    @property
    def es_secretaria(self):
        return self.rol == 'secretaria'
    
    @property
    def es_admin(self):
        return self.rol == 'admin'
    
    @property
    def es_enfermeria(self):
        return self.rol == 'enfermeria'

    @property
    def es_profesional_estudio(self):
        from usuarios.roles import es_rol_estudio_complementario
        return es_rol_estudio_complementario(self.rol)
    
    def puede_ver_todos_los_turnos(self):
        """Determina si el usuario puede ver todos los turnos"""
        from usuarios.roles import es_agenda_turnos_lectura
        return self.rol in ['secretaria', 'admin'] or es_agenda_turnos_lectura(self.rol)
    
    def puede_gestionar_turnos(self):
        """Determina si el usuario puede gestionar turnos"""
        return self.rol in ['secretaria', 'admin', 'medico']
    
    def puede_ver_historia_clinica(self):
        """Determina si el usuario puede ver historias clínicas"""
        return self.rol in ['medico', 'admin']


class UserProfile(models.Model):
    """
    Perfil extendido para información adicional del usuario
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # Información personal adicional
    fecha_nacimiento = models.DateField(blank=True, null=True)
    genero = models.CharField(
        max_length=10,
        choices=[
            ('M', 'Masculino'),
            ('F', 'Femenino'),
            ('O', 'Otro'),
        ],
        blank=True,
        null=True
    )
    
    # Dirección
    direccion = models.TextField(blank=True, null=True)
    ciudad = models.CharField(max_length=100, blank=True, null=True)
    codigo_postal = models.CharField(max_length=10, blank=True, null=True)
    
    # Información médica (para pacientes)
    grupo_sanguineo = models.CharField(
        max_length=5,
        choices=[
            ('A+', 'A+'),
            ('A-', 'A-'),
            ('B+', 'B+'),
            ('B-', 'B-'),
            ('AB+', 'AB+'),
            ('AB-', 'AB-'),
            ('O+', 'O+'),
            ('O-', 'O-'),
        ],
        blank=True,
        null=True
    )
    
    alergias = models.TextField(blank=True, null=True, help_text='Lista de alergias conocidas')
    medicamentos_actuales = models.TextField(blank=True, null=True, help_text='Medicamentos que toma actualmente')
    
    # Información de contacto de emergencia
    contacto_emergencia_nombre = models.CharField(max_length=100, blank=True, null=True)
    contacto_emergencia_telefono = models.CharField(max_length=17, blank=True, null=True)
    contacto_emergencia_relacion = models.CharField(max_length=50, blank=True, null=True)
    
    # Campos de auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Perfil de Usuario'
        verbose_name_plural = 'Perfiles de Usuario'
        db_table = 'usuarios_profile'
    
    def __str__(self):
        return f"Perfil de {self.user.username}"
    
    def get_edad(self):
        """Calcula la edad del usuario"""
        if self.fecha_nacimiento:
            from datetime import date
            today = date.today()
            return today.year - self.fecha_nacimiento.year - (
                (today.month, today.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
            )
        return None


class Secretaria(models.Model):
    """
    Modelo para secretarias del sistema
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='secretaria')
    
    # Información específica de la secretaria
    legajo = models.CharField(max_length=20, unique=True, verbose_name="Legajo")
    sector = models.CharField(max_length=100, blank=True, null=True, verbose_name="Sector")
    
    # Campos de auditoría
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Registro")
    ultima_actualizacion = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")

    class Meta:
        verbose_name = "Secretaria"
        verbose_name_plural = "Secretarias"
        ordering = ['user__last_name', 'user__first_name']

    def __str__(self):
        return f"{self.user.last_name}, {self.user.first_name} (Legajo: {self.legajo})"
    
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
