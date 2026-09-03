"""Modelos de control de calidad analítico (Westgard / Levey-Jennings)."""
from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class EquipoAnalizador(models.Model):
    nombre = models.CharField(max_length=200)
    codigo = models.CharField(max_length=40, unique=True)
    marca_modelo = models.CharField(max_length=120, blank=True, default="")
    area = models.ForeignKey(
        "laboratorio.AreaLaboratorio",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="equipos_qc",
    )
    seccion = models.ForeignKey(
        "laboratorio.SeccionLaboratorio",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="equipos_qc",
    )
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} — {self.nombre}"


class ProductoControl(models.Model):
    """Producto físico de control (Standatrol S-E, control Sysmex, kit VIDAS, etc.)."""

    class Modo(models.TextChoices):
        MULTIPARAM = "MULTIPARAM", "Multiparámetro (producto + nivel)"
        POR_ENSAYO = "POR_ENSAYO", "Por ensayo"

    codigo = models.CharField(max_length=40, unique=True)
    nombre = models.CharField(max_length=200)
    marca = models.CharField(max_length=120, blank=True, default="")
    equipo = models.ForeignKey(
        EquipoAnalizador,
        on_delete=models.PROTECT,
        related_name="productos_control",
    )
    modo = models.CharField(max_length=20, choices=Modo.choices, default=Modo.MULTIPARAM)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["equipo__codigo", "nombre"]

    def __str__(self):
        return f"{self.codigo} — {self.nombre}"


class LoteProductoControl(models.Model):
    producto = models.ForeignKey(
        ProductoControl, on_delete=models.CASCADE, related_name="lotes"
    )
    codigo_lote = models.CharField(max_length=80)
    vencimiento = models.DateField()
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("producto", "codigo_lote")]
        ordering = ["-vencimiento"]

    def __str__(self):
        return f"{self.producto.codigo}/{self.codigo_lote}"


class TargetLoteControl(models.Model):
    """Target del inserto: media/DE por ensayo y nivel dentro de un lote de producto."""

    class Nivel(models.TextChoices):
        N1 = "N1", "S1 (normal)"
        N2 = "N2", "S2 (patológico)"
        N3 = "N3", "Nivel 3"

    lote = models.ForeignKey(
        LoteProductoControl, on_delete=models.CASCADE, related_name="targets"
    )
    tipo_examen = models.ForeignKey(
        "laboratorio.TipoExamen",
        on_delete=models.CASCADE,
        related_name="targets_lote_control",
    )
    nivel = models.CharField(max_length=5, choices=Nivel.choices)
    media_target = models.DecimalField(max_digits=12, decimal_places=4)
    de_target = models.DecimalField(max_digits=12, decimal_places=4)

    class Meta:
        unique_together = [("lote", "tipo_examen", "nivel")]
        ordering = ["tipo_examen__codigo", "nivel"]

    def __str__(self):
        return f"{self.lote_id} {self.tipo_examen_id} {self.nivel}"


class MaterialControl(models.Model):
    class Nivel(models.TextChoices):
        N1 = "N1", "S1 (normal)"
        N2 = "N2", "S2 (patológico)"
        N3 = "N3", "Nivel 3"

    nombre = models.CharField(max_length=200)
    marca = models.CharField(max_length=120, blank=True, default="")
    producto = models.CharField(max_length=200, blank=True, default="")
    nivel = models.CharField(max_length=5, choices=Nivel.choices, default=Nivel.N1)
    tipo_examen = models.ForeignKey(
        "laboratorio.TipoExamen",
        on_delete=models.CASCADE,
        related_name="materiales_control",
    )
    equipo = models.ForeignKey(
        EquipoAnalizador,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="materiales_control",
        help_text="Equipo al que pertenece este material de control (IQC).",
    )
    media_target = models.DecimalField(max_digits=12, decimal_places=4)
    de_target = models.DecimalField(max_digits=12, decimal_places=4)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["tipo_examen_id", "nivel"]

    def __str__(self):
        return f"{self.nombre} ({self.nivel})"


class LoteControl(models.Model):
    material = models.ForeignKey(MaterialControl, on_delete=models.CASCADE, related_name="lotes")
    codigo_lote = models.CharField(max_length=80)
    vencimiento = models.DateField()
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("material", "codigo_lote")]
        ordering = ["-vencimiento"]

    def __str__(self):
        return f"{self.material_id}/{self.codigo_lote}"


class CorridaQC(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        ACEPTADA = "ACEPTADA", "Aceptada"
        RECHAZADA = "RECHAZADA", "Rechazada"

    class Nivel(models.TextChoices):
        N1 = "N1", "S1 (normal)"
        N2 = "N2", "S2 (patológico)"
        N3 = "N3", "Nivel 3"

    equipo = models.ForeignKey(
        EquipoAnalizador,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="corridas_qc",
    )
    lote_control = models.ForeignKey(
        LoteControl,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="corridas",
        help_text="Lote de material por ensayo (VIDAS/Finecare / legado).",
    )
    lote_producto = models.ForeignKey(
        LoteProductoControl,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="corridas",
        help_text="Lote de producto multiparámetro (Standatrol, etc.).",
    )
    nivel = models.CharField(
        max_length=5,
        choices=Nivel.choices,
        blank=True,
        default="",
        help_text="Nivel S1/S2 cuando la corrida es de producto multiparámetro.",
    )
    fecha = models.DateTimeField()
    operador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="corridas_qc",
    )
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    observaciones = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha"]

    def clean(self):
        has_mat = self.lote_control_id is not None
        has_prod = self.lote_producto_id is not None
        if has_mat == has_prod:
            raise ValidationError(
                "La corrida debe tener lote_control (por ensayo) XOR lote_producto (multiparámetro)."
            )
        if has_prod and not self.nivel:
            raise ValidationError({"nivel": "Requerido para corrida de producto multiparámetro."})

    def __str__(self):
        return f"QC {self.id} {self.estado}"


class PuntoQC(models.Model):
    corrida = models.ForeignKey(CorridaQC, on_delete=models.CASCADE, related_name="puntos")
    tipo_examen = models.ForeignKey(
        "laboratorio.TipoExamen",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="puntos_qc",
        help_text="Ensayo del punto (corridas multiparámetro).",
    )
    valor = models.DecimalField(max_digits=14, decimal_places=4)
    z_score = models.FloatField(null=True, blank=True)
    reglas_disparadas = models.JSONField(default=list, blank=True)
    fuera_control = models.BooleanField(default=False)
    warning = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"Punto {self.id} z={self.z_score}"


class Calibracion(models.Model):
    class Tipo(models.TextChoices):
        PUNTO_UNICO = "PUNTO_UNICO", "Punto único"
        CURVA_MULTIPUNTO = "CURVA_MULTIPUNTO", "Curva multipunto"

    equipo = models.ForeignKey(EquipoAnalizador, on_delete=models.CASCADE, related_name="calibraciones")
    tipo_examen = models.ForeignKey(
        "laboratorio.TipoExamen",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="calibraciones_qc",
    )
    fecha = models.DateField()
    vigente_hasta = models.DateField()
    calibrador_nombre = models.CharField(max_length=200, blank=True, default="")
    marca = models.CharField(max_length=120, blank=True, default="")
    codigo_lote = models.CharField(max_length=80, blank=True, default="")
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.PUNTO_UNICO)
    puntos_curva = models.JSONField(default=list, blank=True)
    observaciones = models.TextField(blank=True, default="")
    realizada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="calibraciones_qc",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return f"Cal {self.equipo_id} {self.fecha} {self.tipo}"
