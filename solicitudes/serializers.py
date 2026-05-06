from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.utils import timezone
from .models import Solicitud

class SolicitudSerializer(serializers.ModelSerializer):
    """Serializer principal para el modelo Solicitud"""
    
    # Campos de solo lectura para mostrar información relacionada
    paciente_info = serializers.SerializerMethodField()
    medico_solicitante_info = serializers.SerializerMethodField()
    medicos_asignados_info = serializers.SerializerMethodField()
    
    # Campos calculados
    dias_pendiente = serializers.ReadOnlyField()
    esta_vencida = serializers.ReadOnlyField()
    medicos_asignados_display = serializers.ReadOnlyField()
    
    # Campos de auditoría (solo lectura)
    creado_por = serializers.ReadOnlyField(source='creado_por.username')
    modificado_por = serializers.ReadOnlyField(source='modificado_por.username')
    fecha_creacion = serializers.ReadOnlyField()
    fecha_modificacion = serializers.ReadOnlyField()
    
    class Meta:
        model = Solicitud
        fields = [
            'id',
            'paciente',
            'paciente_info',
            'medico_solicitante',
            'medico_solicitante_info',
            'medicos_asignados',
            'medicos_asignados_info',
            'tipo_solicitud',
            'descripcion',
            'observaciones',
            'lims_paneles',
            'lims_tipos_examen',
            'fecha_solicitud',
            'fecha_limite',
            'fecha_completada',
            'estado',
            'prioridad',
            'lims_id',
            'sincronizado_lims',
            'ultima_sincronizacion',
            'dias_pendiente',
            'esta_vencida',
            'medicos_asignados_display',
            'creado_por',
            'modificado_por',
            'fecha_creacion',
            'fecha_modificacion',
        ]
        read_only_fields = [
            'id',
            'fecha_solicitud',
            'fecha_creacion',
            'fecha_modificacion',
            'ultima_sincronizacion',
            'dias_pendiente',
            'esta_vencida',
            'medicos_asignados_display',
            'creado_por',
            'modificado_por',
        ]

    def validate_fecha_limite(self, value):
        """Valida que la fecha límite sea futura"""
        if value and value <= timezone.now():
            raise serializers.ValidationError(
                "La fecha límite debe ser futura"
            )
        return value

    def validate_fecha_completada(self, value):
        """Valida que la fecha de completado no sea futura"""
        if value and value > timezone.now():
            raise serializers.ValidationError(
                "La fecha de completado no puede ser futura"
            )
        return value

    def get_paciente_info(self, obj):
        """Retorna información básica del paciente"""
        if obj.paciente:
            return {
                'id': obj.paciente.id,
                'nombre': obj.paciente.nombre,
                'apellido': obj.paciente.apellido,
                'dni': obj.paciente.dni,
                'nombre_completo': obj.paciente.nombre_completo,
            }
        return None

    def get_medico_solicitante_info(self, obj):
        """Retorna información básica del médico solicitante"""
        if obj.medico_solicitante:
            nombre_completo = getattr(obj.medico_solicitante, 'nombre_completo', None)
            if not nombre_completo:
                nombre = getattr(obj.medico_solicitante, 'nombre', '')
                apellido = getattr(obj.medico_solicitante, 'apellido', '')
                nombre_completo = f"{nombre} {apellido}".strip()
            return {
                'id': obj.medico_solicitante.id,
                'nombre': obj.medico_solicitante.nombre,
                'apellido': obj.medico_solicitante.apellido,
                'especialidad': obj.medico_solicitante.especialidad,
                'nombre_completo': nombre_completo,
            }
        return None

    def get_medicos_asignados_info(self, obj):
        """Retorna información básica de los médicos asignados"""
        medicos = []
        for medico in obj.medicos_asignados.all():
            nombre_completo = getattr(medico, 'nombre_completo', None)
            if not nombre_completo:
                nombre = getattr(medico, 'nombre', '')
                apellido = getattr(medico, 'apellido', '')
                nombre_completo = f"{nombre} {apellido}".strip()
            medicos.append({
                'id': medico.id,
                'nombre': medico.nombre,
                'apellido': medico.apellido,
                'especialidad': medico.especialidad,
                'nombre_completo': nombre_completo,
            })
        return medicos

    def validate(self, data):
        """Validaciones a nivel de objeto"""
        # Validar que si hay fecha de completado, el estado sea COMPLETADA
        if data.get('fecha_completada') and data.get('estado') != 'COMPLETADA':
            raise serializers.ValidationError(
                "Solo las solicitudes completadas pueden tener fecha de completado"
            )
        
        # Validar que si el estado es COMPLETADA, haya fecha de completado
        if data.get('estado') == 'COMPLETADA' and not data.get('fecha_completada'):
            data['fecha_completada'] = timezone.now()
        
        return data

class SolicitudCreateSerializer(serializers.ModelSerializer):
    """Serializer específico para crear solicitudes"""
    
    class Meta:
        model = Solicitud
        fields = [
            'paciente',
            'medico_solicitante',
            'medicos_asignados',
            'tipo_solicitud',
            'descripcion',
            'observaciones',
            'fecha_limite',
            'prioridad',
            'lims_paneles',
            'lims_tipos_examen',
        ]

    def create(self, validated_data):
        """Crea la solicitud y asigna el usuario que la crea"""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['creado_por'] = request.user
            validated_data['modificado_por'] = request.user
        
        return super().create(validated_data)

class SolicitudUpdateSerializer(serializers.ModelSerializer):
    """Serializer específico para actualizar solicitudes"""
    
    class Meta:
        model = Solicitud
        fields = [
            'medico_solicitante',
            'medicos_asignados',
            'tipo_solicitud',
            'descripcion',
            'observaciones',
            'fecha_limite',
            'estado',
            'prioridad',
            'fecha_completada',
            'lims_paneles',
            'lims_tipos_examen',
        ]
        read_only_fields = ['fecha_completada']

    def update(self, instance, validated_data):
        """Actualiza la solicitud y asigna el usuario que la modifica"""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['modificado_por'] = request.user
        
        return super().update(instance, validated_data)

class SolicitudListSerializer(serializers.ModelSerializer):
    """Serializer para listar solicitudes (versión simplificada)"""
    
    paciente_nombre = serializers.CharField(source='paciente.nombre_completo', read_only=True)
    medico_solicitante_nombre = serializers.CharField(source='medico_solicitante.nombre_completo', read_only=True)
    dias_pendiente = serializers.ReadOnlyField()
    esta_vencida = serializers.ReadOnlyField()
    
    class Meta:
        model = Solicitud
        fields = [
            'id',
            'paciente',
            'paciente_nombre',
            'medico_solicitante',
            'medico_solicitante_nombre',
            'medicos_asignados',
            'tipo_solicitud',
            'estado',
            'prioridad',
            'fecha_solicitud',
            'fecha_limite',
            'dias_pendiente',
            'esta_vencida',
            'sincronizado_lims',
        ]

class SolicitudEstadoSerializer(serializers.ModelSerializer):
    """Serializer para cambiar solo el estado de una solicitud"""
    
    class Meta:
        model = Solicitud
        fields = ['estado']

    def validate_estado(self, value):
        """Valida el cambio de estado"""
        instance = self.instance
        if instance:
            # Validar transiciones de estado permitidas
            transiciones_permitidas = {
                'PENDIENTE': ['EN_PROCESO', 'COMPLETADA', 'CANCELADA'],
                'EN_PROCESO': ['COMPLETADA', 'CANCELADA'],
                'COMPLETADA': ['PENDIENTE'],  # Reabrir
                'CANCELADA': ['PENDIENTE'],   # Reabrir
                'ERROR': ['PENDIENTE', 'CANCELADA'],
            }
            
            estado_actual = instance.estado
            if estado_actual in transiciones_permitidas:
                if value not in transiciones_permitidas[estado_actual]:
                    raise serializers.ValidationError(
                        f"No se puede cambiar de '{estado_actual}' a '{value}'"
                    )
        
        return value

    def update(self, instance, validated_data):
        """Actualiza el estado y maneja lógica adicional"""
        nuevo_estado = validated_data['estado']
        
        # Si se marca como completada, establecer fecha de completado
        if nuevo_estado == 'COMPLETADA' and not instance.fecha_completada:
            validated_data['fecha_completada'] = timezone.now()
        
        # Si se reabre, limpiar fecha de completado
        if nuevo_estado == 'PENDIENTE' and instance.estado in ['COMPLETADA', 'CANCELADA']:
            validated_data['fecha_completada'] = None
        
        return super().update(instance, validated_data)

class SolicitudLimsSerializer(serializers.ModelSerializer):
    """Serializer para sincronización con LIMS"""
    
    class Meta:
        model = Solicitud
        fields = [
            'id',
            'lims_id',
            'sincronizado_lims',
            'ultima_sincronizacion',
        ]
        read_only_fields = ['id']

class SolicitudEstadisticasSerializer(serializers.Serializer):
    """Serializer para estadísticas de solicitudes"""
    
    total_solicitudes = serializers.IntegerField()
    solicitudes_pendientes = serializers.IntegerField()
    solicitudes_en_proceso = serializers.IntegerField()
    solicitudes_completadas = serializers.IntegerField()
    solicitudes_canceladas = serializers.IntegerField()
    solicitudes_vencidas = serializers.IntegerField()
    solicitudes_sincronizadas_lims = serializers.IntegerField()
    
    # Estadísticas por tipo
    por_tipo = serializers.DictField()
    
    # Estadísticas por prioridad
    por_prioridad = serializers.DictField()
    
    # Solicitudes recientes
    solicitudes_recientes = SolicitudListSerializer(many=True)
