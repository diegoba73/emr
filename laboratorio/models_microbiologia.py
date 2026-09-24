"""
Microbiología clínica — independiente del LIMS de química clínica.

El pedido se arma con paciente + médico + tipo de cultivo + tipo de muestra
microbiológica. ``SolicitudExamen`` / ``Muestra`` LIMS son opcionales (legado).
"""
from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from pacientes.models import Paciente

from .obra_social import ESTADO_OBRA_SOCIAL_CHOICES

# Reglas legado (solo si el estudio aún tiene muestra LIMS vinculada).
MUESTRA_ESTADOS_VALIDOS_INICIAR_MICRO = frozenset({"RECIBIDA", "CONSERVADA", "EN_PROCESO"})
MUESTRA_ESTADOS_BLOQUEAN_MICRO = frozenset(
    {"PENDIENTE_TOMA", "TOMADA", "RECHAZADA", "DESCARTADA", "CANCELADA"}
)


class TipoCultivoMicrobiologia(models.Model):
    """Catálogo de tipos de cultivo clínico (hemocultivo, urocultivo, etc.)."""

    codigo = models.CharField(max_length=40, unique=True, verbose_name="Código")
    nombre = models.CharField(max_length=200, verbose_name="Nombre")
    descripcion = models.TextField(blank=True, default="", verbose_name="Descripción")
    orden = models.PositiveSmallIntegerField(default=100, verbose_name="Orden")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tipo de cultivo microbiológico"
        verbose_name_plural = "Tipos de cultivo microbiológico"
        ordering = ["orden", "nombre"]

    def __str__(self) -> str:
        return f"{self.codigo} - {self.nombre}"


class TipoMuestraMicrobiologia(models.Model):
    """Catálogo de tipos de muestra para microbiología clínica."""

    codigo = models.CharField(max_length=40, unique=True, verbose_name="Código")
    nombre = models.CharField(max_length=200, verbose_name="Nombre")
    descripcion = models.TextField(blank=True, default="", verbose_name="Descripción")
    orden = models.PositiveSmallIntegerField(default=100, verbose_name="Orden")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tipo de muestra microbiológica"
        verbose_name_plural = "Tipos de muestra microbiológica"
        ordering = ["orden", "nombre"]

    def __str__(self) -> str:
        return f"{self.codigo} - {self.nombre}"


class MedioCultivo(models.Model):
    """Catálogo de medios de cultivo (agar sangre, MacConkey, etc.).

    Escritura: admin y operadores LIMS. Desactivar con ``activo=False`` en vez de borrar.
    """

    codigo = models.CharField(max_length=30, unique=True, verbose_name="Código")
    nombre = models.CharField(max_length=200, verbose_name="Nombre")
    tipo = models.CharField(max_length=50, blank=True, default="", verbose_name="Tipo")
    descripcion = models.TextField(blank=True, default="", verbose_name="Descripción")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Medio de cultivo"
        verbose_name_plural = "Medios de cultivo"
        ordering = ["nombre"]

    def __str__(self) -> str:
        return f"{self.codigo} - {self.nombre}"


class EstudioMicrobiologia(models.Model):
    """Pedido / estudio de microbiología clínica (cultivo)."""

    ESTADO_CHOICES = [
        ("PENDIENTE", "Pendiente"),
        ("RECIBIDO", "Recibido"),
        ("SEMBRADO", "Sembrado"),
        ("LECTURA_PRELIMINAR", "Lectura preliminar"),
        ("IDENTIFICACION", "Identificación"),
        ("ANTIBIOGRAMA", "Antibiograma"),
        ("LISTO_PARA_VALIDAR", "Listo para validar"),
        ("VALIDADO", "Validado"),
        ("INFORMADO", "Informado"),
        ("CANCELADO", "Cancelado"),
    ]
    ESTADOS_TERMINALES = frozenset({"CANCELADO", "INFORMADO"})
    ESTADOS_BLOQUEAN_OPERACION = frozenset({"CANCELADO"})

    # Espejo del código de TipoCultivoMicrobiologia (catálogo = fuente de verdad).
    TIPO_ESTUDIO_CHOICES = []  # legado; no validar contra lista fija

    numero = models.CharField(
        max_length=32,
        unique=True,
        null=True,
        blank=True,
        verbose_name="Número de estudio",
        help_text="Generado automáticamente si se deja vacío (LAB-YYYY-XXXXX).",
    )
    solicitud = models.ForeignKey(
        "laboratorio.SolicitudExamen",
        on_delete=models.PROTECT,
        related_name="estudios_microbiologia",
        verbose_name="Solicitud LIMS (legado)",
        null=True,
        blank=True,
    )
    muestra = models.ForeignKey(
        "laboratorio.Muestra",
        on_delete=models.PROTECT,
        related_name="estudios_microbiologia",
        verbose_name="Muestra LIMS (legado)",
        null=True,
        blank=True,
    )
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.PROTECT,
        related_name="estudios_microbiologia",
        verbose_name="Paciente",
    )
    consulta_hc = models.ForeignKey(
        "historias_clinicas.Consulta",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="estudios_microbiologia",
        verbose_name="Consulta asociada",
    )
    origen_solicitud = models.CharField(
        max_length=24,
        blank=True,
        default="",
        verbose_name="Origen clínico",
        help_text="Mismos códigos que LIMS (AMBULATORIO_*, INTERNACION_*, GUARDIA, EXTERNO_*).",
    )
    codigo_barra = models.CharField(
        max_length=32,
        unique=True,
        null=True,
        blank=True,
        verbose_name="Código de barras",
        help_text="Igual al número de protocolo (LAB-YYYY-XXXXX); se asigna al imprimir etiqueta.",
    )
    etiquetas_impresas_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Etiquetas impresas",
    )
    medico_interno = models.ForeignKey(
        "medicos.Medico",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="estudios_microbiologia",
        verbose_name="Médico solicitante",
    )
    medico_externo_nombre = models.CharField(
        max_length=200,
        blank=True,
        default="",
        verbose_name="Médico externo",
    )
    tipo_cultivo = models.ForeignKey(
        TipoCultivoMicrobiologia,
        on_delete=models.PROTECT,
        related_name="estudios",
        verbose_name="Tipo de cultivo",
        null=True,
        blank=True,
    )
    tipo_muestra_micro = models.ForeignKey(
        TipoMuestraMicrobiologia,
        on_delete=models.PROTECT,
        related_name="estudios",
        verbose_name="Tipo de muestra",
        null=True,
        blank=True,
    )
    tipo_estudio = models.CharField(
        max_length=40,
        default="UROCULTIVO",
        verbose_name="Tipo de estudio (código)",
        help_text="Espejo del código de tipo_cultivo; el catálogo es la fuente de verdad.",
    )
    estado = models.CharField(
        max_length=32,
        choices=ESTADO_CHOICES,
        default="PENDIENTE",
        verbose_name="Estado",
    )
    estado_obra_social = models.CharField(
        max_length=24,
        choices=ESTADO_OBRA_SOCIAL_CHOICES,
        blank=True,
        default="",
        verbose_name="Estado obra social",
        help_text="Situación de cobertura: autorizado, debe orden, falta autorización o debe abonar.",
    )
    observaciones = models.TextField(blank=True, default="", verbose_name="Observaciones")

    fecha_inicio = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de inicio")
    fecha_cierre = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de cierre")
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="estudios_microbiologia_responsable",
        verbose_name="Responsable",
    )
    cancelado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="estudios_microbiologia_cancelados",
        verbose_name="Cancelado por",
    )
    fecha_cancelacion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de cancelación")
    motivo_cancelacion = models.TextField(blank=True, default="", verbose_name="Motivo de cancelación")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Estudio de microbiología"
        verbose_name_plural = "Estudios de microbiología"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["solicitud", "estado"]),
            models.Index(fields=["muestra", "estado"]),
            models.Index(fields=["paciente", "estado"]),
            models.Index(fields=["estado", "created_at"]),
            models.Index(fields=["fecha_inicio"]),
        ]

    def __str__(self) -> str:
        return self.numero or f"EstudioMicrobiologia #{self.pk}"

    def clean(self):
        if self.muestra_id and self.solicitud_id and self.muestra.solicitud_id != self.solicitud_id:
            raise ValidationError(
                {"muestra": "La muestra debe pertenecer a la misma solicitud que el estudio."}
            )
        if self.muestra_id and self.paciente_id and self.muestra.paciente_id != self.paciente_id:
            raise ValidationError(
                {"paciente": "El paciente del estudio debe coincidir con el paciente de la muestra."}
            )
        if self.solicitud_id and self.paciente_id and self.solicitud.paciente_id != self.paciente_id:
            raise ValidationError(
                {"paciente": "El paciente del estudio debe coincidir con el paciente de la solicitud."}
            )
        if self._state.adding and self.muestra_id:
            if self.muestra.estado not in MUESTRA_ESTADOS_VALIDOS_INICIAR_MICRO:
                raise ValidationError(
                    {
                        "muestra": (
                            "Solo se puede vincular microbiología a muestras LIMS "
                            "RECIBIDA, CONSERVADA o EN_PROCESO."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        if self.tipo_cultivo_id:
            codigo = getattr(self.tipo_cultivo, "codigo", None)
            if codigo:
                self.tipo_estudio = codigo
        if not self.numero:
            from laboratorio.lab_codigo import next_protocolo

            self.numero = next_protocolo()
        self.full_clean()
        super().save(*args, **kwargs)

    def ensure_codigo_barra(self) -> str:
        """Asigna codigo_barra = numero (LAB-YYYY-XXXXX) si aún no tiene."""
        if self.codigo_barra:
            return self.codigo_barra
        if not self.numero:
            from laboratorio.lab_codigo import next_protocolo

            self.numero = next_protocolo()
        self.codigo_barra = self.numero
        return self.codigo_barra

    @property
    def sin_etiquetas(self) -> bool:
        return self.estado == "PENDIENTE" and self.etiquetas_impresas_at is None

    @property
    def esperando_recepcion(self) -> bool:
        return self.estado == "PENDIENTE" and self.etiquetas_impresas_at is not None


class SiembraMicrobiologia(models.Model):
    """Siembra de un medio de cultivo dentro de un estudio microbiológico."""

    ESTADO_CHOICES = [
        ("SEMBRADA", "Sembrada"),
        ("CANCELADA", "Cancelada"),
    ]

    estudio = models.ForeignKey(
        EstudioMicrobiologia,
        on_delete=models.PROTECT,
        related_name="siembras",
        verbose_name="Estudio",
    )
    muestra = models.ForeignKey(
        "laboratorio.Muestra",
        on_delete=models.PROTECT,
        related_name="siembras_microbiologia",
        verbose_name="Muestra LIMS (legado)",
        null=True,
        blank=True,
    )
    medio = models.ForeignKey(
        MedioCultivo,
        on_delete=models.PROTECT,
        related_name="siembras",
        verbose_name="Medio de cultivo",
    )
    fecha_siembra = models.DateTimeField(default=timezone.now, verbose_name="Fecha de siembra")
    sembrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="siembras_realizadas",
        verbose_name="Sembrado por",
    )
    condicion_incubacion = models.CharField(
        max_length=120, blank=True, default="", verbose_name="Condición de incubación"
    )
    temperatura_c = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="Temperatura (°C)"
    )
    atmosfera = models.CharField(max_length=80, blank=True, default="", verbose_name="Atmósfera")
    observaciones = models.TextField(blank=True, default="", verbose_name="Observaciones")
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default="SEMBRADA",
        verbose_name="Estado",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Siembra microbiológica"
        verbose_name_plural = "Siembras microbiológicas"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["estudio", "estado"]),
            models.Index(fields=["medio"]),
            models.Index(fields=["fecha_siembra"]),
        ]

    def __str__(self) -> str:
        return f"Siembra #{self.pk} ({self.medio.codigo})"

    def clean(self):
        if (
            self.estudio_id
            and self.muestra_id
            and self.estudio.muestra_id
            and self.muestra_id != self.estudio.muestra_id
        ):
            raise ValidationError(
                {"muestra": "La siembra debe usar la misma muestra que el estudio asociado."}
            )
        if self.estudio_id and self.estudio.estado in EstudioMicrobiologia.ESTADOS_BLOQUEAN_OPERACION:
            raise ValidationError(
                {"estudio": "No se puede sembrar sobre un estudio cancelado."}
            )
        if self.medio_id and not self.medio.activo:
            raise ValidationError(
                {"medio": "El medio de cultivo debe estar activo."}
            )
        if self._state.adding and self.muestra_id:
            if self.muestra.estado not in MUESTRA_ESTADOS_VALIDOS_INICIAR_MICRO:
                raise ValidationError(
                    {
                        "muestra": (
                            "Solo se puede sembrar con muestras RECIBIDA, CONSERVADA o EN_PROCESO."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class LecturaCultivo(models.Model):
    """Lectura de cultivo asociada a una siembra. B3.1 no genera aislados ni informe."""

    CRECIMIENTO_CHOICES = [
        ("PENDIENTE", "Pendiente"),
        ("SIN_DESARROLLO", "Sin desarrollo"),
        ("ESCASO", "Escaso"),
        ("MODERADO", "Moderado"),
        ("ABUNDANTE", "Abundante"),
        ("MIXTO", "Mixto"),
    ]

    siembra = models.ForeignKey(
        SiembraMicrobiologia,
        on_delete=models.PROTECT,
        related_name="lecturas",
        verbose_name="Siembra",
    )
    estudio = models.ForeignKey(
        EstudioMicrobiologia,
        on_delete=models.PROTECT,
        related_name="lecturas",
        verbose_name="Estudio",
    )
    fecha_lectura = models.DateTimeField(default=timezone.now, verbose_name="Fecha de lectura")
    leido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lecturas_realizadas",
        verbose_name="Leído por",
    )
    horas_incubacion = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="Horas de incubación"
    )
    crecimiento = models.CharField(
        max_length=20,
        choices=CRECIMIENTO_CHOICES,
        default="PENDIENTE",
        verbose_name="Crecimiento",
    )
    descripcion_colonias = models.TextField(blank=True, default="", verbose_name="Descripción colonias")
    tincion_gram = models.TextField(blank=True, default="", verbose_name="Tinción de Gram")
    observaciones = models.TextField(blank=True, default="", verbose_name="Observaciones")
    es_preliminar = models.BooleanField(default=False, verbose_name="Lectura preliminar")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Lectura de cultivo"
        verbose_name_plural = "Lecturas de cultivo"
        ordering = ["-fecha_lectura", "-id"]
        indexes = [
            models.Index(fields=["siembra", "-fecha_lectura"]),
            models.Index(fields=["estudio", "-fecha_lectura"]),
            models.Index(fields=["crecimiento"]),
        ]

    def __str__(self) -> str:
        return f"Lectura #{self.pk} siembra={self.siembra_id}"

    def clean(self):
        if self.siembra_id and self.estudio_id and self.siembra.estudio_id != self.estudio_id:
            raise ValidationError(
                {"siembra": "La siembra debe pertenecer al estudio indicado."}
            )
        if self.estudio_id and self.estudio.estado in EstudioMicrobiologia.ESTADOS_BLOQUEAN_OPERACION:
            raise ValidationError(
                {"estudio": "No se puede leer sobre un estudio cancelado."}
            )
        if self.siembra_id and self.siembra.estado == "CANCELADA":
            raise ValidationError(
                {"siembra": "No se puede leer sobre una siembra cancelada."}
            )
        if (
            self.siembra_id
            and self.fecha_lectura
            and self.siembra.fecha_siembra
            and self.fecha_lectura < self.siembra.fecha_siembra
        ):
            raise ValidationError(
                {"fecha_lectura": "La fecha de lectura no puede ser anterior a la fecha de siembra."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# B3.2 — Microorganismos, aislados e identificación
# ---------------------------------------------------------------------------


class Microorganismo(models.Model):
    """Catálogo de microorganismos / hallazgos (LIMS Fase B3.2 + LabWin).

    Se desactiva con ``activo=False`` en vez de borrar.
    ``nombre`` es el texto para mostrar; ``nombre_original`` conserva el legado.
    Una corrección de catálogo no altera informes ya validados (texto snapshot).
    """

    ORIGEN_CHOICES = [
        ("MANUAL", "Manual"),
        ("REFERENCIA", "Referencia"),
        ("LABWIN_BACTE", "LabWin BACTE"),
    ]
    TIPO_REGISTRO_CHOICES = [
        ("MICROORGANISMO", "Microorganismo"),
        ("HALLAZGO", "Hallazgo"),
        ("MORFOLOGIA", "Morfología"),
        ("FLORA", "Flora"),
        ("NEGATIVO", "Resultado negativo"),
        ("OTRO", "Otro"),
    ]
    CORRECCION_CHOICES = [
        ("NINGUNA", "Sin corrección"),
        ("ORTOGRAFIA_AUTO", "Ortografía automática"),
        ("PENDIENTE_REVISION", "Pendiente revisión profesional"),
    ]

    codigo = models.CharField(max_length=40, unique=True, verbose_name="Código")
    nombre = models.CharField(max_length=200, verbose_name="Nombre para mostrar")
    nombre_original = models.CharField(
        max_length=200,
        blank=True,
        default="",
        verbose_name="Nombre original",
        help_text="Texto legado sin alterar (LabWin u otra fuente).",
    )
    genero = models.CharField(max_length=120, blank=True, default="", verbose_name="Género")
    especie = models.CharField(max_length=120, blank=True, default="", verbose_name="Especie")
    grupo = models.CharField(max_length=80, blank=True, default="", verbose_name="Grupo")
    descripcion = models.TextField(blank=True, default="", verbose_name="Descripción")
    tipo_registro = models.CharField(
        max_length=20,
        choices=TIPO_REGISTRO_CHOICES,
        default="MICROORGANISMO",
        verbose_name="Tipo de registro",
    )
    origen = models.CharField(
        max_length=20,
        choices=ORIGEN_CHOICES,
        default="MANUAL",
        verbose_name="Origen",
    )
    correccion_estado = models.CharField(
        max_length=24,
        choices=CORRECCION_CHOICES,
        default="NINGUNA",
        verbose_name="Estado de corrección",
    )
    requiere_revision = models.BooleanField(default=False, verbose_name="Requiere revisión")
    motivo_revision = models.TextField(blank=True, default="", verbose_name="Motivo de revisión")
    archivo_origen = models.CharField(max_length=255, blank=True, default="", verbose_name="Archivo origen")
    importado_at = models.DateTimeField(null=True, blank=True, verbose_name="Importado en")
    editado_manualmente = models.BooleanField(
        default=False,
        verbose_name="Editado manualmente",
        help_text="Si es True, reimportaciones no pisan nombre/activo.",
    )
    activo = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Microorganismo"
        verbose_name_plural = "Microorganismos"
        ordering = ["nombre"]
        indexes = [
            models.Index(fields=["activo", "nombre"]),
            models.Index(fields=["genero", "especie"]),
            models.Index(fields=["origen", "codigo"]),
            models.Index(fields=["requiere_revision", "activo"]),
        ]

    def __str__(self) -> str:
        return f"{self.codigo} - {self.nombre}"


class AisladoMicrobiologico(models.Model):
    """Aislado obtenido a partir de una lectura de cultivo (LIMS Fase B3.2).

    Estados cableados:

    - ``SOSPECHADO`` (default) — sin identificación todavía.
    - ``IDENTIFICADO`` — auto al crear su primera ``IdentificacionMicroorganismo`` válida.
    - ``DESCARTADO`` — acción ``descartar`` (no se puede identificar después).

    El campo ``requiere_antibiograma`` es informativo en B3.2; no dispara
    creación de antibiograma (queda para B3.3).
    """

    ESTADO_CHOICES = [
        ("SOSPECHADO", "Sospechado"),
        ("IDENTIFICADO", "Identificado"),
        ("DESCARTADO", "Descartado"),
    ]
    ESTADOS_BLOQUEAN_IDENTIFICACION = frozenset({"DESCARTADO"})

    SIGNIFICANCIA_CHOICES = [
        ("NO_DEFINIDA", "No definida"),
        ("CONTAMINANTE", "Contaminante"),
        ("FLORA_HABITUAL", "Flora habitual"),
        ("SIGNIFICATIVO", "Significativo"),
        ("CRITICO", "Crítico"),
    ]

    estudio = models.ForeignKey(
        EstudioMicrobiologia,
        on_delete=models.PROTECT,
        related_name="aislados",
        verbose_name="Estudio",
    )
    lectura_origen = models.ForeignKey(
        LecturaCultivo,
        on_delete=models.PROTECT,
        related_name="aislados",
        verbose_name="Lectura de origen",
    )
    microorganismo = models.ForeignKey(
        Microorganismo,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="aislados",
        verbose_name="Microorganismo",
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default="SOSPECHADO",
        verbose_name="Estado",
    )
    descripcion = models.TextField(blank=True, default="", verbose_name="Descripción")
    cantidad = models.CharField(max_length=80, blank=True, default="", verbose_name="Cantidad")
    significancia = models.CharField(
        max_length=20,
        choices=SIGNIFICANCIA_CHOICES,
        default="NO_DEFINIDA",
        verbose_name="Significancia",
    )
    requiere_antibiograma = models.BooleanField(
        default=False,
        verbose_name="Requiere antibiograma",
        help_text="Marcado para flujo futuro B3.3; en B3.2 no dispara creación automática.",
    )
    observaciones = models.TextField(blank=True, default="", verbose_name="Observaciones")
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="aislados_creados",
        verbose_name="Creado por",
    )
    descartado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="aislados_descartados",
        verbose_name="Descartado por",
    )
    fecha_descarte = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de descarte")
    motivo_descarte = models.TextField(blank=True, default="", verbose_name="Motivo de descarte")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Aislado microbiológico"
        verbose_name_plural = "Aislados microbiológicos"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["estudio", "estado"]),
            models.Index(fields=["lectura_origen"]),
            models.Index(fields=["microorganismo", "estado"]),
            models.Index(fields=["significancia"]),
        ]

    def __str__(self) -> str:
        return f"Aislado #{self.pk} estudio={self.estudio_id}"

    def clean(self):
        if (
            self.lectura_origen_id
            and self.estudio_id
            and self.lectura_origen.estudio_id != self.estudio_id
        ):
            raise ValidationError(
                {"lectura_origen": "La lectura debe pertenecer al estudio indicado."}
            )
        if self.estudio_id and self.estudio.estado in EstudioMicrobiologia.ESTADOS_BLOQUEAN_OPERACION:
            raise ValidationError(
                {"estudio": "No se puede registrar aislado sobre un estudio cancelado."}
            )
        if self.lectura_origen_id and self.lectura_origen.siembra.estado == "CANCELADA":
            raise ValidationError(
                {"lectura_origen": "No se puede crear aislado desde una lectura de siembra cancelada."}
            )
        if self.microorganismo_id and not self.microorganismo.activo:
            raise ValidationError(
                {"microorganismo": "El microorganismo debe estar activo."}
            )
        if self.estado == "IDENTIFICADO" and not self.microorganismo_id:
            raise ValidationError(
                {"microorganismo": "Un aislado IDENTIFICADO requiere un microorganismo asociado."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class IdentificacionMicroorganismo(models.Model):
    """Identificación microbiológica de un aislado (LIMS Fase B3.2).

    Cada identificación referencia un ``Microorganismo`` activo. La primera
    identificación válida sobre un aislado ``SOSPECHADO`` lo pasa a ``IDENTIFICADO``
    y avanza el estudio a ``IDENTIFICACION`` si está en ``SEMBRADO`` o
    ``LECTURA_PRELIMINAR``.

    Las identificaciones no se editan vía PATCH para preservar trazabilidad:
    una identificación errónea se corrige creando otra y/o descartando el aislado.
    """

    aislado = models.ForeignKey(
        AisladoMicrobiologico,
        on_delete=models.PROTECT,
        related_name="identificaciones",
        verbose_name="Aislado",
    )
    microorganismo = models.ForeignKey(
        Microorganismo,
        on_delete=models.PROTECT,
        related_name="identificaciones",
        verbose_name="Microorganismo",
    )
    metodo = models.CharField(max_length=120, blank=True, default="", verbose_name="Método")
    resultado = models.TextField(blank=True, default="", verbose_name="Resultado")
    confianza = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Confianza (%)",
        help_text="Valor entre 0 y 100; opcional.",
    )
    fecha = models.DateTimeField(default=timezone.now, verbose_name="Fecha")
    realizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="identificaciones_realizadas",
        verbose_name="Realizado por",
    )
    observaciones = models.TextField(blank=True, default="", verbose_name="Observaciones")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Identificación de microorganismo"
        verbose_name_plural = "Identificaciones de microorganismo"
        ordering = ["-fecha", "-id"]
        indexes = [
            models.Index(fields=["aislado", "-fecha"]),
            models.Index(fields=["microorganismo"]),
        ]

    def __str__(self) -> str:
        return f"Identificación #{self.pk} aislado={self.aislado_id}"

    def clean(self):
        if self.microorganismo_id and not self.microorganismo.activo:
            raise ValidationError(
                {"microorganismo": "El microorganismo debe estar activo."}
            )
        if self.aislado_id and self.aislado.estado in AisladoMicrobiologico.ESTADOS_BLOQUEAN_IDENTIFICACION:
            raise ValidationError(
                {"aislado": "No se puede identificar un aislado descartado."}
            )
        if (
            self.aislado_id
            and self.aislado.estudio.estado in EstudioMicrobiologia.ESTADOS_BLOQUEAN_OPERACION
        ):
            raise ValidationError(
                {"aislado": "No se puede identificar sobre un estudio cancelado."}
            )
        if self.confianza is not None and (self.confianza < 0 or self.confianza > 100):
            raise ValidationError({"confianza": "La confianza debe estar entre 0 y 100."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# B3.3 — Antibiograma microbiológico
# ---------------------------------------------------------------------------


class Antibiotico(models.Model):
    """Catálogo de antimicrobianos (LIMS Fase B3.3 + LabWin ANTIB).

    ``nombre`` = texto para mostrar; ``nombre_original`` = legado sin alterar.
    ``labwin_d1`` / ``labwin_d2`` se conservan crudos; no son grupos clínicos.
    """

    ORIGEN_CHOICES = [
        ("MANUAL", "Manual"),
        ("REFERENCIA", "Referencia"),
        ("LABWIN_ANTIB", "LabWin ANTIB"),
    ]
    CORRECCION_CHOICES = [
        ("NINGUNA", "Sin corrección"),
        ("ORTOGRAFIA_AUTO", "Ortografía automática"),
        ("PENDIENTE_REVISION", "Pendiente revisión profesional"),
    ]

    codigo = models.CharField(max_length=40, unique=True, verbose_name="Código")
    nombre = models.CharField(max_length=200, verbose_name="Nombre para mostrar")
    nombre_original = models.CharField(
        max_length=200,
        blank=True,
        default="",
        verbose_name="Nombre original",
    )
    familia = models.CharField(max_length=120, blank=True, default="", verbose_name="Familia")
    descripcion = models.TextField(blank=True, default="", verbose_name="Descripción")
    origen = models.CharField(
        max_length=20,
        choices=ORIGEN_CHOICES,
        default="MANUAL",
        verbose_name="Origen",
    )
    correccion_estado = models.CharField(
        max_length=24,
        choices=CORRECCION_CHOICES,
        default="NINGUNA",
        verbose_name="Estado de corrección",
    )
    requiere_revision = models.BooleanField(default=False, verbose_name="Requiere revisión")
    motivo_revision = models.TextField(blank=True, default="", verbose_name="Motivo de revisión")
    archivo_origen = models.CharField(max_length=255, blank=True, default="", verbose_name="Archivo origen")
    importado_at = models.DateTimeField(null=True, blank=True, verbose_name="Importado en")
    editado_manualmente = models.BooleanField(default=False, verbose_name="Editado manualmente")
    labwin_d1 = models.CharField(
        max_length=40,
        blank=True,
        default="",
        verbose_name="LabWin D1_FLD",
        help_text="Valor crudo de exportación; no interpretar como grupo clínico.",
    )
    labwin_d2 = models.CharField(
        max_length=40,
        blank=True,
        default="",
        verbose_name="LabWin D2_FLD",
        help_text="Valor crudo de exportación; no interpretar como grupo clínico.",
    )
    activo = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Antibiótico"
        verbose_name_plural = "Antibióticos"
        ordering = ["nombre"]
        indexes = [
            models.Index(fields=["activo", "nombre"]),
            models.Index(fields=["familia"]),
            models.Index(fields=["origen", "codigo"]),
            models.Index(fields=["requiere_revision", "activo"]),
        ]

    def __str__(self) -> str:
        return f"{self.codigo} - {self.nombre}"


class Antibiograma(models.Model):
    """Antibiograma de un aislado identificado (LIMS Fase B3.3).

    Estados cableados:

    - ``PENDIENTE`` (default al crear; sin resultados todavía).
    - ``EN_PROCESO`` (auto al crear el primer ``ResultadoAntibiotico`` válido).
    - ``COMPLETO`` (acción ``completar``; no se admiten más resultados ni edición).
    - ``CANCELADO`` (acción ``cancelar`` con motivo obligatorio).

    La validación profesional y el informe final se implementan en B3.4
    (``InformeMicrobiologia``).
    """

    ESTADO_CHOICES = [
        ("PENDIENTE", "Pendiente"),
        ("EN_PROCESO", "En proceso"),
        ("COMPLETO", "Completo"),
        ("CANCELADO", "Cancelado"),
    ]
    ESTADOS_BLOQUEAN_CARGA = frozenset({"COMPLETO", "CANCELADO"})
    ESTADOS_TERMINALES = frozenset({"COMPLETO", "CANCELADO"})

    aislado = models.ForeignKey(
        AisladoMicrobiologico,
        on_delete=models.PROTECT,
        related_name="antibiogramas",
        verbose_name="Aislado",
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default="PENDIENTE",
        verbose_name="Estado",
    )
    metodo = models.CharField(max_length=120, blank=True, default="", verbose_name="Método")
    fecha_inicio = models.DateTimeField(default=timezone.now, verbose_name="Fecha de inicio")
    fecha_resultado = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de resultado")
    realizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="antibiogramas_realizados",
        verbose_name="Realizado por",
    )
    cancelado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="antibiogramas_cancelados",
        verbose_name="Cancelado por",
    )
    fecha_cancelacion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de cancelación")
    motivo_cancelacion = models.TextField(blank=True, default="", verbose_name="Motivo de cancelación")
    observaciones = models.TextField(blank=True, default="", verbose_name="Observaciones")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Antibiograma"
        verbose_name_plural = "Antibiogramas"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["aislado", "estado"]),
            models.Index(fields=["estado", "created_at"]),
            models.Index(fields=["fecha_inicio"]),
        ]

    def __str__(self) -> str:
        return f"Antibiograma #{self.pk} aislado={self.aislado_id}"

    def clean(self):
        # Reglas de elegibilidad evaluadas SOLO en alta. Cambios de estado
        # posteriores van por servicio.
        if self._state.adding and self.aislado_id:
            aislado = self.aislado
            if aislado.estado != "IDENTIFICADO":
                raise ValidationError(
                    {"aislado": "Solo se puede crear antibiograma para aislados IDENTIFICADOS."}
                )
            if not aislado.microorganismo_id:
                raise ValidationError(
                    {"aislado": "El aislado debe tener microorganismo asignado para antibiograma."}
                )
            if aislado.estudio.estado in EstudioMicrobiologia.ESTADOS_BLOQUEAN_OPERACION:
                raise ValidationError(
                    {"aislado": "No se puede crear antibiograma sobre un estudio cancelado."}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class ResultadoAntibiotico(models.Model):
    """Resultado de un antibiótico dentro de un antibiograma (LIMS Fase B3.3).

    No se admite duplicar ``antibiotico`` dentro del mismo ``antibiograma``
    (constraint UNIQUE). Carga/edición bloqueada si el antibiograma está
    ``COMPLETO`` o ``CANCELADO``.
    """

    INTERPRETACION_CHOICES = [
        ("S", "Sensible"),
        ("I", "Intermedio"),
        ("R", "Resistente"),
        ("SDD", "Sensible dosis-dependiente"),
        ("NO_APLICA", "No aplica"),
    ]

    antibiograma = models.ForeignKey(
        Antibiograma,
        on_delete=models.PROTECT,
        related_name="resultados",
        verbose_name="Antibiograma",
    )
    antibiotico = models.ForeignKey(
        Antibiotico,
        on_delete=models.PROTECT,
        related_name="resultados",
        verbose_name="Antibiótico",
    )
    halo_mm = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True, verbose_name="Halo (mm)"
    )
    unidad_halo = models.CharField(
        max_length=16, blank=True, default="mm", verbose_name="Unidad halo"
    )
    mic = models.CharField(max_length=40, blank=True, default="", verbose_name="MIC/CIM")
    unidad_mic = models.CharField(
        max_length=24, blank=True, default="", verbose_name="Unidad MIC/CIM"
    )
    interpretacion = models.CharField(
        max_length=10,
        choices=INTERPRETACION_CHOICES,
        verbose_name="Interpretación",
        help_text="Interpretación validada por el laboratorio; no se calcula S/I/R automáticamente.",
    )
    metodo = models.CharField(
        max_length=120,
        blank=True,
        default="",
        verbose_name="Método",
        help_text="Difusión, microdilución, etc. Opcional si ya figura en el antibiograma.",
    )
    estandar_version = models.CharField(
        max_length=80,
        blank=True,
        default="",
        verbose_name="Estándar / versión",
        help_text="Ej. CLSI M100 2024, EUCAST 2024; texto libre del laboratorio.",
    )
    observaciones = models.TextField(blank=True, default="", verbose_name="Observaciones")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Resultado de antibiótico"
        verbose_name_plural = "Resultados de antibiótico"
        ordering = ["antibiograma", "antibiotico"]
        constraints = [
            models.UniqueConstraint(
                fields=["antibiograma", "antibiotico"],
                name="uniq_resultado_por_antibiograma_antibiotico",
            ),
        ]
        indexes = [
            models.Index(fields=["antibiograma"]),
            models.Index(fields=["antibiotico"]),
            models.Index(fields=["interpretacion"]),
        ]

    def __str__(self) -> str:
        return f"ResultadoAntibiotico #{self.pk} ag={self.antibiograma_id} ab={self.antibiotico_id}"

    def clean(self):
        if self.antibiotico_id and not self.antibiotico.activo:
            raise ValidationError(
                {"antibiotico": "El antibiótico debe estar activo."}
            )
        if self.antibiograma_id and self.antibiograma.estado in Antibiograma.ESTADOS_BLOQUEAN_CARGA:
            raise ValidationError(
                {"antibiograma": "No se pueden cargar/modificar resultados en un antibiograma COMPLETO o CANCELADO."}
            )
        if self.interpretacion not in {c[0] for c in self.INTERPRETACION_CHOICES}:
            raise ValidationError({"interpretacion": "Interpretación no válida."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# B3.4 — Informes microbiológicos, validación y cierre
# ---------------------------------------------------------------------------


class InformeMicrobiologia(models.Model):
    """Informe preliminar (opcional) o final (obligatorio para cierre) — LIMS B3.4.

    Flujo: borrador → ``emitir`` → ``EMITIDO``; el informe **final** emitido
    lleva el estudio a ``LISTO_PARA_VALIDAR``. Solo bioquímico/admin crean,
    completan y validan informes; la validación pasa el informe y el estudio
    a ``VALIDADO``. La acción
    ``marcar-informado`` sobre el estudio pasa a ``INFORMADO``.

    No se borran filas; ``ANULADO`` libera el cupo de informe final vigente
    (constraint único condicional).
    """

    TIPO_CHOICES = [
        ("PRELIMINAR", "Preliminar"),
        ("FINAL", "Final"),
    ]
    ESTADO_CHOICES = [
        ("BORRADOR", "Borrador"),
        ("EMITIDO", "Emitido"),
        ("VALIDADO", "Validado"),
        ("ANULADO", "Anulado"),
    ]

    estudio = models.ForeignKey(
        EstudioMicrobiologia,
        on_delete=models.PROTECT,
        related_name="informes",
        verbose_name="Estudio",
    )
    tipo = models.CharField(
        max_length=12,
        choices=TIPO_CHOICES,
        verbose_name="Tipo",
    )
    estado = models.CharField(
        max_length=12,
        choices=ESTADO_CHOICES,
        default="BORRADOR",
        verbose_name="Estado",
    )
    texto = models.TextField(blank=True, default="", verbose_name="Texto del informe")
    version = models.PositiveIntegerField(default=1, verbose_name="Versión")
    emitido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="informes_micro_emitidos",
        verbose_name="Emitido por",
    )
    fecha_emision = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de emisión")
    validado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="informes_micro_validados",
        verbose_name="Validado por",
    )
    fecha_validacion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de validación")
    reemplaza_a = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reemplazos",
        verbose_name="Reemplaza a",
    )
    observaciones = models.TextField(blank=True, default="", verbose_name="Observaciones")
    motivo_anulacion = models.TextField(blank=True, default="", verbose_name="Motivo de anulación")
    anulado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="informes_micro_anulados",
        verbose_name="Anulado por",
    )
    fecha_anulacion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de anulación")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Informe de microbiología"
        verbose_name_plural = "Informes de microbiología"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["estudio", "tipo", "estado"]),
            models.Index(fields=["estudio", "estado"]),
            models.Index(fields=["tipo", "estado"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["estudio"],
                condition=models.Q(tipo="FINAL")
                & ~models.Q(estado="ANULADO"),
                name="uniq_informe_final_vigente_por_estudio",
            ),
        ]

    def __str__(self) -> str:
        return f"Informe {self.tipo} #{self.pk} estudio={self.estudio_id}"


# ---------------------------------------------------------------------------
# Catálogo LabWin — frases rápidas (NEMOTEC) y asociaciones (NEMOESPE)
# ---------------------------------------------------------------------------


class FraseRapidaMicrobiologia(models.Model):
    """Frase rápida / nemotécnico (LabWin NEMOTEC).

    Espacio de códigos independiente de BACTE/ANTIB (p. ej. PSA en NEMOTEC
    no se fusiona con PSA en BACTE).
    """

    ORIGEN_CHOICES = [
        ("MANUAL", "Manual"),
        ("LABWIN_NEMOTEC", "LabWin NEMOTEC"),
    ]
    CATEGORIA_CHOICES = [
        ("GENERAL", "General"),
        ("HALLAZGO", "Hallazgo"),
        ("INTERPRETACION", "Interpretación clínica"),
        ("UMBRAL", "Umbral histórico"),
        ("FENOTIPO", "Fenotipo"),
        ("OTRO", "Otro"),
    ]
    CORRECCION_CHOICES = [
        ("NINGUNA", "Sin corrección"),
        ("ORTOGRAFIA_AUTO", "Ortografía automática"),
        ("PENDIENTE_REVISION", "Pendiente revisión profesional"),
    ]

    abreviatura = models.CharField(max_length=40, unique=True, verbose_name="Abreviatura original")
    texto = models.TextField(verbose_name="Texto para mostrar")
    texto_original = models.TextField(blank=True, default="", verbose_name="Texto original")
    categoria = models.CharField(
        max_length=20,
        choices=CATEGORIA_CHOICES,
        default="GENERAL",
        verbose_name="Categoría",
    )
    origen = models.CharField(
        max_length=20,
        choices=ORIGEN_CHOICES,
        default="MANUAL",
        verbose_name="Origen",
    )
    correccion_estado = models.CharField(
        max_length=24,
        choices=CORRECCION_CHOICES,
        default="NINGUNA",
        verbose_name="Estado de corrección",
    )
    requiere_revision = models.BooleanField(default=False, verbose_name="Requiere revisión")
    motivo_revision = models.TextField(blank=True, default="", verbose_name="Motivo de revisión")
    archivo_origen = models.CharField(max_length=255, blank=True, default="", verbose_name="Archivo origen")
    importado_at = models.DateTimeField(null=True, blank=True, verbose_name="Importado en")
    editado_manualmente = models.BooleanField(default=False, verbose_name="Editado manualmente")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Frase rápida microbiológica"
        verbose_name_plural = "Frases rápidas microbiológicas"
        ordering = ["abreviatura"]
        indexes = [
            models.Index(fields=["activo", "abreviatura"]),
            models.Index(fields=["origen", "abreviatura"]),
            models.Index(fields=["categoria", "activo"]),
            models.Index(fields=["requiere_revision"]),
        ]

    def __str__(self) -> str:
        return f"{self.abreviatura}"


class FraseRapidaAsociacionAnalisis(models.Model):
    """Asociación NEMOESPE: nemotécnico ↔ análisis LabWin + posición.

    Claves verificadas en la exportación:
    - ``analisis_abrev_labwin`` = NEMOESPE.ABREV_FLD (coincide con ANALISIS.ABREV_FLD)
    - ``posicion`` = POSICION_FLD
    - ``nemotec_abrev`` = NEMOTEC_FLD (abreviatura en NEMOTEC)

    ``tipo_examen`` queda nullable hasta mapear códigos LabWin → TipoExamen SYNESIS.
    """

    analisis_abrev_labwin = models.CharField(max_length=40, verbose_name="Análisis LabWin (ABREV_FLD)")
    posicion = models.PositiveIntegerField(verbose_name="Posición (POSICION_FLD)")
    nemotec_abrev = models.CharField(max_length=40, verbose_name="Abreviatura NEMOTEC")
    frase = models.ForeignKey(
        FraseRapidaMicrobiologia,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="asociaciones_analisis",
        verbose_name="Frase rápida",
    )
    numrec_labwin = models.CharField(max_length=40, blank=True, default="", verbose_name="NUMREC_FLD")
    tipo_examen = models.ForeignKey(
        "laboratorio.TipoExamen",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="frases_rapidas_labwin",
        verbose_name="Tipo examen SYNESIS (pendiente de mapeo)",
    )
    archivo_origen = models.CharField(max_length=255, blank=True, default="", verbose_name="Archivo origen")
    importado_at = models.DateTimeField(null=True, blank=True, verbose_name="Importado en")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Asociación frase–análisis LabWin"
        verbose_name_plural = "Asociaciones frase–análisis LabWin"
        ordering = ["analisis_abrev_labwin", "posicion", "nemotec_abrev"]
        constraints = [
            models.UniqueConstraint(
                fields=["analisis_abrev_labwin", "posicion", "nemotec_abrev"],
                name="uniq_labwin_nemoespe_analisis_pos_nemo",
            ),
        ]
        indexes = [
            models.Index(fields=["analisis_abrev_labwin", "posicion"]),
            models.Index(fields=["nemotec_abrev"]),
        ]

    def __str__(self) -> str:
        return f"{self.analisis_abrev_labwin}@{self.posicion}:{self.nemotec_abrev}"


class LabwinMicroCatalogImportBatch(models.Model):
    """Registro de una corrida de importación de catálogos micro LabWin."""

    fuente_dir = models.CharField(max_length=512, verbose_name="Directorio fuente")
    dry_run = models.BooleanField(default=False)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    counts = models.JSONField(default=dict, blank=True)
    errores = models.JSONField(default=list, blank=True)
    revision_pendiente = models.JSONField(default=list, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="labwin_micro_catalog_imports",
    )

    class Meta:
        verbose_name = "Importación catálogo micro LabWin"
        verbose_name_plural = "Importaciones catálogo micro LabWin"
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"LabWin micro import #{self.pk} dry={self.dry_run}"
