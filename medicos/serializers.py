"""
Serializers para la app medicos.

El ABM `/api/medicos/` usa `api.serializers.MedicoSerializer` /
`MedicoLightSerializer`. Este módulo queda para especialidades y usos internos.
"""
from rest_framework import serializers

from .models import Especialidad


class EspecialidadSerializer(serializers.ModelSerializer):
    """Serializer básico para Especialidad."""

    class Meta:
        model = Especialidad
        fields = ['id', 'nombre', 'descripcion']
