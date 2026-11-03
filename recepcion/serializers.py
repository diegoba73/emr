from rest_framework import serializers

from .models import CoberturaRecepcion, LlegadaRecepcion, PuestoRecepcion, ReglaRuteoRecepcion
from .services import evaluar_prioridad_horario, nombre_publico_paciente


class PuestoRecepcionSerializer(serializers.ModelSerializer):
    label_publico = serializers.CharField(read_only=True)

    class Meta:
        model = PuestoRecepcion
        fields = [
            'id',
            'codigo',
            'nombre',
            'etiqueta_paciente',
            'label_publico',
            'activo',
            'modo',
            'es_fallback',
            'orden',
            'ubicacion',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class ReglaRuteoRecepcionSerializer(serializers.ModelSerializer):
    puesto_nombre = serializers.CharField(source='puesto.nombre', read_only=True)

    class Meta:
        model = ReglaRuteoRecepcion
        fields = [
            'id',
            'puesto',
            'puesto_nombre',
            'nombre',
            'prioridad',
            'activo',
            'tipo_actividad',
            'tipo_recurso',
            'recurso',
            'medico',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class CoberturaRecepcionSerializer(serializers.ModelSerializer):
    puesto_nombre = serializers.CharField(source='puesto.nombre', read_only=True)
    puesto_label = serializers.CharField(source='puesto.label_publico', read_only=True)
    usuario_nombre = serializers.SerializerMethodField()

    class Meta:
        model = CoberturaRecepcion
        fields = [
            'id',
            'usuario',
            'usuario_nombre',
            'fecha',
            'puesto',
            'puesto_nombre',
            'puesto_label',
            'tipos',
            'sede',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['usuario', 'fecha', 'created_at', 'updated_at']

    def get_usuario_nombre(self, obj):
        u = obj.usuario
        return getattr(u, 'get_full_name', lambda: '')() or getattr(u, 'username', '') or str(u.pk)


class LlegadaRecepcionSerializer(serializers.ModelSerializer):
    paciente_nombre = serializers.SerializerMethodField()
    paciente_nombre_publico = serializers.SerializerMethodField()
    paciente_dni = serializers.SerializerMethodField()
    puesto_nombre = serializers.CharField(source='puesto.nombre', read_only=True)
    puesto_label = serializers.CharField(source='puesto.label_publico', read_only=True)
    turno_inicio = serializers.DateTimeField(
        source='turno.fecha_hora_inicio', read_only=True, allow_null=True
    )
    medico_nombre = serializers.SerializerMethodField()
    destino = serializers.SerializerMethodField()
    mensaje_paciente = serializers.SerializerMethodField()
    prioridad = serializers.SerializerMethodField()

    class Meta:
        model = LlegadaRecepcion
        fields = [
            'id',
            'paciente',
            'paciente_nombre',
            'paciente_nombre_publico',
            'paciente_dni',
            'puesto',
            'puesto_nombre',
            'puesto_label',
            'turno',
            'turno_inicio',
            'tipo_actividad',
            'estado_flujo',
            'fecha',
            'checkin_en',
            'llamado_en',
            'destino_recurso',
            'destino_label',
            'destino',
            'medico_nombre',
            'notas',
            'numero_orden_dia',
            'prefijo_llamado',
            'codigo_llamado',
            'zona_llamado',
            'mensaje_paciente',
            'prioridad',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'fecha',
            'checkin_en',
            'llamado_en',
            'numero_orden_dia',
            'prefijo_llamado',
            'codigo_llamado',
            'zona_llamado',
            'created_at',
            'updated_at',
        ]

    def get_paciente_nombre(self, obj):
        p = obj.paciente
        if not p:
            return ''
        return f'{p.apellido or ""}, {p.nombre or ""}'.strip(', ')

    def get_paciente_nombre_publico(self, obj):
        return nombre_publico_paciente(obj.paciente)

    def get_paciente_dni(self, obj):
        return getattr(obj.paciente, 'dni', None) or ''

    def get_medico_nombre(self, obj):
        if obj.turno_id and obj.turno and obj.turno.medico:
            m = obj.turno.medico
            return f'{m.apellido or ""}, {m.nombre or ""}'.strip(', ')
        return ''

    def get_destino(self, obj):
        return obj.destino_label or (
            obj.destino_recurso.nombre if obj.destino_recurso_id else ''
        )

    def get_mensaje_paciente(self, obj):
        return getattr(obj, '_mensaje_paciente', None)

    def get_prioridad(self, obj):
        return evaluar_prioridad_horario(turno=obj.turno if obj.turno_id else None)


class PantallaLlamadoSerializer(serializers.ModelSerializer):
    paciente_nombre_publico = serializers.SerializerMethodField()
    destino = serializers.SerializerMethodField()
    puesto_label = serializers.CharField(source='puesto.label_publico', read_only=True)

    class Meta:
        model = LlegadaRecepcion
        fields = [
            'id',
            'paciente_nombre_publico',
            'tipo_actividad',
            'destino',
            'numero_orden_dia',
            'codigo_llamado',
            'prefijo_llamado',
            'zona_llamado',
            'estado_flujo',
            'llamado_en',
            'puesto_id',
            'puesto_label',
        ]

    def get_paciente_nombre_publico(self, obj):
        return nombre_publico_paciente(obj.paciente)

    def get_destino(self, obj):
        return obj.destino_label or (
            obj.destino_recurso.nombre if obj.destino_recurso_id else obj.puesto.label_publico
        )
