"""
Catálogos B0 y modelo transaccional Muestra + EventoMuestra (Fase B1).
Importado desde laboratorio.models para registro en migraciones.
"""
from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from pacientes.models import Paciente


class AreaLaboratorio(models.Model):
    codigo = models.CharField(max_length=20, unique=True, verbose_name="Código")
    nombre = models.CharField(max_length=200, unique=True, verbose_name="Nombre")
    descripcion = models.TextField(blank=True, default="", verbose_name="Descripción")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Área de laboratorio"
        verbose_name_plural = "Áreas de laboratorio"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class SeccionLaboratorio(models.Model):
    area = models.ForeignKey(
        AreaLaboratorio,
        on_delete=models.PROTECT,
        related_name="secciones",
        verbose_name="Área",
    )
    codigo = models.CharField(max_length=30, verbose_name="Código")
    nombre = models.CharField(max_length=200, verbose_name="Nombre")
    descripcion = models.TextField(blank=True, default="", verbose_name="Descripción")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Sección de laboratorio"
        verbose_name_plural = "Secciones de laboratorio"
        ordering = ["area", "nombre"]
        unique_together = [["area", "codigo"]]
        indexes = [
            models.Index(fields=["area", "activo"]),
        ]

    def __str__(self):
        return f"{self.area.codigo}/{self.codigo} - {self.nombre}"


class TipoContenedor(models.Model):
    codigo = models.CharField(max_length=30, unique=True, verbose_name="Código")
    nombre = models.CharField(max_length=200, verbose_name="Nombre")
    descripcion = models.TextField(blank=True, default="", verbose_name="Descripción")
    color = models.CharField(max_length=50, blank=True, default="", verbose_name="Color")
    volumen_ml = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Volumen (ml)"
    )
    aditivo = models.CharField(max_length=100, blank=True, default="", verbose_name="Aditivo")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tipo de contenedor"
        verbose_name_plural = "Tipos de contenedor"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class Muestra(models.Model):
    ESTADO_CHOICES = [
        ("PENDIENTE_TOMA", "Pendiente de toma"),
        ("TOMADA", "Tomada"),
        ("RECIBIDA", "Recibida en laboratorio"),
        ("EN_PROCESO", "En proceso"),
        ("RECHAZADA", "Rechazada"),
        ("CONSERVADA", "En conservación"),
        ("DESCARTADA", "Descartada"),
        ("CANCELADA", "Cancelada"),
    ]

    codigo_barra = models.CharField(
        max_length=32,
        unique=True,
        null=True,
        blank=True,
        verbose_name="Código de barras",
        help_text="Generado automáticamente si se deja vacío (MUE-YYYY-NNNNNN).",
    )
    solicitud = models.ForeignKey(
        "laboratorio.SolicitudExamen",
        on_delete=models.PROTECT,
        related_name="muestras",
        verbose_name="Solicitud",
    )
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.PROTECT,
        related_name="muestras_lims",
        verbose_name="Paciente",
    )
    tipo_muestra = models.ForeignKey(
        "laboratorio.TipoMuestra",
        on_delete=models.PROTECT,
        related_name="muestras",
        verbose_name="Tipo de muestra (catálogo)",
    )
    tipo_contenedor = models.ForeignKey(
        TipoContenedor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="muestras",
        verbose_name="Tipo de contenedor",
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default="PENDIENTE_TOMA",
        verbose_name="Estado",
    )

    fecha_toma = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de toma")
    tomada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="muestras_tomadas",
        verbose_name="Tomada por",
    )
    fecha_recepcion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de recepción")
    recibida_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="muestras_recibidas",
        verbose_name="Recibida por",
    )
    fecha_rechazo = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de rechazo")
    rechazada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="muestras_rechazadas",
        verbose_name="Rechazada por",
    )
    motivo_rechazo = models.TextField(blank=True, default="", verbose_name="Motivo de rechazo")

    ubicacion_actual = models.CharField(max_length=255, blank=True, default="", verbose_name="Ubicación actual")

    fecha_conservacion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de conservación")
    fecha_descarte = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de descarte")
    descartada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="muestras_descartadas",
        verbose_name="Descartada por",
    )

    observaciones = models.TextField(blank=True, default="", verbose_name="Observaciones")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Muestra"
        verbose_name_plural = "Muestras"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["solicitud", "estado"]),
            models.Index(fields=["paciente", "estado"]),
            models.Index(fields=["estado", "created_at"]),
            models.Index(fields=["tipo_muestra"]),
            models.Index(fields=["fecha_toma"]),
            models.Index(fields=["fecha_recepcion"]),
        ]

    def __str__(self):
        return self.codigo_barra or f"Muestra #{self.pk}"

    def clean(self):
        if self.paciente_id and self.solicitud_id:
            if self.paciente_id != self.solicitud.paciente_id:
                raise ValidationError(
                    {"paciente": "El paciente de la muestra debe coincidir con el paciente de la solicitud."}
                )

    def save(self, *args, **kwargs):
        if not self.codigo_barra:
            year = timezone.now().year
            prefix = f"MUE-{year}-"
            last = (
                Muestra.objects.filter(codigo_barra__startswith=prefix)
                .order_by("-codigo_barra")
                .first()
            )
            if last and last.codigo_barra:
                try:
                    n = int(last.codigo_barra.split("-")[-1]) + 1
                except (ValueError, IndexError):
                    n = 1
            else:
                n = 1
            self.codigo_barra = f"MUE-{year}-{n:06d}"
        self.full_clean()
        super().save(*args, **kwargs)


class EventoMuestra(models.Model):
    """Historial append-only de acciones sobre una muestra."""

    ACCION_CHOICES = [
        ("CREADA", "Creada"),
        ("TOMADA", "Tomada"),
        ("RECIBIDA", "Recibida"),
        ("EN_PROCESO", "En proceso"),
        ("PROCESAMIENTO", "Inicio de procesamiento técnico"),
        ("RECHAZADA", "Rechazada"),
        ("CONSERVADA", "Conservada"),
        ("DESCARTADA", "Descartada"),
        ("CANCELADA", "Cancelada"),
        ("CAMBIO_UBICACION", "Cambio de ubicación"),
        ("ACTUALIZADA", "Actualización administrativa"),
    ]

    muestra = models.ForeignKey(
        Muestra,
        on_delete=models.PROTECT,
        related_name="eventos",
        verbose_name="Muestra",
    )
    accion = models.CharField(max_length=32, choices=ACCION_CHOICES, verbose_name="Acción")
    estado_anterior = models.CharField(max_length=32, blank=True, default="", verbose_name="Estado anterior")
    estado_nuevo = models.CharField(max_length=32, blank=True, default="", verbose_name="Estado nuevo")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos_muestra",
        verbose_name="Actor",
    )
    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha")
    observaciones = models.TextField(blank=True, default="", verbose_name="Observaciones")
    metadata = models.JSONField(default=dict, blank=True, verbose_name="Metadata")
    request_id = models.CharField(max_length=64, blank=True, default="", verbose_name="Request ID")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Evento de muestra"
        verbose_name_plural = "Eventos de muestra"
        ordering = ["-fecha", "-id"]
        indexes = [
            models.Index(fields=["muestra", "-fecha"]),
        ]

    def __str__(self):
        return f"{self.muestra_id} {self.accion} @ {self.fecha}"
