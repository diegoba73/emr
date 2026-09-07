"""Serializers inventario LIMS."""
from rest_framework import serializers

from laboratorio.inventario_service import stock_insumo
from laboratorio.models_inventario import (
    ConsumoInsumoExamen,
    InsumoLab,
    LoteInsumo,
    MovimientoStock,
)


class InsumoLabSerializer(serializers.ModelSerializer):
    tipo_contenedor_nombre = serializers.CharField(
        source="tipo_contenedor.nombre", read_only=True, allow_null=True
    )
    medio_cultivo_nombre = serializers.CharField(
        source="medio_cultivo.nombre", read_only=True, allow_null=True
    )
    equipo_codigo = serializers.CharField(
        source="equipo.codigo", read_only=True, allow_null=True
    )
    equipo_nombre = serializers.CharField(
        source="equipo.nombre", read_only=True, allow_null=True
    )
    stock_actual = serializers.SerializerMethodField()

    class Meta:
        model = InsumoLab
        fields = [
            "id",
            "tipo",
            "nombre",
            "codigo",
            "tipo_contenedor",
            "tipo_contenedor_nombre",
            "medio_cultivo",
            "medio_cultivo_nombre",
            "equipo",
            "equipo_codigo",
            "equipo_nombre",
            "unidad",
            "stock_min",
            "stock_actual",
            "proveedor",
            "unidades_por_caja",
            "volumen_por_unidad",
            "composicion",
            "canal_analizador",
            "activo",
        ]

    def get_stock_actual(self, obj):
        return stock_insumo(obj)


class LoteInsumoSerializer(serializers.ModelSerializer):
    insumo_codigo = serializers.CharField(source="insumo.codigo", read_only=True)
    insumo_nombre = serializers.CharField(source="insumo.nombre", read_only=True)
    canal_analizador = serializers.CharField(
        source="insumo.canal_analizador", read_only=True
    )

    class Meta:
        model = LoteInsumo
        fields = [
            "id",
            "insumo",
            "insumo_codigo",
            "insumo_nombre",
            "codigo_lote",
            "cantidad",
            "fecha_vencimiento",
            "ubicacion",
            "activo",
            "canal_analizador",
        ]


class MovimientoStockSerializer(serializers.ModelSerializer):
    lote_codigo = serializers.CharField(source="lote.codigo_lote", read_only=True)
    insumo_codigo = serializers.CharField(source="lote.insumo.codigo", read_only=True)
    canal_analizador = serializers.CharField(
        source="lote.insumo.canal_analizador", read_only=True
    )
    lote_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = MovimientoStock
        fields = [
            "id",
            "tipo",
            "lote",
            "lote_id",
            "lote_codigo",
            "insumo_codigo",
            "canal_analizador",
            "cantidad",
            "motivo",
            "created_at",
            "muestra_id",
            "siembra_id",
            "resultado_id",
        ]
        read_only_fields = [
            "lote",
            "created_at",
            "muestra_id",
            "siembra_id",
            "resultado_id",
        ]


class ConsumoInsumoExamenSerializer(serializers.ModelSerializer):
    tipo_examen_codigo = serializers.CharField(
        source="tipo_examen.codigo", read_only=True
    )
    tipo_examen_nombre = serializers.CharField(
        source="tipo_examen.nombre", read_only=True
    )
    insumo_codigo = serializers.CharField(source="insumo.codigo", read_only=True)
    insumo_nombre = serializers.CharField(source="insumo.nombre", read_only=True)
    insumo_unidad = serializers.CharField(source="insumo.unidad", read_only=True)
    canal_analizador = serializers.CharField(
        source="insumo.canal_analizador", read_only=True
    )
    equipo_codigo = serializers.SerializerMethodField()

    class Meta:
        model = ConsumoInsumoExamen
        fields = [
            "id",
            "tipo_examen",
            "tipo_examen_codigo",
            "tipo_examen_nombre",
            "insumo",
            "insumo_codigo",
            "insumo_nombre",
            "insumo_unidad",
            "canal_analizador",
            "equipo_codigo",
            "cantidad_por_determinacion",
            "rol",
            "activo",
        ]

    def get_equipo_codigo(self, obj):
        te = obj.tipo_examen
        eq = getattr(te, "equipo_analizador", None)
        if eq is not None:
            return eq.codigo
        ins_eq = getattr(obj.insumo, "equipo", None)
        return ins_eq.codigo if ins_eq else None

    def validate_insumo(self, value):
        if value.tipo != InsumoLab.Tipo.REACTIVO:
            raise serializers.ValidationError(
                "Solo se pueden vincular insumos de tipo REACTIVO al consumo por examen."
            )
        return value

    def validate_cantidad_por_determinacion(self, value):
        if value is None or value <= 0:
            raise serializers.ValidationError(
                "cantidad_por_determinacion debe ser mayor que 0."
            )
        return value
