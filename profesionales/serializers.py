from rest_framework import serializers

from medicos.models import Especialidad

from .models import Profesional


class ProfesionalLightSerializer(serializers.ModelSerializer):
    especialidad_nombre = serializers.CharField(source='especialidad.nombre', read_only=True)
    nombre_completo = serializers.ReadOnlyField()

    class Meta:
        model = Profesional
        fields = [
            'id',
            'nombre',
            'apellido',
            'nombre_completo',
            'matricula',
            'especialidad_nombre',
        ]
        read_only_fields = fields


class ProfesionalSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.ReadOnlyField()
    especialidad_nombre = serializers.CharField(
        source='especialidad.nombre',
        read_only=True,
    )
    especialidad_id = serializers.PrimaryKeyRelatedField(
        queryset=Especialidad.objects.all(),
        source='especialidad',
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Profesional
        fields = [
            'id',
            'user',
            'nombre',
            'apellido',
            'matricula',
            'especialidad_id',
            'especialidad_nombre',
            'nombre_completo',
            'fecha_registro',
            'ultima_actualizacion',
        ]
        read_only_fields = [
            'fecha_registro',
            'ultima_actualizacion',
            'nombre_completo',
            'especialidad_nombre',
        ]
