"""Serializers inventario LIMS."""
from rest_framework import serializers

from laboratorio.inventario_service import stock_insumo
from laboratorio.models_inventario import InsumoLab, LoteInsumo, MovimientoStock


class InsumoLabSerializer(serializers.ModelSerializer):
    tipo_contenedor_nombre = serializers.CharField(
        source="tipo_contenedor.nombre", read_only=True, allow_null=True
    )
    medio_cultivo_nombre = serializers.CharField(
        source="medio_cultivo.nombre", read_only=True, allow_null=True
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
            "unidad",
            "stock_min",
            "stock_actual",
            "activo",
        ]

    def get_stock_actual(self, obj):
        return stock_insumo(obj)


class LoteInsumoSerializer(serializers.ModelSerializer):
    insumo_codigo = serializers.CharField(source="insumo.codigo", read_only=True)
    insumo_nombre = serializers.CharField(source="insumo.nombre", read_only=True)

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
        ]


class MovimientoStockSerializer(serializers.ModelSerializer):
    lote_codigo = serializers.CharField(source="lote.codigo_lote", read_only=True)
    insumo_codigo = serializers.CharField(source="lote.insumo.codigo", read_only=True)
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
            "cantidad",
            "motivo",
            "created_at",
            "muestra_id",
            "siembra_id",
        ]
        read_only_fields = ["lote", "created_at", "muestra_id", "siembra_id"]
