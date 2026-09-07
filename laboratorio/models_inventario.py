"""Inventario de insumos de laboratorio (tubos, reactivos, medios)."""
from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class InsumoLab(models.Model):
    class Tipo(models.TextChoices):
        REACTIVO = "REACTIVO", "Reactivo"
        TUBO = "TUBO", "Tubo / contenedor"
        MEDIO = "MEDIO", "Medio de cultivo"
        OTRO = "OTRO", "Otro"

    class Composicion(models.TextChoices):
        SOLO_A = "SOLO_A", "Solo A"
        A_B = "A_B", "A + B (mismo cartucho)"
        OTRO = "OTRO", "Otro"

    class CanalAnalizador(models.TextChoices):
        DEDICADO = "DEDICADO", "Línea dedicada"
        ABIERTO = "ABIERTO", "Línea abierta"

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
    equipo = models.ForeignKey(
        "laboratorio.EquipoAnalizador",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="insumos",
        help_text="Equipo asociado (ej. CM260) para filtros de stock.",
    )
    unidad = models.CharField(
        max_length=40,
        default="u",
        help_text="Unidad en la que contás el stock: cartucho, ml, test, etc.",
    )
    stock_min = models.PositiveIntegerField(default=0)
    proveedor = models.CharField(max_length=120, blank=True, default="")
    # Presentación de compra (opcional): caja con N envases de X ml.
    unidades_por_caja = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Cuántos cartuchos/envases trae una caja al comprar (ej. 10).",
    )
    volumen_por_unidad = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Volumen de cada cartucho/pack en ml (ej. 40). Packs hematología/EC90.",
    )
    composicion = models.CharField(
        max_length=20,
        choices=Composicion.choices,
        blank=True,
        default="",
        help_text="Informativo: cartucho solo A o A+B juntos (no duplica stock).",
    )
    canal_analizador = models.CharField(
        max_length=20,
        choices=CanalAnalizador.choices,
        blank=True,
        default="",
        help_text="Línea del analizador si aplica (dedicada / abierta).",
    )
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
        return sum(lote.cantidad for lote in self.lotes.filter(activo=True))


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


class ConsumoInsumoExamen(models.Model):
    """Receta: cuánto de cada SKU físico consume una determinación."""

    tipo_examen = models.ForeignKey(
        "laboratorio.TipoExamen",
        on_delete=models.CASCADE,
        related_name="consumos_insumo",
    )
    insumo = models.ForeignKey(
        InsumoLab,
        on_delete=models.CASCADE,
        related_name="consumos_examen",
    )
    cantidad_por_determinacion = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=1,
        help_text="Unidades del insumo restadas por cada resultado cargado.",
    )
    rol = models.CharField(
        max_length=40,
        blank=True,
        default="",
        help_text="Etiqueta UI opcional (CARTUCHO, DILUYENTE, etc.).",
    )
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Consumo de insumo por examen"
        verbose_name_plural = "Consumos de insumos por examen"
        ordering = ["tipo_examen_id", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["tipo_examen", "insumo"],
                name="uniq_consumo_insumo_examen",
            )
        ]

    def clean(self):
        super().clean()
        if self.cantidad_por_determinacion is not None and self.cantidad_por_determinacion <= 0:
            raise ValidationError(
                {
                    "cantidad_por_determinacion": (
                        "cantidad_por_determinacion debe ser mayor que 0."
                    )
                }
            )
        if self.insumo_id and self.insumo.tipo != InsumoLab.Tipo.REACTIVO:
            raise ValidationError(
                {
                    "insumo": (
                        "Solo se pueden vincular insumos de tipo REACTIVO "
                        "al consumo por examen."
                    )
                }
            )

    def __str__(self):
        return (
            f"{self.tipo_examen_id}→{self.insumo_id} "
            f"x{self.cantidad_por_determinacion}"
        )


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
    resultado_id = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="ResultadoExamen que originó el egreso (idempotencia).",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Movimiento de stock"
        verbose_name_plural = "Movimientos de stock"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.tipo} {self.cantidad} lote={self.lote_id}"
