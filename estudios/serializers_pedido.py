from __future__ import annotations

from rest_framework import serializers

from medicos.models import Medico
from turnos.models import Recurso

from .models import (
    MedicoTipoEstudio,
    PedidoEstudioPaciente,
    TipoEstudioComplementario,
    TipoEstudioSala,
)


class MedicoTipoEstudioSerializer(serializers.ModelSerializer):
    medico_nombre = serializers.CharField(source='medico.nombre_completo', read_only=True)
    tipo_estudio_nombre = serializers.CharField(source='tipo_estudio.nombre', read_only=True)

    class Meta:
        model = MedicoTipoEstudio
        fields = [
            'id',
            'medico',
            'medico_nombre',
            'tipo_estudio',
            'tipo_estudio_nombre',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class TipoEstudioSalaSerializer(serializers.ModelSerializer):
    tipo_estudio_nombre = serializers.CharField(source='tipo_estudio.nombre', read_only=True)
    recurso_nombre = serializers.CharField(source='recurso.nombre', read_only=True)

    class Meta:
        model = TipoEstudioSala
        fields = [
            'id',
            'tipo_estudio',
            'tipo_estudio_nombre',
            'recurso',
            'recurso_nombre',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def validate_recurso(self, value: Recurso):
        if value.tipo_recurso not in (
            Recurso.TipoRecurso.SALA_PROCEDIMIENTO,
            Recurso.TipoRecurso.SALA_HEMODINAMIA,
        ):
            raise serializers.ValidationError(
                'El recurso debe ser sala de procedimiento o hemodinamia.'
            )
        if value.activo is False:
            raise serializers.ValidationError('La sala no está activa.')
        return value


class PedidoEstudioPacienteSerializer(serializers.ModelSerializer):
    paciente_nombre = serializers.CharField(source='paciente.nombre_completo', read_only=True)
    foto_nombre = serializers.SerializerMethodField()
    download_foto_url = serializers.SerializerMethodField()

    class Meta:
        model = PedidoEstudioPaciente
        fields = [
            'id',
            'paciente',
            'paciente_nombre',
            'estado',
            'origen_canal',
            'notas',
            'turno',
            'estudio',
            'foto_nombre',
            'download_foto_url',
            'created_at',
            'agendado_en',
        ]
        read_only_fields = fields

    def get_foto_nombre(self, obj):
        if not obj.foto:
            return None
        import os

        return os.path.basename(obj.foto.name)

    def get_download_foto_url(self, obj):
        request = self.context.get('request')
        if not request or not obj.pk or not obj.foto:
            return None
        return request.build_absolute_uri(f'/api/estudios-complementarios/pedidos/{obj.pk}/download-foto/')


class PedidoEstudioCreateSerializer(serializers.Serializer):
    foto = serializers.ImageField()
    notas = serializers.CharField(required=False, allow_blank=True, max_length=255)
    origen_canal = serializers.ChoiceField(
        choices=PedidoEstudioPaciente.OrigenCanal.choices,
        default=PedidoEstudioPaciente.OrigenCanal.PORTAL,
    )


class AgendarPedidoEstudioSerializer(serializers.Serializer):
    tipo_estudio = serializers.PrimaryKeyRelatedField(
        queryset=TipoEstudioComplementario.objects.filter(activo=True)
    )
    medico_id = serializers.PrimaryKeyRelatedField(queryset=Medico.objects.all(), source='medico')
    inicio = serializers.DateTimeField()
    horario_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)
