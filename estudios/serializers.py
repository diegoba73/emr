from __future__ import annotations

from rest_framework import serializers
from usuarios.roles import ROLES_SECRETARIA_INSTITUCIONAL

from archivos_medicos.models import ArchivoMedico
from catalogos.models import CirugiaAbordaje, CirugiaEspecialidad, CirugiaProcedimiento
from pacientes.models import Paciente
from medicos.models import Medico
from turnos.models import Recurso

from .actividad_rules import (
    CAMPOS_A2_PROTEGIDOS,
    MSG_CAMPOS_PROTEGIDOS,
    MSG_CIRUGIA_NO_HABILITADA,
    MSG_MULTI_SESION,
)
from .models import (
    ArchivoEstudioComplementario,
    EstudioComplementario,
    InformeEstudioComplementario,
    TipoEstudioComplementario,
)
from .practicas_cehta import PRACTICA_CHOICES


class TipoEstudioComplementarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoEstudioComplementario
        fields = (
            'id',
            'codigo',
            'nombre',
            'descripcion',
            'practica',
            'requiere_informe',
            'activo',
        )


class EstudioComplementarioListSerializer(serializers.ModelSerializer):
    paciente_id = serializers.IntegerField(read_only=True)
    paciente_nombre = serializers.SerializerMethodField()
    tipo_estudio_nombre = serializers.CharField(source='tipo_estudio.nombre', read_only=True, default=None)
    procedimiento_catalogo_nombre = serializers.CharField(
        source='procedimiento_catalogo.nombre', read_only=True, default=None
    )
    cirugia_especialidad_nombre = serializers.CharField(
        source='cirugia_especialidad.nombre', read_only=True, default=None
    )
    cirugia_procedimiento_nombre = serializers.CharField(
        source='cirugia_procedimiento.nombre', read_only=True, default=None
    )
    cirugia_abordaje_nombre = serializers.CharField(
        source='cirugia_abordaje.nombre', read_only=True, default=None
    )
    turno_id = serializers.IntegerField(source='turno.id', read_only=True, default=None)
    turno_fecha_hora_inicio = serializers.DateTimeField(
        source='turno.fecha_hora_inicio', read_only=True, default=None
    )
    turno_recurso_nombre = serializers.CharField(
        source='turno.recurso.nombre', read_only=True, default=None
    )
    turno_estado = serializers.CharField(source='turno.estado', read_only=True, default=None)

    def get_paciente_nombre(self, obj):
        paciente = getattr(obj, 'paciente', None)
        if not paciente:
            return None
        apellido = (paciente.apellido or '').strip()
        nombre = (paciente.nombre or '').strip()
        if apellido and nombre:
            return f'{apellido}, {nombre}'
        return apellido or nombre or None

    class Meta:
        model = EstudioComplementario
        fields = (
            'id',
            'paciente_id',
            'paciente_nombre',
            'tipo_estudio',
            'tipo_estudio_nombre',
            'estudio_diagnostico',
            'practica',
            'tipo_actividad',
            'procedimiento_catalogo',
            'procedimiento_catalogo_nombre',
            'cirugia_especialidad',
            'cirugia_especialidad_nombre',
            'cirugia_especialidad_snapshot',
            'cirugia_procedimiento',
            'cirugia_procedimiento_nombre',
            'cirugia_procedimiento_snapshot',
            'cirugia_abordaje',
            'cirugia_abordaje_nombre',
            'cirugia_abordaje_snapshot',
            'clasificacion_quirurgica_snapshot',
            'permite_multi_sesion',
            'estado',
            'fecha_solicitud',
            'fecha_realizacion',
            'centro_realizador',
            'origen',
            'turno_id',
            'turno_fecha_hora_inicio',
            'turno_recurso_nombre',
            'turno_estado',
            'created_at',
            'updated_at',
        )
        read_only_fields = CAMPOS_A2_PROTEGIDOS


class EstudioComplementarioDetailSerializer(serializers.ModelSerializer):
    paciente_id = serializers.PrimaryKeyRelatedField(
        queryset=Paciente.objects.all(),
        source='paciente',
    )
    tipo_estudio_nombre = serializers.CharField(
        source='tipo_estudio.nombre', read_only=True, default=None
    )
    procedimiento_catalogo_nombre = serializers.CharField(
        source='procedimiento_catalogo.nombre', read_only=True, default=None
    )
    cirugia_especialidad = serializers.PrimaryKeyRelatedField(
        queryset=CirugiaEspecialidad.objects.all(),
        required=False,
        allow_null=True,
    )
    cirugia_procedimiento = serializers.PrimaryKeyRelatedField(
        queryset=CirugiaProcedimiento.objects.all(),
        required=False,
        allow_null=True,
    )
    cirugia_abordaje = serializers.PrimaryKeyRelatedField(
        queryset=CirugiaAbordaje.objects.all(),
        required=False,
        allow_null=True,
    )
    cirugia_especialidad_nombre = serializers.CharField(
        source='cirugia_especialidad.nombre', read_only=True, default=None
    )
    cirugia_procedimiento_nombre = serializers.CharField(
        source='cirugia_procedimiento.nombre', read_only=True, default=None
    )
    cirugia_abordaje_nombre = serializers.CharField(
        source='cirugia_abordaje.nombre', read_only=True, default=None
    )
    estado = serializers.CharField(read_only=True)
    turno_id = serializers.IntegerField(source='turno.id', read_only=True, default=None)
    turno_fecha_hora_inicio = serializers.DateTimeField(
        source='turno.fecha_hora_inicio', read_only=True, default=None
    )
    turno_fecha_hora_fin = serializers.DateTimeField(
        source='turno.fecha_hora_fin', read_only=True, default=None
    )
    turno_recurso_id = serializers.IntegerField(
        source='turno.recurso_id', read_only=True, default=None
    )
    turno_recurso_nombre = serializers.CharField(
        source='turno.recurso.nombre', read_only=True, default=None
    )
    turno_estado = serializers.CharField(source='turno.estado', read_only=True, default=None)
    realizado_por = serializers.IntegerField(source='realizado_por_id', read_only=True, allow_null=True)
    realizado_por_nombre = serializers.SerializerMethodField()
    cerrado_por = serializers.IntegerField(source='cerrado_por_id', read_only=True, allow_null=True)
    fecha_cierre = serializers.DateTimeField(read_only=True, allow_null=True)
    protocolo_cierre_informe = serializers.IntegerField(
        source='protocolo_cierre_informe_id', read_only=True, allow_null=True
    )

    def get_realizado_por_nombre(self, obj) -> str | None:
        user = getattr(obj, 'realizado_por', None)
        if not user:
            return None
        full = (getattr(user, 'get_full_name', lambda: '')() or '').strip()
        if full:
            return full
        return getattr(user, 'username', None) or str(user.pk)

    medico_solicitante = serializers.PrimaryKeyRelatedField(
        queryset=Medico.objects.all(),
        required=False,
        allow_null=True,
    )
    anestesista_previsto = serializers.PrimaryKeyRelatedField(
        queryset=Medico.objects.all(),
        required=False,
        allow_null=True,
    )
    medico_solicitante_nombre = serializers.SerializerMethodField()
    anestesista_previsto_nombre = serializers.SerializerMethodField()

    @staticmethod
    def _nombre_medico(med) -> str | None:
        if not med:
            return None
        apellido = (getattr(med, 'apellido', None) or '').strip()
        nombre = (getattr(med, 'nombre', None) or '').strip()
        if apellido and nombre:
            return f'{apellido}, {nombre}'
        return apellido or nombre or None

    def get_medico_solicitante_nombre(self, obj) -> str | None:
        return self._nombre_medico(getattr(obj, 'medico_solicitante', None))

    def get_anestesista_previsto_nombre(self, obj) -> str | None:
        return self._nombre_medico(getattr(obj, 'anestesista_previsto', None))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance is not None:
            self.fields['paciente_id'].read_only = True
            # PATCH: campos A2 siguen read-only (también en Meta).
        else:
            # C/D: alta puede enviar tipo_actividad + catálogos.
            for key in (
                'tipo_actividad',
                'procedimiento_catalogo',
                'cirugia_especialidad',
                'cirugia_procedimiento',
                'cirugia_abordaje',
                'clasificacion_quirurgica_snapshot',
                'medico_solicitante',
                'anestesista_previsto',
            ):
                if key in self.fields:
                    self.fields[key].read_only = False
            if 'permite_multi_sesion' in self.fields:
                self.fields['permite_multi_sesion'].read_only = True

    class Meta:
        model = EstudioComplementario
        fields = (
            'id',
            'paciente_id',
            'tipo_estudio',
            'tipo_estudio_nombre',
            'estudio_diagnostico',
            'practica',
            'tipo_actividad',
            'procedimiento_catalogo',
            'procedimiento_catalogo_nombre',
            'cirugia_especialidad',
            'cirugia_especialidad_nombre',
            'cirugia_especialidad_snapshot',
            'cirugia_procedimiento',
            'cirugia_procedimiento_nombre',
            'cirugia_procedimiento_snapshot',
            'cirugia_abordaje',
            'cirugia_abordaje_nombre',
            'cirugia_abordaje_snapshot',
            'clasificacion_quirurgica_snapshot',
            'permite_multi_sesion',
            'estado',
            'medico_solicitante',
            'medico_solicitante_nombre',
            'anestesista_previsto',
            'anestesista_previsto_nombre',
            'realizado_por',
            'realizado_por_nombre',
            'cerrado_por',
            'fecha_cierre',
            'protocolo_cierre_informe',
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
            'turno_id',
            'turno_fecha_hora_inicio',
            'turno_fecha_hora_fin',
            'turno_recurso_id',
            'turno_recurso_nombre',
            'turno_estado',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'motivo_anulacion',
            'medico_solicitante_nombre',
            'anestesista_previsto_nombre',
            'realizado_por',
            'realizado_por_nombre',
            'cerrado_por',
            'fecha_cierre',
            'protocolo_cierre_informe',
            'procedimiento_catalogo_nombre',
            'cirugia_especialidad_nombre',
            'cirugia_procedimiento_nombre',
            'cirugia_abordaje_nombre',
            'cirugia_especialidad_snapshot',
            'cirugia_procedimiento_snapshot',
            'cirugia_abordaje_snapshot',
            'permite_multi_sesion',
            # tipo_actividad / procedimiento / snapshot: writable en create vía __init__
        )

    def validate(self, attrs):
        if 'estado' in self.initial_data:
            raise serializers.ValidationError(
                {'estado': 'El estado no se modifica por PATCH; use las acciones dedicadas.'}
            )
        if self.instance is not None:
            # PATCH: cualquier mención de campos A2 protegidos → 400.
            protected_sent = [k for k in CAMPOS_A2_PROTEGIDOS if k in self.initial_data]
            if protected_sent:
                raise serializers.ValidationError(
                    {k: MSG_CAMPOS_PROTEGIDOS for k in protected_sent}
                )
        else:
            # Create: PROCEDIMIENTO (C) / CIRUGIA (D); multi off.
            raw_tipo = self.initial_data.get('tipo_actividad') or EstudioComplementario.TipoActividad.ESTUDIO
            if self.initial_data.get('permite_multi_sesion') in (True, 'true', 'True', 1, '1'):
                raise serializers.ValidationError(
                    {'permite_multi_sesion': MSG_MULTI_SESION}
                )
            if self.initial_data.get('medico_solicitante') in (None, '', []):
                raise serializers.ValidationError(
                    {
                        'medico_solicitante': (
                            'Indique el profesional responsable '
                            '(cirujano en CIRUGIA; profesional en estudio/procedimiento).'
                        )
                    }
                )
            if raw_tipo == EstudioComplementario.TipoActividad.PROCEDIMIENTO:
                if self.initial_data.get('procedimiento_catalogo') in (None, '', []):
                    raise serializers.ValidationError(
                        {'procedimiento_catalogo': 'PROCEDIMIENTO exige procedimiento_catalogo.'}
                    )
                if self.initial_data.get('anestesista_previsto') not in (None, '', []):
                    raise serializers.ValidationError(
                        {'anestesista_previsto': 'Solo CIRUGIA admite anestesista previsto.'}
                    )
            elif raw_tipo == EstudioComplementario.TipoActividad.CIRUGIA:
                if self.initial_data.get('cirugia_especialidad') in (None, '', []):
                    raise serializers.ValidationError(
                        {'cirugia_especialidad': 'CIRUGIA exige especialidad del catálogo quirúrgico.'}
                    )
                if self.initial_data.get('cirugia_procedimiento') in (None, '', []):
                    raise serializers.ValidationError(
                        {'cirugia_procedimiento': 'CIRUGIA exige procedimiento del catálogo quirúrgico.'}
                    )
                if self.initial_data.get('anestesista_previsto') in (None, '', []):
                    raise serializers.ValidationError(
                        {'anestesista_previsto': 'CIRUGIA exige anestesista previsto en el alta.'}
                    )
            else:
                if self.initial_data.get('procedimiento_catalogo') not in (None, '', []):
                    raise serializers.ValidationError(
                        {'procedimiento_catalogo': MSG_CAMPOS_PROTEGIDOS}
                    )
                for k in (
                    'cirugia_especialidad',
                    'cirugia_procedimiento',
                    'cirugia_abordaje',
                ):
                    if self.initial_data.get(k) not in (None, '', []):
                        raise serializers.ValidationError({k: MSG_CAMPOS_PROTEGIDOS})
                if self.initial_data.get('anestesista_previsto') not in (None, '', []):
                    raise serializers.ValidationError(
                        {'anestesista_previsto': 'Solo CIRUGIA admite anestesista previsto.'}
                    )
                if self.initial_data.get('clasificacion_quirurgica_snapshot') not in (
                    None,
                    '',
                ):
                    raise serializers.ValidationError(
                        {'clasificacion_quirurgica_snapshot': MSG_CAMPOS_PROTEGIDOS}
                    )
        inst = self.instance
        if inst is not None:
            nuevo_paciente = attrs.get('paciente')
            if nuevo_paciente is not None and nuevo_paciente.pk != inst.paciente_id:
                raise serializers.ValidationError(
                    {
                        'paciente_id': (
                            'No se puede cambiar el paciente del estudio por PATCH.'
                        ),
                    }
                )
            for key in ('paciente_id', 'paciente'):
                if key not in self.initial_data:
                    continue
                raw = self.initial_data.get(key)
                try:
                    if int(raw) != inst.paciente_id:
                        raise serializers.ValidationError(
                            {
                                key: (
                                    'No se puede cambiar el paciente del estudio por PATCH.'
                                ),
                            }
                        )
                except (TypeError, ValueError):
                    raise serializers.ValidationError(
                        {key: 'Valor de paciente inválido en PATCH.'},
                    ) from None
        paciente = attrs.get('paciente') or getattr(inst, 'paciente', None)
        # Permiso de alta: lo resuelve el viewset con PermissionDenied (403).
        if inst is None:
            raw_tipo = (
                self.initial_data.get('tipo_actividad')
                or attrs.get('tipo_actividad')
                or EstudioComplementario.TipoActividad.ESTUDIO
            )
            tipo_act = raw_tipo
            proc = attrs.get('procedimiento_catalogo')
            snap = None
            cir_esp = attrs.get('cirugia_especialidad')
            cir_proc = attrs.get('cirugia_procedimiento')
            cir_abr = attrs.get('cirugia_abordaje')
            if tipo_act == EstudioComplementario.TipoActividad.PROCEDIMIENTO:
                snap = EstudioComplementario.ClasificacionQuirurgicaSnapshot.NO_QUIRURGICO
                attrs['tipo_actividad'] = tipo_act
                attrs['clasificacion_quirurgica_snapshot'] = snap
                attrs['tipo_estudio'] = None
                attrs['practica'] = None
                cir_esp = cir_proc = cir_abr = None
            elif tipo_act == EstudioComplementario.TipoActividad.CIRUGIA:
                snap = EstudioComplementario.ClasificacionQuirurgicaSnapshot.QUIRURGICO
                attrs['tipo_actividad'] = tipo_act
                attrs['clasificacion_quirurgica_snapshot'] = snap
                attrs['tipo_estudio'] = None
                attrs['practica'] = None
                proc = None
                attrs['procedimiento_catalogo'] = None
            else:
                tipo_act = EstudioComplementario.TipoActividad.ESTUDIO
                attrs['tipo_actividad'] = tipo_act
                attrs['procedimiento_catalogo'] = None
                attrs['clasificacion_quirurgica_snapshot'] = None
                proc = None
                cir_esp = cir_proc = cir_abr = None
            estudio = EstudioComplementario(
                paciente=paciente,
                tipo_estudio=attrs.get('tipo_estudio'),
                practica=attrs.get('practica') or None,
                tipo_actividad=tipo_act,
                procedimiento_catalogo=proc,
                cirugia_especialidad=cir_esp,
                cirugia_procedimiento=cir_proc,
                cirugia_abordaje=cir_abr,
                clasificacion_quirurgica_snapshot=snap,
                atencion=attrs.get('atencion'),
                consulta_hc=attrs.get('consulta_hc'),
                solicitud_emr=attrs.get('solicitud_emr'),
                fecha_realizacion=attrs.get('fecha_realizacion'),
            )
        else:
            estudio = EstudioComplementario(
                paciente=paciente or inst.paciente,
                tipo_estudio=attrs.get('tipo_estudio', inst.tipo_estudio),
                practica=attrs.get('practica', getattr(inst, 'practica', '') or None),
                tipo_actividad=inst.tipo_actividad or EstudioComplementario.TipoActividad.ESTUDIO,
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
    titulo = serializers.CharField(source='archivo_medico.titulo', read_only=True)
    tipo_archivo = serializers.CharField(source='archivo_medico.tipo_archivo', read_only=True)
    archivo_nombre = serializers.SerializerMethodField()

    class Meta:
        model = ArchivoEstudioComplementario
        fields = (
            'id',
            'archivo_medico_id',
            'titulo',
            'tipo_archivo',
            'archivo_nombre',
            'tipo_rol',
            'descripcion',
            'orden',
            'es_principal',
            'download_url',
            'created_at',
        )
        read_only_fields = (
            'id',
            'titulo',
            'tipo_archivo',
            'archivo_nombre',
            'download_url',
            'created_at',
        )

    def get_archivo_nombre(self, obj) -> str | None:
        archivo = getattr(obj.archivo_medico, 'archivo', None)
        if not archivo or not getattr(archivo, 'name', None):
            return None
        import os
        return os.path.basename(archivo.name)

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


class SubirArchivoEstudioSerializer(serializers.Serializer):
    archivo = serializers.FileField()
    titulo = serializers.CharField(required=False, allow_blank=True, max_length=200, default='')
    tipo_archivo = serializers.ChoiceField(
        choices=ArchivoMedico.TIPO_CHOICES,
        default='PDF',
        required=False,
    )
    tipo_rol = serializers.ChoiceField(
        choices=ArchivoEstudioComplementario.TipoRol.choices,
        default=ArchivoEstudioComplementario.TipoRol.OTRO,
        required=False,
    )
    descripcion = serializers.CharField(required=False, allow_blank=True, default='')
    orden = serializers.IntegerField(required=False, default=0, min_value=0)
    es_principal = serializers.BooleanField(required=False, default=False)


class SugerirInformeEstudioSerializer(serializers.Serializer):
    notas_medico = serializers.CharField(required=False, allow_blank=True, default='', max_length=4000)
    prefer_medgemma = serializers.BooleanField(required=False, default=True)


class QuitarArchivoEstudioSerializer(serializers.Serializer):
    archivo_estudio_id = serializers.IntegerField(min_value=1)


class InformeEstudioComplementarioSerializer(serializers.ModelSerializer):
    estado = serializers.CharField(read_only=True)
    version = serializers.IntegerField(read_only=True)
    tiene_pdf = serializers.SerializerMethodField()
    download_pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = InformeEstudioComplementario
        fields = (
            'id',
            'version',
            'estado',
            'tipo',
            'texto',
            'es_vigente',
            'tiene_pdf',
            'download_pdf_url',
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

    def get_tiene_pdf(self, obj) -> bool:
        return bool(obj.archivo_pdf)

    def get_download_pdf_url(self, obj) -> str:
        request = self.context.get('request')
        if not request or not obj.archivo_pdf:
            return ''
        estudio_id = obj.estudio_id
        return request.build_absolute_uri(
            f'/api/estudios-complementarios/{estudio_id}/informes/{obj.pk}/download-pdf/'
        )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None
        rol = str(getattr(user, 'rol', '') or '').lower() if user else ''
        if rol == 'enfermeria' or rol in ROLES_SECRETARIA_INSTITUCIONAL:
            validado = (
                instance.estado == InformeEstudioComplementario.EstadoInforme.VALIDADO
                and instance.es_vigente
            )
            if not validado:
                data['texto'] = ''
            if not validado or not instance.archivo_pdf:
                data['download_pdf_url'] = ''
        return data

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


class MarcarRealizadoEstudioSerializer(serializers.Serializer):
    """C/D: profesional; CIRUGIA exige anestesista + dx pre; recurso según tipo."""

    profesional_id = serializers.PrimaryKeyRelatedField(
        queryset=Medico.objects.all(),
        source='profesional',
        required=False,
        allow_null=True,
    )
    anestesista_id = serializers.PrimaryKeyRelatedField(
        queryset=Medico.objects.all(),
        source='anestesista',
        required=False,
        allow_null=True,
    )
    diagnostico_preoperatorio = serializers.CharField(
        required=False, allow_blank=True, allow_null=True,
    )
    recurso_id = serializers.PrimaryKeyRelatedField(
        queryset=Recurso.objects.filter(activo=True),
        source='recurso',
        required=False,
        allow_null=True,
    )
    fecha_realizacion = serializers.DateTimeField(required=False, allow_null=True)


class AsignarTurnoEstudioSerializer(serializers.Serializer):
    recurso_id = serializers.PrimaryKeyRelatedField(
        queryset=Recurso.objects.filter(activo=True),
        source='recurso',
    )
    fecha_hora_inicio = serializers.DateTimeField()
    fecha_hora_fin = serializers.DateTimeField()
    medico_id = serializers.PrimaryKeyRelatedField(
        queryset=Medico.objects.all(),
        source='medico',
        required=False,
        allow_null=True,
    )
    sesion_id = serializers.IntegerField(required=False, allow_null=True)


class ReprogramarTurnoEstudioSerializer(serializers.Serializer):
    recurso_id = serializers.PrimaryKeyRelatedField(
        queryset=Recurso.objects.filter(activo=True),
        source='recurso',
    )
    fecha_hora_inicio = serializers.DateTimeField()
    fecha_hora_fin = serializers.DateTimeField()
    motivo = serializers.CharField()
    medico_id = serializers.PrimaryKeyRelatedField(
        queryset=Medico.objects.all(),
        source='medico',
        required=False,
        allow_null=True,
    )
    sesion_id = serializers.IntegerField(required=False, allow_null=True)


class AgendarTurnoEstudioDesdeAgendaSerializer(serializers.Serializer):
    """Crea estudio (si hace falta) y asigna turno de sala en un solo paso."""

    paciente_id = serializers.PrimaryKeyRelatedField(
        queryset=Paciente.objects.all(),
        source='paciente',
    )
    recurso_id = serializers.PrimaryKeyRelatedField(
        queryset=Recurso.objects.filter(activo=True),
        source='recurso',
    )
    fecha_hora_inicio = serializers.DateTimeField()
    fecha_hora_fin = serializers.DateTimeField()
    estudio_id = serializers.PrimaryKeyRelatedField(
        queryset=EstudioComplementario.objects.filter(
            estado=EstudioComplementario.Estado.SOLICITADO,
            turno__isnull=True,
        ),
        source='estudio',
        required=False,
        allow_null=True,
    )
    tipo_estudio = serializers.PrimaryKeyRelatedField(
        queryset=TipoEstudioComplementario.objects.filter(activo=True),
        required=False,
        allow_null=True,
    )
    practica = serializers.ChoiceField(
        choices=PRACTICA_CHOICES,
        required=False,
        allow_blank=True,
    )
    origen = serializers.ChoiceField(
        choices=EstudioComplementario.Origen.choices,
        required=False,
        default=EstudioComplementario.Origen.EXTERNO,
    )
    descripcion_clinica = serializers.CharField(required=False, allow_blank=True, default='')
    medico_id = serializers.PrimaryKeyRelatedField(
        queryset=Medico.objects.all(),
        source='medico',
        required=False,
        allow_null=True,
    )
    sesion_id = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, attrs):
        if attrs.get('estudio'):
            return attrs
        if not attrs.get('tipo_estudio') and not attrs.get('practica'):
            raise serializers.ValidationError(
                'Indique tipo_estudio o practica para registrar el estudio.'
            )
        return attrs


class RectificarInformeSerializer(serializers.Serializer):
    motivo_rectificacion = serializers.CharField()
    texto = serializers.CharField(required=False, allow_blank=True, default='')


class CorreccionClasificacionSnapshotSerializer(serializers.Serializer):
    """A2b — body de corrección admin (snapshot compatible + motivo)."""

    clasificacion_quirurgica_snapshot = serializers.ChoiceField(
        choices=EstudioComplementario.ClasificacionQuirurgicaSnapshot.choices,
    )
    motivo = serializers.CharField(allow_blank=False, trim_whitespace=True)
