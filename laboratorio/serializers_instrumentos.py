"""Serializers de interfaz de analizadores."""
from rest_framework import serializers

from laboratorio.models_instrumentos import (
    InterfazInstrumento,
    MapeoAnalitoInstrumento,
    MensajeInstrumento,
)


class InterfazInstrumentoSerializer(serializers.ModelSerializer):
    equipo_codigo = serializers.CharField(source="equipo.codigo", read_only=True)
    equipo_nombre = serializers.CharField(source="equipo.nombre", read_only=True)

    class Meta:
        model = InterfazInstrumento
        fields = (
            "id",
            "nombre",
            "equipo",
            "equipo_codigo",
            "equipo_nombre",
            "driver",
            "transporte",
            "host",
            "puerto",
            "puerto_serie",
            "activo",
            "ultimo_contacto",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at", "ultimo_contacto")


class MapeoAnalitoInstrumentoSerializer(serializers.ModelSerializer):
    tipo_examen_codigo = serializers.CharField(source="tipo_examen.codigo", read_only=True)
    tipo_examen_nombre = serializers.CharField(source="tipo_examen.nombre", read_only=True)

    class Meta:
        model = MapeoAnalitoInstrumento
        fields = (
            "id",
            "interfaz",
            "codigo_instrumento",
            "tipo_examen",
            "tipo_examen_codigo",
            "tipo_examen_nombre",
            "activo",
        )


class MensajeInstrumentoSerializer(serializers.ModelSerializer):
    interfaz_nombre = serializers.CharField(source="interfaz.nombre", read_only=True)
    interfaz_driver = serializers.CharField(source="interfaz.driver", read_only=True)
    solicitud_numero = serializers.CharField(source="solicitud.numero", read_only=True)

    class Meta:
        model = MensajeInstrumento
        fields = (
            "id",
            "interfaz",
            "interfaz_nombre",
            "interfaz_driver",
            "direccion",
            "estado",
            "sample_id",
            "detalle",
            "muestra",
            "solicitud",
            "solicitud_numero",
            "created_at",
        )
        read_only_fields = fields


class ConsultaTrabajoSerializer(serializers.Serializer):
    interfaz_id = serializers.IntegerField(required=False)
    equipo_codigo = serializers.CharField(required=False, allow_blank=True)
    driver = serializers.CharField(required=False, allow_blank=True)
    sample_id = serializers.CharField(max_length=32)
    crudo = serializers.CharField(required=False, allow_blank=True, default="")


class IngestaItemSerializer(serializers.Serializer):
    codigo_instrumento = serializers.CharField(max_length=32)
    valor = serializers.CharField(max_length=64)
    unidad = serializers.CharField(max_length=32, required=False, allow_blank=True, default="")


class IngestaSerializer(serializers.Serializer):
    interfaz_id = serializers.IntegerField(required=False)
    equipo_codigo = serializers.CharField(required=False, allow_blank=True)
    driver = serializers.CharField(required=False, allow_blank=True)
    sample_id = serializers.CharField(max_length=32)
    resultados = IngestaItemSerializer(many=True)
    crudo = serializers.CharField(required=False, allow_blank=True, default="")
