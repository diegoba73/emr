from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from pacientes.models import Paciente
from medicos.models import Medico
from integracion_lims import lims_service
import logging

logger = logging.getLogger(__name__)

class Solicitud(models.Model):
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('EN_PROCESO', 'En Proceso'),
        ('COMPLETADA', 'Completada'),
        ('CANCELADA', 'Cancelada'),
        ('ERROR', 'Error'),
    ]
    
    TIPO_SOLICITUD_CHOICES = [
        ('EXAMEN_LABORATORIO', 'Examen de Laboratorio'),
        ('ESTUDIO_IMAGEN', 'Estudio de Imagen'),
        ('CONSULTA_ESPECIALISTA', 'Consulta con Especialista'),
        ('PROCEDIMIENTO', 'Procedimiento'),
        ('OTRO', 'Otro'),
    ]
    
    # Campos básicos
    paciente = models.ForeignKey(
        Paciente, 
        on_delete=models.CASCADE,
        related_name='solicitudes',
        verbose_name="Paciente"
    )
    medico_solicitante = models.ForeignKey(
        Medico, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='solicitudes_realizadas',
        verbose_name="Médico Solicitante"
    )
    medicos_asignados = models.ManyToManyField(
        Medico,
        related_name='solicitudes_asignadas',
        blank=True,
        verbose_name="Médicos Asignados"
    )
    
    # Información de la solicitud
    tipo_solicitud = models.CharField(
        max_length=50,
        choices=TIPO_SOLICITUD_CHOICES,
        default='EXAMEN_LABORATORIO',
        verbose_name="Tipo de Solicitud"
    )
    descripcion = models.TextField(
        blank=True,
        verbose_name="Descripción"
    )
    observaciones = models.TextField(
        blank=True,
        verbose_name="Observaciones"
    )
    
    # Fechas
    fecha_solicitud = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Solicitud"
    )
    fecha_limite = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha Límite"
    )
    fecha_completada = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha Completada"
    )
    
    # Estado y seguimiento
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='PENDIENTE',
        verbose_name="Estado"
    )
    prioridad = models.CharField(
        max_length=20,
        choices=[
            ('BAJA', 'Baja'),
            ('NORMAL', 'Normal'),
            ('ALTA', 'Alta'),
            ('URGENTE', 'Urgente'),
        ],
        default='NORMAL',
        verbose_name="Prioridad"
    )
    
    # Selección de LIMS (persistencia local)
    lims_paneles = models.JSONField(default=list, blank=True, verbose_name="Paneles LIMS seleccionados")
    lims_tipos_examen = models.JSONField(default=list, blank=True, verbose_name="Tipos de examen LIMS seleccionados")
    
    # Integración con LIMS
    lims_id = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        unique=True, 
        verbose_name="ID de solicitud en LIMS"
    )
    sincronizado_lims = models.BooleanField(
        default=False,
        verbose_name="Sincronizado con LIMS"
    )
    ultima_sincronizacion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Última Sincronización"
    )
    
    # Campos de auditoría
    creado_por = models.ForeignKey(
        'usuarios.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solicitudes_creadas',
        verbose_name="Creado por"
    )
    modificado_por = models.ForeignKey(
        'usuarios.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solicitudes_modificadas',
        verbose_name="Modificado por"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Solicitud"
        verbose_name_plural = "Solicitudes"
        ordering = ['-fecha_solicitud']
        indexes = [
            models.Index(fields=['estado', 'fecha_solicitud']),
            models.Index(fields=['paciente', 'estado']),
            models.Index(fields=['medico_solicitante', 'estado']),
        ]

    def __str__(self):
        return f"Solicitud {self.id} - {self.paciente.nombre_completo} - {self.get_estado_display()}"

    def clean(self):
        """
        Validaciones personalizadas.
        Valida que fecha_limite > fecha_solicitud (si existe).
        """
        if self.fecha_limite and self.fecha_solicitud:
            if self.fecha_limite <= self.fecha_solicitud:
                raise ValidationError({
                    'fecha_limite': 'La fecha límite debe ser posterior a la fecha de solicitud.'
                })
        
        if self.fecha_completada and self.fecha_completada > timezone.now():
            raise ValidationError({
                'fecha_completada': 'La fecha de completado no puede ser futura.'
            })

    def save(self, *args, **kwargs):
        """Valida y persiste; no envía a sistemas externos (LIMS solo vía ViewSet)."""
        # Validar antes de guardar
        self.clean()

        super().save(*args, **kwargs)

        # Actualizar fecha de completado si el estado cambió a COMPLETADA
        if self.estado == 'COMPLETADA' and not self.fecha_completada:
            self.fecha_completada = timezone.now()
            super().save(update_fields=['fecha_completada'])

    def _enviar_a_lims(self):
        """Envía la solicitud al sistema LIMS"""
        try:
            solicitud_data = {
                'external_id': str(self.id),
                'paciente_id': self.paciente.id,
                'paciente_nombre': getattr(self.paciente, 'nombre_completo', None),
                'medico_id': self.medico_solicitante.id if self.medico_solicitante else None,
                'medico_solicitante_id': self.medico_solicitante.id if self.medico_solicitante else None,
                'medico_nombre': f"{getattr(self.medico_solicitante, 'nombre', '')} {getattr(self.medico_solicitante, 'apellido', '')}".strip() if self.medico_solicitante else None,
                'descripcion': self.descripcion,
                'observaciones': self.observaciones,
                'prioridad': self.prioridad,
                'paneles': self.lims_paneles or [],
                'tipos_examen': self.lims_tipos_examen or [],
            }
            
            response = lims_service.enviar_solicitud_a_lims(solicitud_data)
            
            if response and 'id' in response:
                self.lims_id = response['id']
                self.sincronizado_lims = True
                self.ultima_sincronizacion = timezone.now()
                super().save(update_fields=['lims_id', 'sincronizado_lims', 'ultima_sincronizacion'])
                logger.info(f"Solicitud {self.id} enviada exitosamente al LIMS con ID: {self.lims_id}")
            else:
                logger.error(f"Error al enviar solicitud {self.id} al LIMS: Respuesta inválida")
                
        except Exception as e:
            logger.error(f"Error al enviar solicitud {self.id} al LIMS: {str(e)}")

    def marcar_como_completada(self):
        """Marca la solicitud como completada"""
        self.estado = 'COMPLETADA'
        self.fecha_completada = timezone.now()
        self.save()

    def cancelar(self):
        """Cancela la solicitud"""
        self.estado = 'CANCELADA'
        self.save()

    def reabrir(self):
        """Reabre una solicitud cancelada o completada"""
        if self.estado in ['CANCELADA', 'COMPLETADA']:
            self.estado = 'PENDIENTE'
            self.fecha_completada = None
            self.save()

    @property
    def dias_pendiente(self):
        """
        Calcula los días pendientes de la solicitud.
        Retorna (now - fecha_solicitud).days si está pendiente, 0 en caso contrario.
        """
        if self.estado == 'PENDIENTE':
            return (timezone.now() - self.fecha_solicitud).days
        return 0

    @property
    def esta_vencida(self):
        """
        Verifica si la solicitud está vencida.
        True si fecha_limite < now y no está completada/cancelada.
        """
        if self.fecha_limite and self.estado not in ['COMPLETADA', 'CANCELADA']:
            return timezone.now() > self.fecha_limite
        return False

    def get_medicos_asignados_display(self):
        """Retorna una representación legible de los médicos asignados"""
        medicos = self.medicos_asignados.all()
        if medicos:
            return ", ".join([medico.nombre_completo for medico in medicos])
        return "Sin asignar"