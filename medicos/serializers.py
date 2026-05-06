"""
Serializers para la app medicos.
"""
from rest_framework import serializers
from .models import Medico, Especialidad


class EspecialidadSerializer(serializers.ModelSerializer):
    """Serializer básico para Especialidad."""
    
    class Meta:
        model = Especialidad
        fields = ['id', 'nombre', 'descripcion']


class MedicoSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo Medico.
    Incluye campos calculados y relación con especialidad.
    """
    nombre_completo = serializers.ReadOnlyField(help_text="Nombre completo del médico")
    especialidad_nombre = serializers.CharField(
        source='especialidad.nombre',
        read_only=True,
        help_text="Nombre de la especialidad"
    )
    especialidad_id = serializers.PrimaryKeyRelatedField(
        queryset=Especialidad.objects.all(),
        source='especialidad',
        write_only=True,
        required=False,
        allow_null=True,
        help_text="ID de la especialidad para escritura"
    )

    class Meta:
        model = Medico
        fields = [
            'id',
            'user',
            'nombre',
            'apellido',
            'matricula',
            'especialidad_id',
            'especialidad_nombre',
            'nombre_completo',
            'areas_interes_ia',
            'fecha_registro',
            'ultima_actualizacion',
        ]
        read_only_fields = ['fecha_registro', 'ultima_actualizacion', 'nombre_completo', 'especialidad_nombre']

