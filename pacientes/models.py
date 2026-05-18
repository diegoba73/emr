from django.db import models
from django.conf import settings

class Paciente(models.Model):
    """
    Modelo para pacientes del sistema.
    Almacena TODA la información del paciente directamente en esta tabla.
    La relación con User es opcional.
    """
    # Relación con el usuario del sistema (OPCIONAL)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='paciente',
        verbose_name="Usuario del Sistema",
        blank=True,
        null=True
    )
    
    # Información personal del paciente (almacenada directamente en esta tabla)
    nombre = models.CharField(max_length=100, verbose_name="Nombre", null=True, blank=True)
    apellido = models.CharField(max_length=100, verbose_name="Apellido", null=True, blank=True)
    dni = models.CharField(max_length=20, unique=True, verbose_name="DNI / Documento")
    fecha_nacimiento = models.DateField(blank=True, null=True, verbose_name="Fecha de Nacimiento")
    sexo = models.CharField(
        max_length=1,
        choices=[('M', 'Masculino'), ('F', 'Femenino'), ('O', 'Otro')],
        blank=True,
        null=True,
        verbose_name="Sexo"
    )
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

    # Trazabilidad operativa (usuario staff que creó/modificó la ficha; distinto de ``user`` portal)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pacientes_creados",
        verbose_name="Creado por",
        help_text="Usuario operador que dio de alta la ficha (no la cuenta portal del paciente).",
    )
    modificado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pacientes_modificados",
        verbose_name="Modificado por",
        help_text="Último usuario operador que modificó la ficha.",
    )

    class Meta:
        verbose_name = "Paciente"
        verbose_name_plural = "Pacientes"
        ordering = ['apellido', 'nombre']
        indexes = [
            models.Index(fields=['apellido'], name='paciente_apellido_idx'),
            models.Index(fields=['nombre'], name='paciente_nombre_idx'),
        ]

    def __str__(self):
        return f"{self.apellido}, {self.nombre} ({self.dni})"
    
    @property
    def nombre_completo(self):
        """Nombre completo del paciente. Tolera valores ``None``.

        Si ``nombre`` y ``apellido`` están vacíos, devuelve ``"Paciente {dni}"``
        para que la UI nunca muestre la cadena literal ``"None None"``.
        """
        nombre = (self.nombre or "").strip()
        apellido = (self.apellido or "").strip()
        completo = f"{nombre} {apellido}".strip()
        return completo or f"Paciente {self.dni}"

    @property
    def edad(self):
        """Calcula la edad del paciente en años cumplidos.

        Devuelve ``None`` si no hay fecha de nacimiento. Si la fecha es futura,
        el resultado puede ser ``0`` o negativo (caso borde explícito).
        """
        fecha_nac = self.fecha_nacimiento
        if not fecha_nac:
            return None
        from datetime import date

        today = date.today()
        return today.year - fecha_nac.year - (
            (today.month, today.day) < (fecha_nac.month, fecha_nac.day)
        )
