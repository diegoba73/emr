from django.conf import settings
from django.db import models


class Profesional(models.Model):
    """Directorio de profesionales no médicos (nutrición, kinesiología, etc.)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profesional',
        verbose_name='Usuario del Sistema',
        blank=True,
        null=True,
    )
    nombre = models.CharField(max_length=100, blank=True, null=True, verbose_name='Nombre')
    apellido = models.CharField(max_length=100, blank=True, null=True, verbose_name='Apellido')
    matricula = models.CharField(max_length=50, unique=True, verbose_name='Matrícula / código')
    especialidad = models.ForeignKey(
        'medicos.Especialidad',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='profesionales',
        verbose_name='Especialidad',
    )
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Registro')
    ultima_actualizacion = models.DateTimeField(auto_now=True, verbose_name='Última Actualización')

    class Meta:
        verbose_name = 'Profesional'
        verbose_name_plural = 'Profesionales'
        ordering = ['apellido', 'nombre']

    def __str__(self):
        return self.nombre_completo

    @property
    def email(self):
        if self.user:
            return self.user.email
        return None

    @property
    def telefono(self):
        if self.user:
            return getattr(self.user, 'telefono', None)
        return None

    @property
    def nombre_completo(self):
        primer_nombre = self.nombre or (self.user.first_name if self.user else '')
        apellido = self.apellido or (self.user.last_name if self.user else '')
        nombre_completo = f'{primer_nombre} {apellido}'.strip()
        return nombre_completo or f'Profesional {self.id}'
