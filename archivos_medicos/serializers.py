import os

from rest_framework import serializers

from historias_clinicas.models import Consulta

from .access import (
    resolver_consulta_para_paciente,
    validar_consulta_archivo_para_usuario,
)
from .models import ArchivoMedico


def _archivo_download_path(obj, request) -> str | None:
    if not request or not obj.pk:
        return None
    return request.build_absolute_uri(
        f'/api/archivos-medicos/archivos/{obj.pk}/download/'
    )


class ArchivoMedicoSerializer(serializers.ModelSerializer):
    paciente_id = serializers.IntegerField()
    consulta_id = serializers.IntegerField(required=False, allow_null=True)
    subido_por = serializers.ReadOnlyField(source='subido_por.username')
    paciente_nombre = serializers.ReadOnlyField(source='paciente.nombre_completo')
    archivo = serializers.FileField(write_only=True, required=False, allow_null=True)
    archivo_nombre = serializers.SerializerMethodField()
    archivo_size = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = ArchivoMedico
        fields = [
            'id', 'titulo', 'descripcion', 'tipo_archivo', 'archivo',
            'archivo_nombre', 'archivo_size', 'download_url',
            'paciente_id', 'consulta_id', 'paciente_nombre',
            'fecha_subida', 'fecha_estudio', 'subido_por',
            'es_urgente',
        ]
        read_only_fields = [
            'id', 'fecha_subida', 'subido_por', 'paciente_nombre',
            'archivo_nombre', 'archivo_size', 'download_url',
        ]

    def get_archivo_nombre(self, obj):
        if not obj.archivo:
            return None
        return os.path.basename(obj.archivo.name)

    def get_archivo_size(self, obj):
        try:
            return obj.archivo.size if obj.archivo else None
        except (OSError, ValueError):
            return None

    def get_download_url(self, obj):
        return _archivo_download_path(obj, self.context.get('request'))

    def validate_archivo(self, value):
        if not value:
            return value
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("El archivo no puede ser mayor a 10MB")
        allowed_extensions = [
            '.dcm', '.nii', '.nii.gz', '.jpg', '.jpeg', '.png',
            '.tif', '.tiff', '.pdf', '.doc', '.docx', '.txt',
        ]
        file_extension = os.path.splitext(value.name)[1].lower()
        if file_extension not in allowed_extensions:
            raise serializers.ValidationError(
                f"Extensión no permitida. Extensiones permitidas: {', '.join(allowed_extensions)}"
            )
        return value

    def _paciente_id_efectivo(self, attrs) -> int:
        if 'paciente_id' in attrs:
            return attrs['paciente_id']
        if self.instance:
            return self.instance.paciente_id
        raise serializers.ValidationError({'paciente_id': 'Este campo es obligatorio.'})

    def _consulta_id_efectivo(self, attrs):
        if 'consulta_id' in attrs:
            return attrs['consulta_id']
        if self.instance:
            return self.instance.consulta_id
        return None

    def validate(self, attrs):
        paciente_id = self._paciente_id_efectivo(attrs)
        consulta_id = self._consulta_id_efectivo(attrs)
        request = self.context.get('request')

        if (
            self.instance
            and 'paciente_id' in attrs
            and attrs['paciente_id'] != self.instance.paciente_id
            and 'consulta_id' not in attrs
            and self.instance.consulta_id
        ):
            raise serializers.ValidationError({
                'paciente_id': (
                    'Al cambiar de paciente debe actualizar o quitar consulta_id.'
                ),
            })

        if consulta_id is not None:
            if not request or not request.user.is_authenticated:
                raise serializers.ValidationError({
                    'consulta_id': 'Se requiere autenticación para asociar una consulta.',
                })
            try:
                consulta = resolver_consulta_para_paciente(consulta_id, paciente_id)
                validar_consulta_archivo_para_usuario(request.user, consulta, paciente_id)
            except ValueError as exc:
                raise serializers.ValidationError({'consulta_id': str(exc)}) from exc

        return attrs

    def create(self, validated_data):
        paciente_id = validated_data.pop('paciente_id')
        consulta_id = validated_data.pop('consulta_id', None)
        consulta = None
        if consulta_id is not None:
            consulta = Consulta.objects.get(pk=consulta_id)
        return ArchivoMedico.objects.create(
            paciente_id=paciente_id,
            consulta=consulta,
            **validated_data,
        )

    def update(self, instance, validated_data):
        if 'paciente_id' in validated_data:
            instance.paciente_id = validated_data.pop('paciente_id')
        if 'consulta_id' in validated_data:
            cid = validated_data.pop('consulta_id')
            instance.consulta = Consulta.objects.get(pk=cid) if cid else None
        return super().update(instance, validated_data)


class ArchivoMedicoListSerializer(serializers.ModelSerializer):
    paciente_nombre = serializers.ReadOnlyField(source='paciente.nombre_completo')
    paciente_id = serializers.IntegerField(read_only=True)
    consulta_id = serializers.IntegerField(read_only=True)
    archivo_nombre = serializers.SerializerMethodField()
    archivo_size = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = ArchivoMedico
        fields = [
            'id', 'titulo', 'descripcion', 'tipo_archivo', 'paciente_nombre',
            'paciente_id', 'consulta_id', 'archivo_nombre', 'archivo_size',
            'download_url', 'fecha_subida', 'fecha_estudio', 'es_urgente',
        ]

    def get_archivo_nombre(self, obj):
        if not obj.archivo:
            return None
        return os.path.basename(obj.archivo.name)

    def get_archivo_size(self, obj):
        try:
            return obj.archivo.size if obj.archivo else None
        except (OSError, ValueError):
            return None

    def get_download_url(self, obj):
        return _archivo_download_path(obj, self.context.get('request'))
