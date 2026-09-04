"""Serializers QC."""
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from laboratorio.models_qc import (
    Calibracion,
    CorridaQC,
    EquipoAnalizador,
    LoteControl,
    LoteProductoControl,
    MaterialControl,
    ProductoControl,
    PuntoQC,
    TargetLoteControl,
)


class EquipoAnalizadorSerializer(serializers.ModelSerializer):
    class Meta:
        model = EquipoAnalizador
        fields = ["id", "nombre", "codigo", "marca_modelo", "area", "seccion", "activo"]
        extra_kwargs = {
            "codigo": {
                "validators": [
                    UniqueValidator(
                        queryset=EquipoAnalizador.objects.all(),
                        message="Ya existe un equipo con ese código.",
                    )
                ]
            },
            "area": {"required": False, "allow_null": True},
            "seccion": {"required": False, "allow_null": True},
        }


class MaterialControlSerializer(serializers.ModelSerializer):
    tipo_examen_codigo = serializers.CharField(source="tipo_examen.codigo", read_only=True)
    tipo_examen_nombre = serializers.CharField(source="tipo_examen.nombre", read_only=True)
    equipo_codigo = serializers.CharField(source="equipo.codigo", read_only=True, allow_null=True)
    equipo_nombre = serializers.CharField(source="equipo.nombre", read_only=True, allow_null=True)

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
            "equipo",
            "equipo_codigo",
            "equipo_nombre",
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


class ProductoControlSerializer(serializers.ModelSerializer):
    equipo_codigo = serializers.CharField(source="equipo.codigo", read_only=True)
    equipo_nombre = serializers.CharField(source="equipo.nombre", read_only=True)

    class Meta:
        model = ProductoControl
        fields = [
            "id",
            "codigo",
            "nombre",
            "marca",
            "equipo",
            "equipo_codigo",
            "equipo_nombre",
            "modo",
            "activo",
        ]


class TargetLoteControlSerializer(serializers.ModelSerializer):
    tipo_examen_codigo = serializers.CharField(source="tipo_examen.codigo", read_only=True)
    tipo_examen_nombre = serializers.CharField(source="tipo_examen.nombre", read_only=True)

    class Meta:
        model = TargetLoteControl
        fields = [
            "id",
            "lote",
            "tipo_examen",
            "tipo_examen_codigo",
            "tipo_examen_nombre",
            "nivel",
            "media_target",
            "de_target",
        ]


class LoteProductoControlSerializer(serializers.ModelSerializer):
    producto_codigo = serializers.CharField(source="producto.codigo", read_only=True)
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)
    equipo = serializers.IntegerField(source="producto.equipo_id", read_only=True)
    equipo_codigo = serializers.CharField(source="producto.equipo.codigo", read_only=True)
    targets = TargetLoteControlSerializer(many=True, read_only=True)

    class Meta:
        model = LoteProductoControl
        fields = [
            "id",
            "producto",
            "producto_codigo",
            "producto_nombre",
            "equipo",
            "equipo_codigo",
            "codigo_lote",
            "vencimiento",
            "activo",
            "targets",
        ]


class ValorEnsayoQCSerializer(serializers.Serializer):
    tipo_examen = serializers.IntegerField()
    valor = serializers.DecimalField(max_digits=14, decimal_places=4)


class PuntoQCSerializer(serializers.ModelSerializer):
    tipo_examen_codigo = serializers.CharField(
        source="tipo_examen.codigo", read_only=True, allow_null=True
    )

    class Meta:
        model = PuntoQC
        fields = [
            "id",
            "tipo_examen",
            "tipo_examen_codigo",
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
    lote_codigo = serializers.SerializerMethodField()
    material_nombre = serializers.SerializerMethodField()
    producto_nombre = serializers.SerializerMethodField()
    valor = serializers.DecimalField(
        max_digits=14, decimal_places=4, write_only=True, required=False
    )
    modo = serializers.ChoiceField(
        choices=["ACEPTAR_NIVEL", "VALORES", "RECHAZAR_NIVEL"],
        write_only=True,
        required=False,
        default=None,
        allow_null=True,
    )
    valores = ValorEnsayoQCSerializer(many=True, write_only=True, required=False)

    class Meta:
        model = CorridaQC
        fields = [
            "id",
            "equipo",
            "lote_control",
            "lote_producto",
            "nivel",
            "lote_codigo",
            "material_nombre",
            "producto_nombre",
            "fecha",
            "estado",
            "observaciones",
            "puntos",
            "valor",
            "modo",
            "valores",
        ]
        extra_kwargs = {
            "lote_control": {"required": False, "allow_null": True},
            "lote_producto": {"required": False, "allow_null": True},
            "nivel": {"required": False, "allow_blank": True},
            "estado": {"read_only": True},
        }

    def get_lote_codigo(self, obj):
        if obj.lote_producto_id:
            return obj.lote_producto.codigo_lote
        if obj.lote_control_id:
            return obj.lote_control.codigo_lote
        return ""

    def get_material_nombre(self, obj):
        if obj.lote_control_id:
            return obj.lote_control.material.nombre
        return ""

    def get_producto_nombre(self, obj):
        if obj.lote_producto_id:
            return obj.lote_producto.producto.nombre
        return ""

    def validate(self, attrs):
        lote_control = attrs.get("lote_control")
        lote_producto = attrs.get("lote_producto")
        if self.instance is None:
            has_mat = lote_control is not None
            has_prod = lote_producto is not None
            if has_mat == has_prod:
                raise serializers.ValidationError(
                    "La corrida debe tener lote_control (por ensayo) XOR lote_producto (multiparámetro)."
                )
            if has_prod and not attrs.get("nivel"):
                raise serializers.ValidationError(
                    {"nivel": "Requerido para corrida de producto multiparámetro."}
                )
            modo = attrs.get("modo")
            valores = attrs.get("valores") or []
            if has_prod:
                if modo is None:
                    attrs["modo"] = "VALORES" if valores else "ACEPTAR_NIVEL"
                elif modo == "VALORES" and not valores:
                    raise serializers.ValidationError(
                        {"valores": "Modo VALORES requiere al menos un valor por ensayo."}
                    )
            elif modo == "VALORES" and not attrs.get("valor"):
                raise serializers.ValidationError(
                    {"valor": "Modo VALORES en control por ensayo requiere el valor medido."}
                )
        return attrs


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
