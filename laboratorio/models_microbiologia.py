"""
Microbiología base — LIMS Fase B3.1.

Modelos operativos para iniciar y seguir un estudio microbiológico básico
desde una muestra ya transaccionalizada (B0/B1) y vinculable opcionalmente a
``ResultadoExamen`` (B2/B2.1). Esta fase NO incluye microorganismos,
aislados, identificación, antibiograma, informes preliminares ni finales.

Cadena:

    SolicitudExamen
        └── Muestra (RECIBIDA / EN_PROCESO)
                 └── EstudioMicrobiologia (B3.1)
                         └── SiembraMicrobiologia (B3.1)
                                 └── LecturaCultivo (B3.1)

Microbiología NUNCA se serializa en ``ResultadoExamen.valor_obtenido``.

Importado por ``laboratorio/models.py`` para asegurar registro Django.
"""
from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from pacientes.models import Paciente

# Reglas reutilizables de estado de muestra (compartido con B2/B2.1).
MUESTRA_ESTADOS_VALIDOS_INICIAR_MICRO = frozenset({"RECIBIDA", "EN_PROCESO"})
MUESTRA_ESTADOS_BLOQUEAN_MICRO = frozenset(
    {"PENDIENTE_TOMA", "TOMADA", "RECHAZADA", "DESCARTADA", "CANCELADA"}
)


class MedioCultivo(models.Model):
    """Catálogo de medios de cultivo (agar sangre, MacConkey, etc.). Catálogo maestro
    administrativo; desactivar con ``activo=False`` en vez de borrar.
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
    """Estudio microbiológico asociado a una muestra real de la solicitud.

    Estados cableados (B3.1 + B3.2 + B3.3 + B3.4):

    - ``PENDIENTE`` (default al crear) — B3.1
    - ``RECIBIDO`` (acción ``iniciar``) — B3.1
    - ``SEMBRADO`` (auto al crear primera siembra válida) — B3.1
    - ``LECTURA_PRELIMINAR`` (auto al cargar lectura ``es_preliminar=True``) — B3.1
    - ``IDENTIFICACION`` (auto al registrar la primera identificación de aislado) — B3.2
    - ``ANTIBIOGRAMA`` (auto al crear antibiograma o primer ResultadoAntibiotico) — B3.3
    - ``LISTO_PARA_VALIDAR`` (emisión del informe final) — **B3.4**
    - ``VALIDADO`` (validación profesional del informe final) — **B3.4**
    - ``INFORMADO`` (marcado como informado/entregado) — **B3.4**
    - ``CANCELADO`` (acción ``cancelar`` con motivo obligatorio) — B3.1

    Estado futuro (no cableado): ``INCUBANDO``.
    """

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

    TIPO_ESTUDIO_CHOICES = [
        ("CULTIVO_RUTINA", "Cultivo de rutina"),
        ("UROCULTIVO", "Urocultivo"),
        ("HEMOCULTIVO", "Hemocultivo"),
        ("COPROCULTIVO", "Coprocultivo"),
        ("CULTIVO_HERIDA", "Cultivo de herida"),
        ("OTRO", "Otro"),
    ]

    numero = models.CharField(
        max_length=32,
        unique=True,
        null=True,
        blank=True,
        verbose_name="Número de estudio",
        help_text="Generado automáticamente si se deja vacío (MIC-YYYY-NNNNNN).",
    )
    solicitud = models.ForeignKey(
        "laboratorio.SolicitudExamen",
        on_delete=models.PROTECT,
        related_name="estudios_microbiologia",
        verbose_name="Solicitud",
    )
    muestra = models.ForeignKey(
        "laboratorio.Muestra",
        on_delete=models.PROTECT,
        related_name="estudios_microbiologia",
        verbose_name="Muestra",
    )
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.PROTECT,
        related_name="estudios_microbiologia",
        verbose_name="Paciente",
    )
    tipo_estudio = models.CharField(
        max_length=32,
        choices=TIPO_ESTUDIO_CHOICES,
        default="CULTIVO_RUTINA",
        verbose_name="Tipo de estudio",
    )
    estado = models.CharField(
        max_length=32,
        choices=ESTADO_CHOICES,
        default="PENDIENTE",
        verbose_name="Estado",
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
        # Estado inicial debe ser válido respecto al estado de la muestra (sólo se valida en alta;
        # transiciones posteriores van por servicio).
        if self._state.adding and self.muestra_id:
            if self.muestra.estado not in MUESTRA_ESTADOS_VALIDOS_INICIAR_MICRO:
                raise ValidationError(
                    {
                        "muestra": (
                            "Solo se puede iniciar microbiología sobre muestras RECIBIDA o EN_PROCESO."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        if not self.numero:
            year = timezone.now().year
            prefix = f"MIC-{year}-"
            last = (
                EstudioMicrobiologia.objects.filter(numero__startswith=prefix)
                .order_by("-numero")
                .first()
            )
            if last and last.numero:
                try:
                    n = int(last.numero.split("-")[-1]) + 1
                except (ValueError, IndexError):
                    n = 1
            else:
                n = 1
            self.numero = f"{prefix}{n:06d}"
        self.full_clean()
        super().save(*args, **kwargs)


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
        verbose_name="Muestra",
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
        if self.estudio_id and self.muestra_id and self.muestra_id != self.estudio.muestra_id:
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
                            "Solo se puede sembrar con muestras RECIBIDA o EN_PROCESO."
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
    """Catálogo de microorganismos (LIMS Fase B3.2).

    Catálogo administrativo: se desactiva con ``activo=False`` en vez de borrar.
    Escritura limitada a admin/superuser; lectura amplia para roles LIMS.
    """

    codigo = models.CharField(max_length=40, unique=True, verbose_name="Código")
    nombre = models.CharField(max_length=200, verbose_name="Nombre")
    genero = models.CharField(max_length=120, blank=True, default="", verbose_name="Género")
    especie = models.CharField(max_length=120, blank=True, default="", verbose_name="Especie")
    grupo = models.CharField(max_length=80, blank=True, default="", verbose_name="Grupo")
    descripcion = models.TextField(blank=True, default="", verbose_name="Descripción")
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
    """Catálogo de antibióticos (LIMS Fase B3.3).

    Catálogo administrativo: se desactiva con ``activo=False`` en vez de borrar.
    Escritura limitada a admin/superuser; lectura amplia para roles LIMS.
    """

    codigo = models.CharField(max_length=40, unique=True, verbose_name="Código")
    nombre = models.CharField(max_length=200, verbose_name="Nombre")
    familia = models.CharField(max_length=120, blank=True, default="", verbose_name="Familia")
    descripcion = models.TextField(blank=True, default="", verbose_name="Descripción")
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
    mic = models.CharField(max_length=40, blank=True, default="", verbose_name="MIC")
    interpretacion = models.CharField(
        max_length=10,
        choices=INTERPRETACION_CHOICES,
        verbose_name="Interpretación",
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
    lleva el estudio a ``LISTO_PARA_VALIDAR``. La validación profesional
    (solo admin) pasa el informe final y el estudio a ``VALIDADO``. La acción
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
