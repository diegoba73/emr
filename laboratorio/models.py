from django.db import models
from django.db.models import Max
from pacientes.models import Paciente
from medicos.models import Medico
from django.utils import timezone
from historias_clinicas.models import Consulta


class TipoExamen(models.Model):
    """Tipos de exámenes de laboratorio disponibles"""
    codigo = models.CharField(max_length=20, unique=True, null=True, blank=True, verbose_name="Código")
    nombre = models.CharField(max_length=100, verbose_name="Nombre del Examen")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    precio = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Precio")
    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Tipo de Examen"
        verbose_name_plural = "Tipos de Exámenes"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class PanelExamen(models.Model):
    """Paneles que agrupan varios tipos de exámenes"""
    codigo = models.CharField(max_length=20, unique=True, null=True, blank=True, verbose_name="Código")
    nombre = models.CharField(max_length=100, verbose_name="Nombre del Panel")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    examenes = models.ManyToManyField(TipoExamen, verbose_name="Exámenes del Panel")
    precio = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Precio")
    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Panel de Examen"
        verbose_name_plural = "Paneles de Exámenes"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class SolicitudExamen(models.Model):
    """Solicitudes de exámenes de laboratorio"""
    ESTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('EN_PROCESO', 'En Proceso'),
        ('COMPLETADO', 'Completado'),
        ('CANCELADO', 'Cancelado'),
    ]

    numero = models.CharField(max_length=20, unique=True, null=True, blank=True, verbose_name="Número de Solicitud")
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, verbose_name="Paciente")
    medico = models.ForeignKey(Medico, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Médico")
    consulta = models.ForeignKey(Consulta, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Consulta")
    
    # Campos para exámenes individuales y paneles
    examenes_individuales = models.ManyToManyField(TipoExamen, blank=True, verbose_name="Exámenes Individuales")
    paneles = models.ManyToManyField(PanelExamen, blank=True, verbose_name="Paneles")
    
    fecha_solicitud = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Solicitud")
    fecha_entrega = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Entrega")
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE', verbose_name="Estado")
    observaciones = models.TextField(blank=True, verbose_name="Observaciones")
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Total")

    class Meta:
        verbose_name = "Solicitud de Examen"
        verbose_name_plural = "Solicitudes de Exámenes"
        ordering = ['-fecha_solicitud']

    def __str__(self):
        return f"Solicitud {self.numero} - {self.paciente}"

    def save(self, *args, **kwargs):
        if not self.numero:
            # Generar número automático de forma más robusta
            year = timezone.now().year
            try:
                last_solicitud = SolicitudExamen.objects.filter(
                    numero__startswith=f'LAB{year}'
                ).order_by('-numero').first()
                
                if last_solicitud and last_solicitud.numero:
                    # Extraer el número de forma más segura
                    try:
                        # Buscar el último número después del guión
                        parts = last_solicitud.numero.split('-')
                        if len(parts) == 2:
                            last_num = int(parts[1])
                            new_num = last_num + 1
                        else:
                            new_num = 1
                    except (ValueError, IndexError):
                        # Si hay error al parsear, empezar desde 1
                        new_num = 1
                else:
                    new_num = 1
                
                self.numero = f'LAB{year}-{new_num:04d}'
            except Exception as e:
                # Fallback: usar timestamp si algo falla
                import time
                self.numero = f'LAB{year}-{int(time.time())}'
        
        super().save(*args, **kwargs)

    def calcular_total(self):
        """Calcula el total de la solicitud de forma robusta"""
        total = 0
        
        try:
            # Sumar exámenes individuales
            for examen in self.examenes_individuales.all():
                if examen.precio:
                    total += examen.precio
            
            # Sumar paneles
            for panel in self.paneles.all():
                if panel.precio:
                    total += panel.precio
        except Exception as e:
            # Si hay error al calcular, retornar 0
            total = 0
        
        return total


class ResultadoExamen(models.Model):
    """Resultados de los exámenes mejorados"""
    solicitud = models.ForeignKey(SolicitudExamen, on_delete=models.CASCADE, verbose_name="Solicitud")
    tipo_examen = models.ForeignKey(TipoExamen, on_delete=models.CASCADE, verbose_name="Tipo de Examen")
    
    # Valores del resultado
    valor_numerico = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Valor Numérico")
    valor_texto = models.CharField(max_length=255, blank=True, verbose_name="Valor Texto")
    unidad = models.CharField(max_length=50, blank=True, verbose_name="Unidad")
    
    # Rangos normales
    valor_normal_min = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Valor Normal Mínimo")
    valor_normal_max = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Valor Normal Máximo")
    valor_normal_texto = models.CharField(max_length=255, blank=True, verbose_name="Valor Normal (Texto)")
    
    # Análisis del resultado
    es_normal = models.BooleanField(default=True, verbose_name="¿Es Normal?")
    interpretacion_ia = models.TextField(blank=True, verbose_name="Interpretación IA")
    observaciones = models.TextField(blank=True, verbose_name="Observaciones")
    
    # Metadatos
    fecha_resultado = models.DateTimeField(auto_now_add=True, verbose_name="Fecha del Resultado")
    tecnico = models.CharField(max_length=100, blank=True, verbose_name="Técnico Responsable")
    validado_por = models.ForeignKey('medicos.Medico', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Validado por")

    class Meta:
        verbose_name = "Resultado de Examen"
        verbose_name_plural = "Resultados de Exámenes"
        unique_together = ['solicitud', 'tipo_examen']
        ordering = ['-fecha_resultado']

    def __str__(self):
        return f"Resultado {self.tipo_examen} - {self.solicitud.numero}"

    def calcular_es_normal(self):
        """Calcula automáticamente si el valor es normal"""
        if self.valor_numerico and self.valor_normal_min and self.valor_normal_max:
            return self.valor_normal_min <= self.valor_numerico <= self.valor_normal_max
        return True

    def save(self, *args, **kwargs):
        # Calcular automáticamente si es normal
        self.es_normal = self.calcular_es_normal()
        super().save(*args, **kwargs)