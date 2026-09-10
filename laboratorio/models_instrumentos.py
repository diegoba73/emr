"""Interfaz bidireccional con analizadores (CM260, Sysmex XP-300)."""
from __future__ import annotations

from django.db import models
from django.utils import timezone


class InterfazInstrumento(models.Model):
    class Driver(models.TextChoices):
        CM260 = "CM260", "Wiener CM260"
        SYSMEX_XP300 = "SYSMEX_XP300", "Sysmex XP-300"

    class Transporte(models.TextChoices):
        TCP = "TCP", "TCP/IP"
        SERIAL = "SERIAL", "RS-232"
        SIMULADOR = "SIMULADOR", "Simulador"

    equipo = models.ForeignKey(
        "laboratorio.EquipoAnalizador",
        on_delete=models.PROTECT,
        related_name="interfaces_instrumento",
    )
    nombre = models.CharField(max_length=120)
    driver = models.CharField(max_length=20, choices=Driver.choices)
    transporte = models.CharField(
        max_length=16,
        choices=Transporte.choices,
        default=Transporte.SIMULADOR,
    )
    host = models.CharField(max_length=120, blank=True, default="")
    puerto = models.PositiveIntegerField(null=True, blank=True)
    puerto_serie = models.CharField(
        max_length=40,
        blank=True,
        default="",
        help_text="COM3, /dev/ttyUSB0, etc. Solo transporte SERIAL.",
    )
    activo = models.BooleanField(default=True)
    ultimo_contacto = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["driver", "nombre"]
        verbose_name = "Interfaz de analizador"
        verbose_name_plural = "Interfaces de analizador"

    def __str__(self):
        return f"{self.nombre} ({self.driver})"

    def tocar(self) -> None:
        self.ultimo_contacto = timezone.now()
        self.save(update_fields=["ultimo_contacto", "updated_at"])


class MapeoAnalitoInstrumento(models.Model):
    interfaz = models.ForeignKey(
        InterfazInstrumento,
        on_delete=models.CASCADE,
        related_name="mapeos",
    )
    codigo_instrumento = models.CharField(max_length=32)
    tipo_examen = models.ForeignKey(
        "laboratorio.TipoExamen",
        on_delete=models.PROTECT,
        related_name="mapeos_instrumento",
    )
    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = [("interfaz", "codigo_instrumento")]
        ordering = ["interfaz", "codigo_instrumento"]
        verbose_name = "Mapeo de analito"
        verbose_name_plural = "Mapeos de analito"

    def __str__(self):
        return f"{self.codigo_instrumento} → {self.tipo_examen.codigo}"

    def save(self, *args, **kwargs):
        self.codigo_instrumento = (self.codigo_instrumento or "").strip().upper()
        super().save(*args, **kwargs)


class MensajeInstrumento(models.Model):
    class Direccion(models.TextChoices):
        IN = "IN", "Entrante"
        OUT = "OUT", "Saliente"

    class Estado(models.TextChoices):
        OK = "OK", "OK"
        SIN_MATCH = "SIN_MATCH", "Sin match"
        IQC_BLOQUEADO = "IQC_BLOQUEADO", "IQC bloqueado"
        ERROR = "ERROR", "Error"

    interfaz = models.ForeignKey(
        InterfazInstrumento,
        on_delete=models.CASCADE,
        related_name="mensajes",
    )
    direccion = models.CharField(max_length=8, choices=Direccion.choices)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.OK)
    sample_id = models.CharField(max_length=32, blank=True, default="")
    crudo = models.TextField(blank=True, default="", help_text="ASTM truncado; sin PHI extra.")
    detalle = models.CharField(max_length=255, blank=True, default="")
    muestra = models.ForeignKey(
        "laboratorio.Muestra",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mensajes_instrumento",
    )
    solicitud = models.ForeignKey(
        "laboratorio.SolicitudExamen",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mensajes_instrumento",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Mensaje de analizador"
        verbose_name_plural = "Mensajes de analizador"
        indexes = [
            models.Index(fields=["estado", "created_at"], name="lab_msg_estado_idx"),
            models.Index(fields=["interfaz", "created_at"], name="lab_msg_interfaz_idx"),
        ]

    def __str__(self):
        return f"{self.interfaz_id} {self.direccion} {self.estado}"
