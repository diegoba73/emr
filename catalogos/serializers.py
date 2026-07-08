"""
Serializers para la app catalogos.
"""
from rest_framework import serializers
from .models import (
    CentroFisico,
    TipoAtencion,
    AreaInternacion,
    CamaInternacion,
)
class CentroFisicoSerializer(serializers.ModelSerializer):
    """Serializer para CentroFisico."""
    
    class Meta:
        model = CentroFisico
        fields = [
            'id',
            'codigo',
            'nombre',
            'descripcion',
            'direccion',
            'telefono',
            'activo',
        ]
        read_only_fields = ['id']


class TipoAtencionSerializer(serializers.ModelSerializer):
    """Serializer para TipoAtencion."""
    centro_fisico_nombre = serializers.CharField(
        source='centro_fisico.nombre',
        read_only=True
    )
    
    class Meta:
        model = TipoAtencion
        fields = [
            'id',
            'codigo',
            'nombre',
            'descripcion',
            'centro_fisico',
            'centro_fisico_nombre',
            'requiere_internacion',
            'es_urgencia',
            'activo',
        ]
        read_only_fields = ['id', 'centro_fisico_nombre']


class AreaInternacionSerializer(serializers.ModelSerializer):
    """Serializer de solo lectura para áreas de internación (catálogo)."""

    centro_fisico_nombre = serializers.CharField(
        source='centro_fisico.nombre',
        read_only=True,
    )

    class Meta:
        model = AreaInternacion
        fields = [
            'id',
            'codigo',
            'nombre',
            'descripcion',
            'centro_fisico',
            'centro_fisico_nombre',
            'capacidad_camas',
            'activo',
        ]
        read_only_fields = ['id', 'centro_fisico_nombre']


class CamaInternacionSerializer(serializers.ModelSerializer):
    """Serializer de solo lectura para camas de internación (catálogo)."""

    area_nombre = serializers.CharField(source='area.nombre', read_only=True)

    class Meta:
        model = CamaInternacion
        fields = [
            'id',
            'numero',
            'area',
            'area_nombre',
            'estado',
            'tipo_cama',
            'activa',
        ]
        read_only_fields = ['id', 'area_nombre']
