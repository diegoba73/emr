from django.db import models
from django.utils import timezone
from datetime import timedelta


class Sector(models.Model):
    """Sectores de internación (UCO, UCE)"""
    nombre = models.CharField(max_length=50, unique=True, verbose_name="Nombre del Sector")
    
    class Meta:
        verbose_name = "Sector"
        verbose_name_plural = "Sectores"
        ordering = ['nombre']
    
    def __str__(self):
        return self.nombre


class Cama(models.Model):
    """Camas de internación"""
    ESTADO_CHOICES = [
        ('DISPONIBLE', 'Disponible'),
        ('OCUPADA', 'Ocupada'),
        ('LIMPIEZA', 'En Limpieza'),
        ('MANTENIMIENTO', 'En Mantenimiento'),
    ]
    
    nombre = models.CharField(max_length=50, verbose_name="Nombre de la Cama")
    sector = models.ForeignKey(
        Sector,
        on_delete=models.CASCADE,
        related_name='camas',
        verbose_name="Sector"
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='DISPONIBLE',
        verbose_name="Estado"
    )
    aislada = models.BooleanField(
        default=False,
        verbose_name="Cama Aislada"
    )
    
    class Meta:
        verbose_name = "Cama"
        verbose_name_plural = "Camas"
        ordering = ['sector', 'nombre']
        unique_together = ['nombre', 'sector']
    
    def __str__(self):
        return f"{self.nombre} - {self.sector.nombre}"


class Internacion(models.Model):
    """Internaciones de pacientes"""
    paciente = models.ForeignKey(
        'pacientes.Paciente',
        on_delete=models.CASCADE,
        related_name='internaciones_camas',
        verbose_name="Paciente"
    )
    cama = models.ForeignKey(
        Cama,
        on_delete=models.CASCADE,
        related_name='internaciones',
        verbose_name="Cama"
    )
    medico = models.ForeignKey(
        'medicos.Medico',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='internaciones_camas',
        verbose_name="Médico"
    )
    fecha_ingreso = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Ingreso")
    fecha_alta = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Alta")
    diagnostico_cie = models.ForeignKey(
        'catalogos.DiagnosticoCIE10',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='internaciones',
        verbose_name="Diagnóstico CIE-10"
    )
    diagnostico_ingreso = models.TextField(null=True, blank=True, verbose_name="Diagnóstico de Ingreso (texto libre)")
    activo = models.BooleanField(default=True, verbose_name="Activa")
    
    class Meta:
        verbose_name = "Internación"
        verbose_name_plural = "Internaciones"
        ordering = ['-fecha_ingreso']
    
    def __str__(self):
        return f"Internación {self.paciente.apellido}, {self.paciente.nombre} - {self.cama.nombre}"
    
    def save(self, *args, **kwargs):
        # Si es una nueva internación (no tiene ID aún)
        if not self.pk:
            # Verificar que la cama esté disponible
            if self.cama.estado != 'DISPONIBLE':
                raise ValueError(f"La cama {self.cama.nombre} no está disponible. Estado actual: {self.cama.estado}")
            
            # Marcar cama como ocupada
            self.cama.estado = 'OCUPADA'
            self.cama.save()
        else:
            # Si es una actualización
            original = Internacion.objects.get(pk=self.pk)
            cama_cambio = original.cama.id != self.cama.id
            
            # Si se está dando de alta
            if not original.fecha_alta and self.fecha_alta:
                # Se está dando de alta
                self.activo = False
                # Cambiar estado de cama a LIMPIEZA
                self.cama.estado = 'LIMPIEZA'
                self.cama.save()
            # Si se está cambiando de cama (y no es un alta)
            elif cama_cambio and (not self.fecha_alta or original.fecha_alta):
                # Guardar primero la internación para evitar problemas de estado
                super().save(*args, **kwargs)
                
                # Luego actualizar estados de camas
                # Liberar la cama original solo si no tiene otra internación activa
                # Usar self.__class__ para evitar conflicto de nombres
                tiene_otra_internacion = self.__class__.objects.filter(
                    cama=original.cama,
                    activo=True
                ).exclude(pk=self.pk).exists()
                
                if not tiene_otra_internacion:
                    original.cama.estado = 'DISPONIBLE'
                    original.cama.save()
                
                # Ocupar la nueva cama
                self.cama.estado = 'OCUPADA'
                self.cama.save()
                
                return  # Ya guardamos arriba, no volver a guardar
        
        super().save(*args, **kwargs)
    
    @property
    def dias_internacion(self):
        """Calcula los días de internación"""
        if self.fecha_alta:
            return (self.fecha_alta - self.fecha_ingreso).days
        else:
            return (timezone.now() - self.fecha_ingreso).days
