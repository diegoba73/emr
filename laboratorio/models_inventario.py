"""Inventario de insumos de laboratorio (tubos, reactivos, medios)."""
from __future__ import annotations

from django.conf import settings
from django.db import models


class InsumoLab(models.Model):
    class Tipo(models.TextChoices):
        REACTIVO = "REACTIVO", "Reactivo"
        TUBO = "TUBO", "Tubo / contenedor"
        MEDIO = "MEDIO", "Medio de cultivo"
        OTRO = "OTRO", "Otro"

    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.OTRO)
    nombre = models.CharField(max_length=200)
    codigo = models.CharField(max_length=40, unique=True)
    tipo_contenedor = models.ForeignKey(
        "laboratorio.TipoContenedor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="insumos",
    )
    medio_cultivo = models.ForeignKey(
        "laboratorio.MedioCultivo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="insumos",
    )
    unidad = models.CharField(max_length=40, default="u")
    stock_min = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Insumo de laboratorio"
        verbose_name_plural = "Insumos de laboratorio"
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} — {self.nombre}"

    @property
    def stock_actual(self) -> int:
        return sum(
            lote.cantidad
            for lote in self.lotes.filter(activo=True)
        )


class LoteInsumo(models.Model):
    insumo = models.ForeignKey(InsumoLab, on_delete=models.CASCADE, related_name="lotes")
    codigo_lote = models.CharField(max_length=80)
    cantidad = models.PositiveIntegerField(default=0)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    ubicacion = models.CharField(max_length=120, blank=True, default="")
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Lote de insumo"
        verbose_name_plural = "Lotes de insumos"
        ordering = ["fecha_vencimiento", "id"]
        unique_together = [("insumo", "codigo_lote")]

    def __str__(self):
        return f"{self.insumo.codigo}/{self.codigo_lote}"


class MovimientoStock(models.Model):
    class Tipo(models.TextChoices):
        INGRESO = "INGRESO", "Ingreso"
        EGRESO = "EGRESO", "Egreso"
        AJUSTE = "AJUSTE", "Ajuste"
        DESCARTE = "DESCARTE", "Descarte"

    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    lote = models.ForeignKey(LoteInsumo, on_delete=models.PROTECT, related_name="movimientos")
    cantidad = models.PositiveIntegerField()
    motivo = models.CharField(max_length=255, blank=True, default="")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimientos_stock_lab",
    )
    muestra_id = models.IntegerField(null=True, blank=True)
    siembra_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Movimiento de stock"
        verbose_name_plural = "Movimientos de stock"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.tipo} {self.cantidad} lote={self.lote_id}"
