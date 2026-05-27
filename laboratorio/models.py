"""
Modelos para el sistema LIMS (Laboratory Information Management System).
Soporta flujo mixto: Digital (EMR) y Papel (recetas externas).
"""
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
from pacientes.models import Paciente
from medicos.models import Medico


# ============================================================================
# MODELOS DE INFRAESTRUCTURA
# ============================================================================

class TipoMuestra(models.Model):
    """
    Tipos de muestras biológicas (sangre, orina, etc.).
    """
    codigo = models.CharField(max_length=10, unique=True, verbose_name="Código")
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    color_tubo = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Color del Tubo",
        help_text="Útil para UI (ej: Rojo, Azul, Verde)"
    )
    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Tipo de Muestra"
        verbose_name_plural = "Tipos de Muestra"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class TipoExamen(models.Model):
    """
    Análisis individual (ej: "Glucosa", "Hemoglobina").
    """
    TIPO_RESULTADO_CHOICES = [
        ("TEXTO", "Texto"),
        ("NUMERICO", "Numérico"),
        ("CUALITATIVO", "Cualitativo"),
    ]

    codigo = models.CharField(max_length=20, unique=True, verbose_name="Código")
    nombre = models.CharField(max_length=200, verbose_name="Nombre")
    abreviatura = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Abreviatura"
    )
    tipo_muestra_requerida = models.ForeignKey(
        TipoMuestra,
        on_delete=models.CASCADE,
        related_name='tipos_examen',
        verbose_name="Tipo de Muestra Requerida"
    )
    seccion = models.ForeignKey(
        "laboratorio.SeccionLaboratorio",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tipos_examen",
        verbose_name="Sección",
    )
    tipo_resultado = models.CharField(
        max_length=32,
        choices=TIPO_RESULTADO_CHOICES,
        default="TEXTO",
        verbose_name="Tipo de resultado",
    )
    unidad_default = models.CharField(
        max_length=32,
        blank=True,
        default="",
        verbose_name="Unidad por defecto",
    )
    precio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Precio"
    )
    rango_referencia_texto = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Rango de Referencia (Texto)",
        help_text="Para imprimir en informe (ej: '70-100 mg/dL')"
    )
    rango_min = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="Rango mínimo",
    )
    rango_max = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="Rango máximo",
    )
    valor_critico_min = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="Valor crítico mínimo",
    )
    valor_critico_max = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="Valor crítico máximo",
    )
    permite_resultado_texto = models.BooleanField(
        default=True,
        verbose_name="Permite resultado textual",
    )
    requiere_muestra = models.BooleanField(
        default=False,
        verbose_name="Requiere muestra física",
        help_text=(
            "Si está activo, cargar-resultados exige muestra_id trazable "
            "para nuevas cargas/actualizaciones."
        ),
    )
    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Tipo de Examen"
        verbose_name_plural = "Tipos de Examen"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    def clean(self):
        super().clean()
        if self.rango_min is not None and self.rango_max is not None:
            if self.rango_min > self.rango_max:
                raise ValidationError(
                    {"rango_max": "rango_max debe ser mayor o igual que rango_min."}
                )
        if self.valor_critico_min is not None and self.valor_critico_max is not None:
            if self.valor_critico_min > self.valor_critico_max:
                raise ValidationError(
                    {
                        "valor_critico_max": (
                            "valor_critico_max debe ser mayor o igual que valor_critico_min."
                        )
                    }
                )
        if self.seccion_id:
            seccion = self.seccion
            if seccion and not seccion.activo:
                raise ValidationError(
                    {"seccion": "La sección de laboratorio debe estar activa."}
                )


class PanelExamen(models.Model):
    """
    Grupo de análisis (ej: "Hepatograma", "Perfil Lipídico").
    """
    codigo = models.CharField(max_length=20, unique=True, verbose_name="Código")
    nombre = models.CharField(max_length=200, verbose_name="Nombre")
    tipos_examen = models.ManyToManyField(
        TipoExamen,
        related_name='paneles',
        blank=True,
        verbose_name="Tipos de Examen",
        help_text="Exámenes que componen este panel"
    )
    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Panel de Examen"
        verbose_name_plural = "Paneles de Examen"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


# ============================================================================
# MODELOS TRANSACCIONALES (CORE DEL LAB)
# ============================================================================

class SolicitudExamen(models.Model):
    """
    La Orden de Laboratorio.
    Soporta flujo mixto: Digital (EMR) y Papel (recetas externas).
    """
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('TOMA_MUESTRA', 'Toma de Muestra'),
        ('EN_PROCESO', 'En Proceso'),
        ('VALIDADO', 'Validado'),
        ('ENTREGADO', 'Entregado'),
        ('CANCELADO', 'Cancelado'),
    ]

    ORIGEN_CHOICES = [
        ('EMR', 'EMR (Digital)'),
        ('GUARDIA', 'Guardia'),
        ('EXTERNO_PAPEL', 'Externo (Papel)'),
    ]

    # Identificador único generado automáticamente
    numero = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        verbose_name="Número de Protocolo",
        help_text="Generado automáticamente en formato LAB-YYYY-XXXXX"
    )

    # Paciente (link estricto al EMR)
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name='solicitudes_examen',
        verbose_name="Paciente"
    )

    # Médico Híbrido (IMPORTANTE: soporta interno y externo)
    medico_interno = models.ForeignKey(
        Medico,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solicitudes_examen',
        verbose_name="Médico Interno",
        help_text="Médico del sistema EMR"
    )
    medico_externo_nombre = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Médico Externo",
        help_text="Nombre del médico para recetas en papel de médicos fuera de la clínica"
    )

    # Origen de la solicitud
    origen_solicitud = models.CharField(
        max_length=20,
        choices=ORIGEN_CHOICES,
        default='EMR',
        verbose_name="Origen de la Solicitud"
    )

    # Contenido: Exámenes y Paneles
    tipos_examen = models.ManyToManyField(
        TipoExamen,
        related_name='solicitudes',
        blank=True,
        verbose_name="Tipos de Examen"
    )
    paneles = models.ManyToManyField(
        PanelExamen,
        related_name='solicitudes',
        blank=True,
        verbose_name="Paneles de Examen"
    )

    # Estado
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='PENDIENTE',
        verbose_name="Estado"
    )

    # Fechas
    fecha_solicitud = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Solicitud"
    )
    fecha_entrega_prometida = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Entrega Prometida"
    )

    # Campos adicionales
    observaciones = models.TextField(
        blank=True,
        null=True,
        verbose_name="Observaciones"
    )

    class Meta:
        verbose_name = "Solicitud de Examen"
        verbose_name_plural = "Solicitudes de Examen"
        ordering = ['-fecha_solicitud']
        indexes = [
            models.Index(fields=['estado', 'fecha_solicitud']),
            models.Index(fields=['paciente', 'estado']),
        ]

    def __str__(self):
        numero_str = self.numero or f"Sin número ({self.id})"
        paciente_str = self.paciente.nombre_completo if self.paciente else "Sin paciente"
        return f"{numero_str} - {paciente_str}"

    def clean(self):
        """
        Validaciones personalizadas.
        La orden puede cancelarse aunque existan filas ResultadoExamen (p. ej. vacías al crear la orden).
        No cargar ni mutar resultados sobre solicitud cancelada: ver ResultadoExamen.clean().
        """

    def save(self, *args, **kwargs):
        """
        Generador de Protocolo: Si no tiene número, genera uno con formato LAB-YYYY-XXXXX.
        """
        if not self.numero:
            year = timezone.now().year
            # Buscar el último número del año
            last_solicitud = SolicitudExamen.objects.filter(
                numero__startswith=f'LAB-{year}-'
            ).order_by('-fecha_solicitud').first()

            if last_solicitud and last_solicitud.numero:
                try:
                    # Extraer el número secuencial (última parte después del último guión)
                    last_num = int(last_solicitud.numero.split('-')[-1])
                    new_num = last_num + 1
                except (ValueError, IndexError):
                    new_num = 1
            else:
                new_num = 1

            # Formato: LAB-YYYY-XXXXX (con padding a 5 dígitos)
            self.numero = f'LAB-{year}-{new_num:05d}'

        # Validar antes de guardar
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def medico_display(self):
        """
        Retorna el nombre del médico (interno o externo) para display.
        """
        if self.medico_interno:
            return self.medico_interno.nombre_completo
        elif self.medico_externo_nombre:
            return self.medico_externo_nombre
        return "Sin médico asignado"


class ResultadoExamen(models.Model):
    """
    Resultado de un examen individual dentro de una solicitud.
    """
    solicitud = models.ForeignKey(
        SolicitudExamen,
        on_delete=models.CASCADE,
        related_name='resultados',
        verbose_name="Solicitud"
    )
    tipo_examen = models.ForeignKey(
        TipoExamen,
        on_delete=models.PROTECT,  # Integridad histórica: no borrar exámenes con resultados
        related_name='resultados',
        verbose_name="Tipo de Examen"
    )
    valor_obtenido = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name="Valor Obtenido",
        help_text="Puede ser número o texto (ej: 'Positivo', 'Negativo', '120.5'). Vacío hasta cargar resultado.",
    )
    es_patologico = models.BooleanField(
        default=False,
        verbose_name="Es Patológico"
    )
    valor_numerico = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="Valor numérico",
    )
    unidad = models.CharField(
        max_length=32,
        blank=True,
        default="",
        verbose_name="Unidad",
    )
    rango_referencia_snapshot = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Rango referencia (snapshot)",
    )
    rango_min_snapshot = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="Rango mínimo (snapshot)",
    )
    rango_max_snapshot = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="Rango máximo (snapshot)",
    )
    es_critico = models.BooleanField(
        default=False,
        verbose_name="Es crítico",
    )
    valor_critico_min_snapshot = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="Crítico mínimo (snapshot)",
    )
    valor_critico_max_snapshot = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="Crítico máximo (snapshot)",
    )
    validado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resultados_validados',
        verbose_name="Validado por"
    )
    fecha_validacion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Validación"
    )
    observaciones = models.TextField(
        blank=True,
        null=True,
        verbose_name="Observaciones"
    )
    muestra = models.ForeignKey(
        "laboratorio.Muestra",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="resultados",
        verbose_name="Muestra",
        help_text="Muestra física asociada (opcional; compatibilidad con resultados históricos sin muestra).",
    )

    class Meta:
        verbose_name = "Resultado de Examen"
        verbose_name_plural = "Resultados de Examen"
        ordering = ['tipo_examen__nombre']
        unique_together = ['solicitud', 'tipo_examen']  # Un resultado por tipo de examen por solicitud
        indexes = [
            models.Index(fields=['muestra']),
            models.Index(fields=['solicitud', 'muestra']),
        ]

    def __str__(self):
        return f"{self.solicitud.numero} - {self.tipo_examen.nombre}: {self.valor_obtenido}"

    def clean(self):
        """
        Validación: Un resultado no puede cargarse si la solicitud está cancelada.
        Si hay muestra: misma solicitud, mismo paciente, no estados terminales inválidos.
        """
        if self.solicitud.estado == 'CANCELADO':
            raise ValidationError({
                'solicitud': 'No se pueden cargar resultados en una solicitud cancelada.'
            })
        if self.pk:
            prev = (
                ResultadoExamen.objects.filter(pk=self.pk)
                .values("muestra_id", "validado_por_id")
                .first()
            )
            if prev and prev.get("validado_por_id"):
                if prev.get("muestra_id") != self.muestra_id:
                    raise ValidationError(
                        {"muestra": "No se puede cambiar la muestra de un resultado validado."}
                    )
        if self.muestra_id:
            from laboratorio.resultado_muestra_validacion import (
                validate_muestra_integridad_resultado,
            )

            validate_muestra_integridad_resultado(
                solicitud_id=self.solicitud_id,
                paciente_solicitud_id=self.solicitud.paciente_id,
                muestra=self.muestra,
            )
        if self.solicitud.estado in ("VALIDADO", "ENTREGADO", "CANCELADO"):
            raise ValidationError(
                {"solicitud": "No se pueden modificar resultados en el estado actual de la solicitud."}
            )
        if self.valor_obtenido == "" and self.valor_numerico is not None:
            raise ValidationError(
                {
                    "valor_obtenido": (
                        "El resultado sigue pendiente si valor_obtenido está vacío, "
                        "aunque exista valor_numerico."
                    )
                }
            )

    def save(self, *args, **kwargs):
        """
        Validar antes de guardar.
        """
        self.full_clean()
        super().save(*args, **kwargs)


# Catálogos B0 y muestras B1 (evita ciclos de import: FK string en Muestra hacia SolicitudExamen)
from laboratorio.models_catalog import (  # noqa: E402,F401
    AreaLaboratorio,
    EventoMuestra,
    Muestra,
    SeccionLaboratorio,
    TipoContenedor,
)
# Microbiología B3.1 + B3.2 + B3.3 (registro Django; FK string a SolicitudExamen / Muestra).
from laboratorio.models_microbiologia import (  # noqa: E402,F401
    AisladoMicrobiologico,
    Antibiograma,
    Antibiotico,
    EstudioMicrobiologia,
    IdentificacionMicroorganismo,
    InformeMicrobiologia,
    LecturaCultivo,
    MedioCultivo,
    Microorganismo,
    ResultadoAntibiotico,
    SiembraMicrobiologia,
)

