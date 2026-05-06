from django.db import models
from pacientes.models import Paciente
from medicos.models import Medico

class SolicitudExamenLims(models.Model):
    # ID del objeto en el LIMS
    lims_id = models.CharField(max_length=100, unique=True, verbose_name="ID de la Solicitud en LIMS")

    # Relaciones con modelos locales del EMR
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='solicitudes_lims', verbose_name="Paciente")
    medico_solicitante = models.ForeignKey(Medico, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Médico Solicitante")

    # Campos de datos que se sincronizan desde el LIMS
    numero_solicitud = models.CharField(max_length=20, verbose_name="Número de Solicitud LIMS")
    fecha_solicitud = models.DateTimeField(verbose_name="Fecha de Solicitud")
    estado = models.CharField(max_length=20, verbose_name="Estado LIMS")

    class Meta:
        verbose_name = "Solicitud de Examen (LIMS)"
        verbose_name_plural = "Solicitudes de Exámenes (LIMS)"
        ordering = ['-fecha_solicitud']

    def __str__(self):
        return f"Solicitud LIMS {self.numero_solicitud} - {self.paciente.nombre_completo}"

class ResultadoExamenLims(models.Model):
    # ID del objeto en el LIMS
    lims_id = models.CharField(max_length=100, unique=True, verbose_name="ID del Resultado en LIMS")

    # Relación con la solicitud local
    solicitud_lims = models.ForeignKey(SolicitudExamenLims, on_delete=models.CASCADE, related_name='resultados_lims', verbose_name="Solicitud LIMS")

    # Campos de datos que se sincronizan desde el LIMS
    tipo_examen = models.CharField(max_length=200, verbose_name="Tipo de Examen")
    valor_numerico = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Valor Numérico")
    valor_texto = models.CharField(max_length=255, blank=True, verbose_name="Valor Texto")
    es_normal = models.BooleanField(default=True, verbose_name="¿Es Normal?")

    class Meta:
        verbose_name = "Resultado de Examen (LIMS)"
        verbose_name_plural = "Resultados de Exámenes (LIMS)"

    def __str__(self):
        return f"{self.tipo_examen} - Solicitud {self.solicitud_lims.numero_solicitud}"