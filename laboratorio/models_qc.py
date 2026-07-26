"""Modelos de control de calidad analítico (Westgard / Levey-Jennings)."""
from __future__ import annotations

from django.conf import settings
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

    equipo = models.ForeignKey(
        EquipoAnalizador,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="corridas_qc",
    )
    lote_control = models.ForeignKey(LoteControl, on_delete=models.PROTECT, related_name="corridas")
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

    def __str__(self):
        return f"QC {self.id} {self.estado}"


class PuntoQC(models.Model):
    corrida = models.ForeignKey(CorridaQC, on_delete=models.CASCADE, related_name="puntos")
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
