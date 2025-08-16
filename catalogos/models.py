from django.db import models


class DiagnosticoCIE10(models.Model):
    """Diagnósticos CIE-10 estandarizados"""
    codigo = models.CharField(max_length=10, unique=True, verbose_name="Código CIE-10")
    descripcion = models.TextField(verbose_name="Descripción")
    categoria = models.CharField(max_length=100, verbose_name="Categoría")
    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Diagnóstico CIE-10"
        verbose_name_plural = "Diagnósticos CIE-10"
        ordering = ['codigo']

    def __str__(self):
        return f"{self.codigo} - {self.descripcion[:50]}"


class Medicamento(models.Model):
    """Catálogo de medicamentos"""
    nombre = models.CharField(max_length=200, verbose_name="Nombre del Medicamento")
    principio_activo = models.CharField(max_length=200, verbose_name="Principio Activo")
    presentacion = models.CharField(max_length=100, verbose_name="Presentación")
    concentracion = models.CharField(max_length=50, verbose_name="Concentración")
    via_administracion = models.CharField(max_length=50, verbose_name="Vía de Administración")
    codigo_atc = models.CharField(max_length=20, blank=True, null=True, verbose_name="Código ATC")
    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Medicamento"
        verbose_name_plural = "Medicamentos"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} - {self.presentacion}"


class Procedimiento(models.Model):
    """Procedimientos médicos"""
    codigo = models.CharField(max_length=20, unique=True, verbose_name="Código")
    nombre = models.CharField(max_length=200, verbose_name="Nombre del Procedimiento")
    descripcion = models.TextField(verbose_name="Descripción")
    especialidad = models.ForeignKey('medicos.Especialidad', on_delete=models.CASCADE, verbose_name="Especialidad")
    duracion_estimada = models.IntegerField(help_text="Duración en minutos", verbose_name="Duración Estimada")
    requiere_anestesia = models.BooleanField(default=False, verbose_name="Requiere Anestesia")
    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Procedimiento"
        verbose_name_plural = "Procedimientos"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class CentroAtencion(models.Model):
    """Centros de atención médica"""
    nombre = models.CharField(max_length=200, verbose_name="Nombre del Centro")
    tipo = models.CharField(
        max_length=20,
        choices=[
            ('HOSPITAL', 'Hospital'),
            ('CLINICA', 'Clínica'),
            ('CONSULTORIO', 'Consultorio'),
            ('CENTRO_SALUD', 'Centro de Salud'),
            ('LABORATORIO', 'Laboratorio')
        ],
        verbose_name="Tipo de Centro"
    )
    direccion = models.TextField(verbose_name="Dirección")
    telefono = models.CharField(max_length=20, verbose_name="Teléfono")
    email = models.EmailField(verbose_name="Email")
    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Centro de Atención"
        verbose_name_plural = "Centros de Atención"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"

# NUEVO: Modelo para Centros Físicos
class CentroFisico(models.Model):
    """Centros físicos de la clínica"""
    CENTRO_CHOICES = [
        ('CEHTA', 'CEHTA - Centro de Atención Ambulatoria'),
        ('ICPL', 'ICPL - Instituto Cardiológico con Internación'),
    ]
    
    codigo = models.CharField(
        max_length=10,
        choices=CENTRO_CHOICES,
        unique=True,
        verbose_name="Código del Centro"
    )
    nombre = models.CharField(max_length=100, verbose_name="Nombre del Centro")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    direccion = models.TextField(blank=True, null=True, verbose_name="Dirección")
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")
    activo = models.BooleanField(default=True, verbose_name="Centro Activo")
    
    class Meta:
        verbose_name = "Centro Físico"
        verbose_name_plural = "Centros Físicos"
        ordering = ['codigo']
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

# NUEVO: Modelo para Tipos de Atención
class TipoAtencion(models.Model):
    """Tipos de atención médica disponibles"""
    TIPO_CHOICES = [
        # CEHTA
        ('AMBULATORIA', 'Atención Ambulatoria'),
        
        # ICPL
        ('GUARDIA_CARDIOLOGICA', 'Guardia Cardiológica'),
        ('INTERNACION_UCO', 'Internación UCO (Terapia Intensiva)'),
        ('INTERNACION_UCE', 'Internación UCE (Observación/Intermedia)'),
        ('CIRUGIA_AMBULATORIA', 'Cirugía Ambulatoria'),
        ('CIRUGIA_COMPLEJA', 'Cirugía Compleja con Internación'),
    ]
    
    codigo = models.CharField(
        max_length=30,
        choices=TIPO_CHOICES,
        unique=True,
        verbose_name="Código del Tipo"
    )
    nombre = models.CharField(max_length=100, verbose_name="Nombre del Tipo")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    centro_fisico = models.ForeignKey(
        CentroFisico,
        on_delete=models.CASCADE,
        related_name='tipos_atencion',
        verbose_name="Centro Físico"
    )
    requiere_internacion = models.BooleanField(default=False, verbose_name="Requiere Internación")
    es_urgencia = models.BooleanField(default=False, verbose_name="Es Urgencia/Emergencia")
    activo = models.BooleanField(default=True, verbose_name="Tipo Activo")
    
    class Meta:
        verbose_name = "Tipo de Atención"
        verbose_name_plural = "Tipos de Atención"
        ordering = ['centro_fisico', 'codigo']
    
    def __str__(self):
        return f"{self.nombre} ({self.centro_fisico.codigo})"

# NUEVO: Modelo para Áreas/Unidades de Internación
class AreaInternacion(models.Model):
    """Áreas específicas de internación"""
    AREA_CHOICES = [
        ('UCO', 'UCO - Unidad de Cuidados Intensivos'),
        ('UCE', 'UCE - Unidad de Cuidados Especiales'),
        ('PISO_GENERAL', 'Piso General'),
        ('CIRUGIA', 'Área de Cirugía'),
    ]
    
    codigo = models.CharField(
        max_length=20,
        choices=AREA_CHOICES,
        unique=True,
        verbose_name="Código del Área"
    )
    nombre = models.CharField(max_length=100, verbose_name="Nombre del Área")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    centro_fisico = models.ForeignKey(
        CentroFisico,
        on_delete=models.CASCADE,
        related_name='areas_internacion',
        verbose_name="Centro Físico"
    )
    capacidad_camas = models.PositiveIntegerField(default=0, verbose_name="Capacidad de Camas")
    activo = models.BooleanField(default=True, verbose_name="Área Activa")
    
    class Meta:
        verbose_name = "Área de Internación"
        verbose_name_plural = "Áreas de Internación"
        ordering = ['centro_fisico', 'codigo']
    
    def __str__(self):
        return f"{self.nombre} ({self.centro_fisico.codigo})"

# NUEVO: Modelo para Camas de Internación
class CamaInternacion(models.Model):
    """Camas específicas en áreas de internación"""
    ESTADO_CHOICES = [
        ('DISPONIBLE', 'Disponible'),
        ('OCUPADA', 'Ocupada'),
        ('MANTENIMIENTO', 'En Mantenimiento'),
        ('RESERVADA', 'Reservada'),
    ]
    
    numero = models.CharField(max_length=20, verbose_name="Número de Cama")
    area = models.ForeignKey(
        AreaInternacion,
        on_delete=models.CASCADE,
        related_name='camas',
        verbose_name="Área"
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='DISPONIBLE',
        verbose_name="Estado de la Cama"
    )
    tipo_cama = models.CharField(
        max_length=50,
        choices=[
            ('ESTANDAR', 'Cama Estándar'),
            ('UCI', 'Cama UCI'),
            ('UCE', 'Cama UCE'),
            ('POST_QUIRURGICA', 'Cama Post-Quirúrgica'),
        ],
        default='ESTANDAR',
        verbose_name="Tipo de Cama"
    )
    activa = models.BooleanField(default=True, verbose_name="Cama Activa")
    
    class Meta:
        verbose_name = "Cama de Internación"
        verbose_name_plural = "Camas de Internación"
        ordering = ['area', 'numero']
        unique_together = ['area', 'numero']
    
    def __str__(self):
        return f"Cama {self.numero} - {self.area.nombre} ({self.area.centro_fisico.codigo})"
