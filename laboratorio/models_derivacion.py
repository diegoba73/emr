"""Laboratorios externos de derivación (LAC Trelew, IACA Bahía Blanca)."""
from __future__ import annotations

from django.db import models


class LaboratorioDerivacion(models.Model):
    """Destino externo para exámenes que no se procesan en el lab propio."""

    codigo = models.CharField(max_length=20, unique=True, verbose_name="Código")
    nombre = models.CharField(max_length=200, verbose_name="Nombre")
    ciudad = models.CharField(max_length=120, blank=True, default="", verbose_name="Ciudad")
    acepta_sangre = models.BooleanField(default=False, verbose_name="Acepta sangre")
    acepta_orina = models.BooleanField(default=False, verbose_name="Acepta orina")
    acepta_cultivo = models.BooleanField(default=False, verbose_name="Acepta cultivos")
    acepta_cualquier = models.BooleanField(
        default=False,
        verbose_name="Acepta cualquier muestra",
        help_text="Si está activo, no se restringe por tipo de muestra.",
    )
    activo = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Laboratorio de derivación"
        verbose_name_plural = "Laboratorios de derivación"
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} — {self.nombre} ({self.ciudad})"


class EstadoDerivacion(models.TextChoices):
    LOCAL = "LOCAL", "Local (lab propio)"
    PENDIENTE_ENVIO = "PENDIENTE_ENVIO", "Pendiente de envío"
    ENVIADO = "ENVIADO", "Enviado a lab externo"
    RESULTADO_RECIBIDO = "RESULTADO_RECIBIDO", "Resultado externo cargado"
