from django.db import models
from pacientes.models import Paciente
from medicos.models import Medico
from medicos.models import Especialidad
from catalogos.models import CentroFisico, TipoAtencion
from datetime import timedelta # Importamos timedelta para operaciones con tiempo

class Turno(models.Model):
    # Relaciones con Paciente y Medico
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name='turnos',
        verbose_name="Paciente",
        null=True,
        blank=True
    )
    medico = models.ForeignKey(
        Medico,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='turnos',
        verbose_name="Médico"
    )
    especialidad = models.ForeignKey(
        Especialidad,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Especialidad del Turno"
    )
    
    # NUEVO: Centro físico y tipo de atención
    centro_fisico = models.ForeignKey(
        CentroFisico,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='turnos',
        verbose_name="Centro Físico"
    )
    tipo_atencion = models.ForeignKey(
        TipoAtencion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='turnos',
        verbose_name="Tipo de Atención"
    )

    # Información del turno
    fecha_hora = models.DateTimeField(verbose_name="Fecha y Hora del Turno", null=True, blank=True)
    fecha_hora_inicio = models.DateTimeField(verbose_name="Fecha y Hora de Inicio")
    # Campo de fecha_hora_fin, ahora opcional en DB y formulario
    fecha_hora_fin = models.DateTimeField(blank=True, null=True, verbose_name="Fecha y Hora de Fin")
    motivo_consulta = models.TextField(blank=True, null=True, verbose_name="Motivo de Consulta")

    # Estado del turno
    ESTADO_CHOICES = [
        ('DISPONIBLE', 'Disponible'),
        ('RESERVADO', 'Reservado'),
        ('CONFIRMADO', 'Confirmado'),
        ('REALIZADO', 'Realizado'),
        ('CANCELADO', 'Cancelado'),
        ('REAGENDADO', 'Reagendado'),
    ]
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='DISPONIBLE',
        verbose_name="Estado del Turno"
    )

    # Campos para IA/Análisis de datos (futuro)
    notas_administrativas = models.TextField(blank=True, null=True, verbose_name="Notas Administrativas")

    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    ultima_modificacion = models.DateTimeField(auto_now=True, verbose_name="Última Modificación")


    class Meta:
        verbose_name = "Turno"
        verbose_name_plural = "Turnos"
        ordering = ['fecha_hora_inicio']
        # unique_together = ('medico', 'fecha_hora_inicio') # Puedes mantenerlo si quieres asegurar que un médico no tenga dos turnos exactamente a la misma hora

    def __str__(self):
        paciente_str = f"{self.paciente.apellido}, {self.paciente.nombre}" if self.paciente else "Sin Paciente"
        medico_str = f"Dr. {self.medico.apellido}" if self.medico else "Médico Desconocido"
        return f"Turno de {paciente_str} con {medico_str} el {self.fecha_hora_inicio.strftime('%d-%m-%Y %H:%M')} ({self.estado})"

    # --- AÑADIR ESTE MÉTODO save() ---
    def save(self, *args, **kwargs):
        # Si fecha_hora está establecida pero fecha_hora_inicio no, la copiamos
        if self.fecha_hora and not self.fecha_hora_inicio:
            self.fecha_hora_inicio = self.fecha_hora
        
        # Si la fecha_hora_fin no está establecida, la calculamos
        if self.fecha_hora_inicio and not self.fecha_hora_fin:
            # Duración predeterminada: 1 hora
            self.fecha_hora_fin = self.fecha_hora_inicio + timedelta(hours=1)
        super().save(*args, **kwargs) # Llama al método save original del modelo