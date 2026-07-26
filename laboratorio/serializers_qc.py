"""Serializers QC."""
from rest_framework import serializers

from laboratorio.models_qc import (
    Calibracion,
    CorridaQC,
    EquipoAnalizador,
    LoteControl,
    MaterialControl,
    PuntoQC,
)


class EquipoAnalizadorSerializer(serializers.ModelSerializer):
    class Meta:
        model = EquipoAnalizador
        fields = ["id", "nombre", "codigo", "marca_modelo", "area", "seccion", "activo"]


class MaterialControlSerializer(serializers.ModelSerializer):
    tipo_examen_codigo = serializers.CharField(source="tipo_examen.codigo", read_only=True)
    tipo_examen_nombre = serializers.CharField(source="tipo_examen.nombre", read_only=True)

    class Meta:
        model = MaterialControl
        fields = [
            "id",
            "nombre",
            "marca",
            "producto",
            "nivel",
            "tipo_examen",
            "tipo_examen_codigo",
            "tipo_examen_nombre",
            "media_target",
            "de_target",
            "activo",
        ]


class LoteControlSerializer(serializers.ModelSerializer):
    material_nombre = serializers.CharField(source="material.nombre", read_only=True)

    class Meta:
        model = LoteControl
        fields = [
            "id",
            "material",
            "material_nombre",
            "codigo_lote",
            "vencimiento",
            "activo",
        ]


class PuntoQCSerializer(serializers.ModelSerializer):
    class Meta:
        model = PuntoQC
        fields = [
            "id",
            "valor",
            "z_score",
            "reglas_disparadas",
            "fuera_control",
            "warning",
            "created_at",
        ]
        read_only_fields = fields


class CorridaQCSerializer(serializers.ModelSerializer):
    puntos = PuntoQCSerializer(many=True, read_only=True)
    lote_codigo = serializers.CharField(source="lote_control.codigo_lote", read_only=True)
    material_nombre = serializers.CharField(
        source="lote_control.material.nombre", read_only=True
    )
    valor = serializers.DecimalField(
        max_digits=14, decimal_places=4, write_only=True, required=False
    )

    class Meta:
        model = CorridaQC
        fields = [
            "id",
            "equipo",
            "lote_control",
            "lote_codigo",
            "material_nombre",
            "fecha",
            "estado",
            "observaciones",
            "puntos",
            "valor",
        ]
        read_only_fields = ["estado"]


class CalibracionSerializer(serializers.ModelSerializer):
    equipo_nombre = serializers.CharField(source="equipo.nombre", read_only=True)
    equipo_codigo = serializers.CharField(source="equipo.codigo", read_only=True)
    tipo_examen_codigo = serializers.CharField(
        source="tipo_examen.codigo", read_only=True, allow_null=True
    )
    tipo_examen_nombre = serializers.CharField(
        source="tipo_examen.nombre", read_only=True, allow_null=True
    )

    class Meta:
        model = Calibracion
        fields = [
            "id",
            "equipo",
            "equipo_nombre",
            "equipo_codigo",
            "tipo_examen",
            "tipo_examen_codigo",
            "tipo_examen_nombre",
            "fecha",
            "vigente_hasta",
            "calibrador_nombre",
            "marca",
            "codigo_lote",
            "tipo",
            "puntos_curva",
            "observaciones",
        ]

    def validate(self, attrs):
        tipo = attrs.get("tipo") or getattr(self.instance, "tipo", Calibracion.Tipo.PUNTO_UNICO)
        puntos = attrs.get("puntos_curva")
        if puntos is None and self.instance is not None:
            puntos = self.instance.puntos_curva
        if puntos is None:
            puntos = []
        tipo_examen = attrs.get("tipo_examen")
        if "tipo_examen" not in attrs and self.instance is not None:
            tipo_examen = self.instance.tipo_examen

        if tipo == Calibracion.Tipo.CURVA_MULTIPUNTO:
            if not tipo_examen:
                raise serializers.ValidationError(
                    {"tipo_examen": "Requerido para calibración por curva multipunto."}
                )
            if not isinstance(puntos, list) or len(puntos) < 2:
                raise serializers.ValidationError(
                    {"puntos_curva": "La curva multipunto requiere al menos 2 puntos."}
                )
            for i, p in enumerate(puntos):
                if not isinstance(p, dict):
                    raise serializers.ValidationError(
                        {"puntos_curva": f"Punto {i + 1} inválido (debe ser objeto)."}
                    )
                if p.get("concentracion") in (None, ""):
                    raise serializers.ValidationError(
                        {"puntos_curva": f"Punto {i + 1}: falta concentración."}
                    )
        attrs["puntos_curva"] = puntos if isinstance(puntos, list) else []
        return attrs
