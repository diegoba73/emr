from __future__ import annotations

from rest_framework import serializers

from pacientes.models import Paciente

from .access import usuario_puede_crear_estudio
from .models import (
    ArchivoEstudioComplementario,
    EstudioComplementario,
    InformeEstudioComplementario,
    TipoEstudioComplementario,
)


class TipoEstudioComplementarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoEstudioComplementario
        fields = (
            'id',
            'codigo',
            'nombre',
            'descripcion',
            'modalidad',
            'requiere_informe',
            'activo',
        )


class EstudioComplementarioListSerializer(serializers.ModelSerializer):
    paciente_id = serializers.IntegerField(read_only=True)
    tipo_estudio_nombre = serializers.CharField(source='tipo_estudio.nombre', read_only=True, default=None)

    class Meta:
        model = EstudioComplementario
        fields = (
            'id',
            'paciente_id',
            'tipo_estudio',
            'tipo_estudio_nombre',
            'estudio_diagnostico',
            'modalidad',
            'estado',
            'fecha_solicitud',
            'fecha_realizacion',
            'centro_realizador',
            'origen',
            'created_at',
            'updated_at',
        )


class EstudioComplementarioDetailSerializer(serializers.ModelSerializer):
    paciente_id = serializers.PrimaryKeyRelatedField(
        queryset=Paciente.objects.all(),
        source='paciente',
    )
    estado = serializers.CharField(read_only=True)

    class Meta:
        model = EstudioComplementario
        fields = (
            'id',
            'paciente_id',
            'tipo_estudio',
            'estudio_diagnostico',
            'modalidad',
            'estado',
            'medico_solicitante',
            'atencion',
            'consulta_hc',
            'solicitud_emr',
            'fecha_solicitud',
            'fecha_realizacion',
            'centro_realizador',
            'origen',
            'descripcion_clinica',
            'accession_number',
            'study_instance_uid',
            'pacs_metadata',
            'motivo_anulacion',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('motivo_anulacion',)

    def validate(self, attrs):
        if 'estado' in self.initial_data:
            raise serializers.ValidationError(
                {'estado': 'El estado no se modifica por PATCH; use las acciones dedicadas.'}
            )
        paciente = attrs.get('paciente') or getattr(self.instance, 'paciente', None)
        request = self.context.get('request')
        if request and paciente and self.instance is None:
            if not usuario_puede_crear_estudio(request.user, paciente):
                raise serializers.ValidationError(
                    {'paciente_id': 'No tiene permiso para crear estudios de este paciente.'}
                )
        inst = self.instance
        estudio = EstudioComplementario(
            paciente=paciente or (inst.paciente if inst else None),
            modalidad=attrs.get('modalidad', getattr(inst, 'modalidad', '')),
            atencion=attrs.get('atencion', getattr(inst, 'atencion', None)),
            consulta_hc=attrs.get('consulta_hc', getattr(inst, 'consulta_hc', None)),
            solicitud_emr=attrs.get('solicitud_emr', getattr(inst, 'solicitud_emr', None)),
            fecha_realizacion=attrs.get('fecha_realizacion', getattr(inst, 'fecha_realizacion', None)),
        )
        try:
            estudio.full_clean()
        except Exception as exc:
            if hasattr(exc, 'message_dict'):
                raise serializers.ValidationError(exc.message_dict) from exc
            raise serializers.ValidationError(str(exc)) from exc
        return attrs


class ArchivoEstudioComplementarioSerializer(serializers.ModelSerializer):
    archivo_medico_id = serializers.IntegerField()
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = ArchivoEstudioComplementario
        fields = (
            'id',
            'archivo_medico_id',
            'tipo_rol',
            'descripcion',
            'orden',
            'es_principal',
            'download_url',
            'created_at',
        )
        read_only_fields = ('id', 'download_url', 'created_at')

    def get_download_url(self, obj) -> str:
        request = self.context.get('request')
        if not request:
            return ''
        estudio_id = obj.estudio_id
        return request.build_absolute_uri(
            f'/api/estudios-complementarios/{estudio_id}/archivos/{obj.pk}/download/'
        )


class AgregarArchivoSerializer(serializers.Serializer):
    archivo_medico_id = serializers.IntegerField()
    tipo_rol = serializers.ChoiceField(
        choices=ArchivoEstudioComplementario.TipoRol.choices,
        default=ArchivoEstudioComplementario.TipoRol.OTRO,
        required=False,
    )
    descripcion = serializers.CharField(required=False, allow_blank=True, default='')
    orden = serializers.IntegerField(required=False, default=0, min_value=0)
    es_principal = serializers.BooleanField(required=False, default=False)


class InformeEstudioComplementarioSerializer(serializers.ModelSerializer):
    estado = serializers.CharField(read_only=True)
    version = serializers.IntegerField(read_only=True)

    class Meta:
        model = InformeEstudioComplementario
        fields = (
            'id',
            'version',
            'estado',
            'tipo',
            'texto',
            'es_vigente',
            'informado_por',
            'fecha_informe',
            'validado_por',
            'fecha_validacion',
            'reemplaza_a',
            'motivo_rectificacion',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'informado_por',
            'fecha_informe',
            'validado_por',
            'fecha_validacion',
            'reemplaza_a',
            'motivo_rectificacion',
        )

    def validate(self, attrs):
        if self.instance and self.instance.estado == InformeEstudioComplementario.EstadoInforme.VALIDADO:
            raise serializers.ValidationError(
                'No se puede editar un informe validado; use rectificación.'
            )
        return attrs


class CrearInformeSerializer(serializers.Serializer):
    texto = serializers.CharField(required=False, allow_blank=True, default='')
    tipo = serializers.ChoiceField(
        choices=InformeEstudioComplementario.TipoInforme.choices,
        default=InformeEstudioComplementario.TipoInforme.FINAL,
        required=False,
    )


class AnularEstudioSerializer(serializers.Serializer):
    motivo_anulacion = serializers.CharField()


class RectificarInformeSerializer(serializers.Serializer):
    motivo_rectificacion = serializers.CharField()
    texto = serializers.CharField(required=False, allow_blank=True, default='')
