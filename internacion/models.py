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


class TipoDieta(models.Model):
    """Catálogo de tipos terapéuticos de dieta (no el menú)."""
    nombre = models.CharField(max_length=80, unique=True, verbose_name="Nombre")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Tipo de dieta"
        verbose_name_plural = "Tipos de dieta"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Internacion(models.Model):
    """Internaciones de pacientes"""
    numero_internacion = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        verbose_name="Número de Internación",
    )
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
    atencion_origen = models.ForeignKey(
        'turnos.Atencion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='internaciones_derivadas',
        verbose_name="Atención de origen",
    )
    motivo_ingreso = models.TextField(null=True, blank=True, verbose_name="Motivo de Ingreso")
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
    tipo_dieta = models.ForeignKey(
        TipoDieta,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='internaciones',
        verbose_name="Tipo de dieta",
    )
    alergias = models.TextField(blank=True, default='', verbose_name='Alergias')
    tiene_alergias = models.BooleanField(
        null=True,
        blank=True,
        verbose_name='¿Alergias?',
        help_text='None = no informado; True = Sí; False = No',
    )
    anamnesis_ingreso = models.TextField(blank=True, default='', verbose_name='Anamnesis de ingreso')
    examen_fisico_ingreso = models.TextField(blank=True, default='', verbose_name='Examen físico de ingreso')
    medicacion_habitual = models.TextField(blank=True, default='', verbose_name='Medicación habitual')
    plan_estudio_tratamiento = models.TextField(
        blank=True,
        default='',
        verbose_name='Plan de estudio / tratamiento',
    )
    activo = models.BooleanField(default=True, verbose_name="Activa")
    
    class Meta:
        verbose_name = "Internación"
        verbose_name_plural = "Internaciones"
        ordering = ['-fecha_ingreso']
    
    def __str__(self):
        return f"Internación {self.paciente.apellido}, {self.paciente.nombre} - {self.cama.nombre}"
    
    def save(self, *args, **kwargs):
        if not self.numero_internacion:
            fecha_actual = timezone.now()
            prefijo = f"INT-{fecha_actual.strftime('%Y%m%d')}"
            ultima_internacion = Internacion.objects.filter(
                numero_internacion__startswith=prefijo
            ).order_by('-numero_internacion').first()
            if ultima_internacion and ultima_internacion.numero_internacion:
                try:
                    ultimo_numero = int(ultima_internacion.numero_internacion.split('-')[-1])
                    nuevo_numero = ultimo_numero + 1
                except (ValueError, IndexError):
                    nuevo_numero = 1
            else:
                nuevo_numero = 1
            self.numero_internacion = f"{prefijo}-{nuevo_numero:03d}"

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


class TurnoEnfermeria(models.TextChoices):
    MANANA = 'MANANA', 'Mañana'
    TARDE = 'TARDE', 'Tarde'
    NOCHE = 'NOCHE', 'Noche'


class IndicacionMedica(models.Model):
    """Hoja de indicaciones médicas (papel): dieta, O2, hidratación, controles, texto."""

    internacion = models.ForeignKey(
        Internacion,
        on_delete=models.CASCADE,
        related_name='indicaciones_medicas',
    )
    fecha = models.DateTimeField(auto_now_add=True, db_index=True)
    registrado_por = models.ForeignKey(
        'usuarios.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='indicaciones_internacion',
    )
    hidratacion = models.CharField(max_length=255, blank=True, default='')
    oxigenoterapia = models.CharField(max_length=255, blank=True, default='')
    reposo = models.CharField(max_length=255, blank=True, default='')
    controles = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='TA, FC, glucemia, diuresis, etc.',
    )
    precauciones = models.TextField(blank=True, default='')
    indicaciones = models.TextField(blank=True, default='')
    vigente = models.BooleanField(default=True)

    class Meta:
        ordering = ['-fecha', '-id']
        verbose_name = 'Indicación médica'
        verbose_name_plural = 'Indicaciones médicas'


class MedicacionInternacion(models.Model):
    """Plan de medicación de internación (kardex / indicación farmacológica)."""

    internacion = models.ForeignKey(
        Internacion,
        on_delete=models.CASCADE,
        related_name='medicaciones',
    )
    fecha = models.DateTimeField(auto_now_add=True, db_index=True)
    registrado_por = models.ForeignKey(
        'usuarios.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medicaciones_internacion',
    )
    medicamento = models.CharField(max_length=200)
    dosis = models.CharField(max_length=100, blank=True, default='')
    via = models.CharField(max_length=80, blank=True, default='')
    frecuencia = models.CharField(max_length=100, blank=True, default='')
    horario = models.CharField(max_length=120, blank=True, default='')
    activa = models.BooleanField(default=True)
    observaciones = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-activa', '-fecha', '-id']
        verbose_name = 'Medicación de internación'
        verbose_name_plural = 'Medicaciones de internación'


class ControlEnfermeria(models.Model):
    """Control de enfermería (signos vitales y glucemia por turno)."""

    internacion = models.ForeignKey(
        Internacion,
        on_delete=models.CASCADE,
        related_name='controles_enfermeria',
    )
    fecha = models.DateTimeField(auto_now_add=True, db_index=True)
    turno = models.CharField(max_length=10, choices=TurnoEnfermeria.choices)
    registrado_por = models.ForeignKey(
        'usuarios.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='controles_enfermeria',
    )
    tension_arterial = models.CharField(max_length=15, blank=True, default='')
    frecuencia_cardiaca = models.PositiveSmallIntegerField(null=True, blank=True)
    frecuencia_respiratoria = models.PositiveSmallIntegerField(null=True, blank=True)
    temperatura = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    saturacion_oxigeno = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    dolor = models.PositiveSmallIntegerField(null=True, blank=True, help_text='EVA 0-10')
    glucemia = models.PositiveSmallIntegerField(null=True, blank=True)
    observaciones = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-fecha', '-id']
        verbose_name = 'Control de enfermería'
        verbose_name_plural = 'Controles de enfermería'


class BalanceHidrico(models.Model):
    """Balance hídrico de enfermería."""

    internacion = models.ForeignKey(
        Internacion,
        on_delete=models.CASCADE,
        related_name='balances_hidricos',
    )
    fecha = models.DateTimeField(auto_now_add=True, db_index=True)
    turno = models.CharField(max_length=10, choices=TurnoEnfermeria.choices)
    registrado_por = models.ForeignKey(
        'usuarios.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='balances_hidricos',
    )
    ingresos_vo_ml = models.PositiveIntegerField(null=True, blank=True)
    ingresos_ev_ml = models.PositiveIntegerField(null=True, blank=True)
    diuresis_ml = models.PositiveIntegerField(null=True, blank=True)
    otros_egresos_ml = models.PositiveIntegerField(null=True, blank=True)
    observaciones = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-fecha', '-id']
        verbose_name = 'Balance hídrico'
        verbose_name_plural = 'Balances hídricos'


class NotaEnfermeria(models.Model):
    """Observaciones, curaciones y dispositivos (hoja de enfermería)."""

    internacion = models.ForeignKey(
        Internacion,
        on_delete=models.CASCADE,
        related_name='notas_enfermeria',
    )
    fecha = models.DateTimeField(auto_now_add=True, db_index=True)
    registrado_por = models.ForeignKey(
        'usuarios.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notas_enfermeria_internacion',
    )
    observaciones = models.TextField(blank=True, default='')
    curaciones = models.TextField(blank=True, default='')
    dispositivos = models.TextField(
        blank=True,
        default='',
        help_text='SV, acceso venoso, O2, SNG, etc.',
    )

    class Meta:
        ordering = ['-fecha', '-id']
        verbose_name = 'Nota de enfermería'
        verbose_name_plural = 'Notas de enfermería'


class RegistroKinesiologia(models.Model):
    """Hoja de kinesiología respiratoria / motora."""

    internacion = models.ForeignKey(
        Internacion,
        on_delete=models.CASCADE,
        related_name='registros_kinesiologia',
    )
    fecha = models.DateTimeField(auto_now_add=True, db_index=True)
    registrado_por = models.ForeignKey(
        'usuarios.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registros_kinesiologia',
    )
    frecuencia_respiratoria = models.PositiveSmallIntegerField(null=True, blank=True)
    saturacion_oxigeno = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    oxigenoterapia = models.CharField(max_length=120, blank=True, default='')
    secreciones = models.CharField(max_length=255, blank=True, default='')
    tecnica = models.TextField(blank=True, default='', help_text='Técnica kine aplicada')
    movilizacion = models.CharField(max_length=255, blank=True, default='')
    evolucion = models.TextField(blank=True, default='')
    plan = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-fecha', '-id']
        verbose_name = 'Registro de kinesiología'
        verbose_name_plural = 'Registros de kinesiología'


class MedicacionHabitualInternacion(models.Model):
    """Medicación habitual al ingreso (filas del papel: fármaco + mg/día)."""

    internacion = models.ForeignKey(
        Internacion,
        on_delete=models.CASCADE,
        related_name='medicaciones_habituales',
    )
    fecha = models.DateTimeField(auto_now_add=True, db_index=True)
    registrado_por = models.ForeignKey(
        'usuarios.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medicaciones_habituales_internacion',
    )
    medicamento = models.CharField(max_length=200)
    dosis_mg_dia = models.CharField(max_length=50, blank=True, default='')

    class Meta:
        ordering = ['id']
        verbose_name = 'Medicación habitual de ingreso'
        verbose_name_plural = 'Medicaciones habituales de ingreso'
