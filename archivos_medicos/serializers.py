from rest_framework import serializers
from .models import ArchivoMedico
import os


class ArchivoMedicoSerializer(serializers.ModelSerializer):
    # Exponer IDs para lectura y escritura
    paciente_id = serializers.IntegerField()
    consulta_id = serializers.IntegerField(required=False, allow_null=True)
    subido_por = serializers.ReadOnlyField(source='subido_por.username')
    paciente_nombre = serializers.ReadOnlyField(source='paciente.nombre_completo')

    class Meta:
        model = ArchivoMedico
        fields = [
            'id', 'titulo', 'descripcion', 'tipo_archivo', 'archivo',
            'paciente_id', 'consulta_id', 'paciente_nombre',
            'fecha_subida', 'fecha_estudio', 'subido_por',
            'es_urgente'
        ]
        read_only_fields = ['id', 'fecha_subida', 'subido_por', 'paciente_nombre']

    def validate_archivo(self, value):
        # Para desarrollo, permitir archivos vacíos
        if not value:
            return value  # Permitir archivo vacío en desarrollo
        
        # Validar tamaño del archivo (10MB máximo)
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("El archivo no puede ser mayor a 10MB")
        
        # Validar extensión
        allowed_extensions = [
            '.dcm', '.nii', '.nii.gz', '.jpg', '.jpeg', '.png', 
            '.tif', '.tiff', '.pdf', '.doc', '.docx', '.txt'
        ]
        file_extension = os.path.splitext(value.name)[1].lower()
        if file_extension not in allowed_extensions:
            raise serializers.ValidationError(
                f"Extensión no permitida. Extensiones permitidas: {', '.join(allowed_extensions)}"
            )
        
        return value

    def create(self, validated_data):
        # El subido_por se maneja en perform_create del ViewSet
        return super().create(validated_data)


class ArchivoMedicoListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listar archivos"""
    paciente_nombre = serializers.ReadOnlyField(source='paciente.nombre_completo')
    paciente_id = serializers.IntegerField(read_only=True)
    consulta_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = ArchivoMedico
        fields = [
            'id', 'titulo', 'descripcion', 'tipo_archivo', 'paciente_nombre',
            'paciente_id', 'consulta_id', 'archivo',
            'fecha_subida', 'fecha_estudio', 'es_urgente'
        ]
