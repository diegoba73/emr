from django.db import models
from django.conf import settings
from pacientes.models import Paciente
from .validators import validar_tamanio_archivo, validar_extension_archivo


class ArchivoMedico(models.Model):
    TIPO_CHOICES = [
        ('DICOM', 'DICOM (.dcm)'),
        ('NIFTI', 'NIFTI (.nii, .nii.gz)'),
        ('RAYOS_X', 'Rayos X (imagen estandarizada)'),
        ('TOMOGRAFIA', 'Tomografía'),
        ('RESONANCIA', 'Resonancia Magnética'),
        ('ULTRASONIDO', 'Ultrasonido'),
        ('FOTO_CLINICA', 'Foto Clínica (.jpg, .png)'),
        ('PATOLOGIA', 'Patología (.tif, .png)'),
        ('PDF', 'Documento PDF'),
        ('OTRO', 'Otro'),
    ]

    # Información básica del archivo
    titulo = models.CharField(max_length=200, verbose_name="Título del Archivo")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    tipo_archivo = models.CharField(
        max_length=50,
        choices=TIPO_CHOICES,
        verbose_name="Tipo de Archivo"
    )

    # Archivo físico
    archivo = models.FileField(
        upload_to='archivos_medicos/%Y/%m/%d/',
        verbose_name="Archivo",
        validators=[validar_tamanio_archivo, validar_extension_archivo],
        blank=True,
        null=True
    )

    # Relaciones
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name='archivos',
        verbose_name="Paciente"
    )

    # Relación opcional con consulta específica
    consulta = models.ForeignKey(
        'historias_clinicas.Consulta',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='archivos',
        verbose_name="Consulta Asociada"
    )

    # Metadatos
    fecha_subida = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Subida")
    fecha_estudio = models.DateField(null=True, blank=True, verbose_name="Fecha del Estudio")
    subido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,  # Permitir que esté vacío
        verbose_name="Subido por"
    )

    # Información adicional
    es_urgente = models.BooleanField(default=False, verbose_name="Es Urgente")

    class Meta:
        verbose_name = "Archivo Médico"
        verbose_name_plural = "Archivos Médicos"
        ordering = ['-fecha_subida']

    def __str__(self):
        return self.titulo
