"""
Serializers para la app historias_clinicas.
Maneja escrituras anidadas (Nested Writes) para una buena UX.
"""
import logging
from rest_framework import serializers
from django.db import transaction
from .models import (
    HistoriaClinica,
    Consulta,
    Diagnostico,
    Tratamiento,
    Prescripcion,
    Sintoma,
)
from catalogos.models import DiagnosticoCIE10, Medicamento

logger = logging.getLogger(__name__)


# ============================================================================
# SERIALIZERS SIMPLES
# ============================================================================

class DiagnosticoSerializer(serializers.ModelSerializer):
    """Serializer simple para Diagnostico."""
    diagnostico_cie_codigo = serializers.CharField(
        source='diagnostico_cie.codigo',
        read_only=True
    )
    diagnostico_cie_descripcion = serializers.CharField(
        source='diagnostico_cie.descripcion',
        read_only=True
    )
    diagnostico_cie_id = serializers.PrimaryKeyRelatedField(
        queryset=DiagnosticoCIE10.objects.all(),
        source='diagnostico_cie',
        write_only=True,
        required=False,
        allow_null=True
    )
    sintomas_nombres = serializers.SerializerMethodField()
    sintomas_ids = serializers.PrimaryKeyRelatedField(
        queryset=Sintoma.objects.all(),
        many=True,
        write_only=True,
        required=False,
        source='sintomas_asociados'
    )

    class Meta:
        model = Diagnostico
        fields = [
            'id',
            'diagnostico_cie_id',
            'diagnostico_cie_codigo',
            'diagnostico_cie_descripcion',
            'nombre_diagnostico',
            'descripcion_diagnostico',
            'sintomas_ids',
            'sintomas_nombres',
            'fecha_diagnostico',
        ]
        read_only_fields = ['id', 'fecha_diagnostico', 'diagnostico_cie_codigo', 'diagnostico_cie_descripcion', 'sintomas_nombres']

    def get_sintomas_nombres(self, obj):
        """Retorna los nombres de los síntomas asociados."""
        return [s.nombre for s in obj.sintomas_asociados.all()]


class TratamientoSerializer(serializers.ModelSerializer):
    """Serializer simple para Tratamiento."""
    
    class Meta:
        model = Tratamiento
        fields = [
            'id',
            'tipo_tratamiento',
            'descripcion_tratamiento',
            'dosis_frecuencia',
            'fecha_inicio',
            'fecha_fin_estimada',
            'instrucciones_adicionales',
            'fecha_registro',
        ]
        read_only_fields = ['id', 'fecha_registro']


class PrescripcionSerializer(serializers.ModelSerializer):
    """Serializer simple para Prescripcion."""
    medicamento_nombre = serializers.CharField(
        source='medicamento.nombre',
        read_only=True
    )
    medicamento_id = serializers.PrimaryKeyRelatedField(
        queryset=Medicamento.objects.all(),
        source='medicamento',
        write_only=True
    )

    class Meta:
        model = Prescripcion
        fields = [
            'id',
            'medicamento_id',
            'medicamento_nombre',
            'dosis',
            'frecuencia',
            'duracion',
            'instrucciones',
            'activa',
            'fecha_inicio',
            'fecha_fin',
            'observaciones',
            'fecha_prescripcion',
        ]
        read_only_fields = ['id', 'fecha_prescripcion', 'medicamento_nombre']


# ============================================================================
# SERIALIZERS DE CONSULTA
# ============================================================================

class ConsultaSerializer(serializers.ModelSerializer):
    """
    Serializer de lectura para Consulta.
    Incluye los nested serializers (many=True).
    """
    paciente_nombre = serializers.CharField(
        source='historia_clinica.paciente.nombre_completo',
        read_only=True
    )
    medico_nombre = serializers.CharField(
        source='medico.nombre_completo',
        read_only=True
    )
    diagnosticos = DiagnosticoSerializer(many=True, read_only=True)
    tratamientos = TratamientoSerializer(many=True, read_only=True)
    prescripciones = PrescripcionSerializer(many=True, read_only=True)

    class Meta:
        model = Consulta
        fields = [
            'id',
            'historia_clinica',
            'paciente_nombre',
            'medico',
            'medico_nombre',
            'turno',
            'fecha_hora_consulta',
            'motivo_consulta_detalle',
            'anamnesis',
            'examen_fisico',
            'diagnostico_presuntivo',
            'plan_manejo',
            'notas_medicas',
            'fecha_registro',
            'ultima_actualizacion',
            'diagnosticos',
            'tratamientos',
            'prescripciones',
        ]
        read_only_fields = ['id', 'fecha_registro', 'ultima_actualizacion']


class ConsultaCreateSerializer(serializers.ModelSerializer):
    """
    Serializer de escritura para Consulta.
    Acepta datos de consulta + listas de diagnosticos, tratamientos, prescripciones.
    Método create() atómico con transaction.atomic().
    """
    # Campos anidados para escritura
    diagnosticos = DiagnosticoSerializer(many=True, required=False)
    tratamientos = TratamientoSerializer(many=True, required=False)
    prescripciones = PrescripcionSerializer(many=True, required=False)
    
    # Campos de lectura
    paciente_nombre = serializers.CharField(
        source='historia_clinica.paciente.nombre_completo',
        read_only=True
    )
    medico_nombre = serializers.CharField(
        source='medico.nombre_completo',
        read_only=True
    )

    class Meta:
        model = Consulta
        fields = [
            'id',
            'historia_clinica',
            'paciente_nombre',
            'medico',
            'medico_nombre',
            'turno',
            'fecha_hora_consulta',
            'motivo_consulta_detalle',
            'anamnesis',
            'examen_fisico',
            'diagnostico_presuntivo',
            'plan_manejo',
            'notas_medicas',
            'diagnosticos',
            'tratamientos',
            'prescripciones',
            'fecha_registro',
            'ultima_actualizacion',
        ]
        read_only_fields = ['id', 'fecha_registro', 'ultima_actualizacion', 'paciente_nombre', 'medico_nombre']

    @transaction.atomic
    def create(self, validated_data):
        """
        Método create() atómico:
        - Crea la Consulta
        - Itera y crea los objetos relacionados vinculándolos a la consulta creada
        - Asigna el médico del request user si no viene explícito
        """
        # Extraer datos anidados
        diagnosticos_data = validated_data.pop('diagnosticos', [])
        tratamientos_data = validated_data.pop('tratamientos', [])
        prescripciones_data = validated_data.pop('prescripciones', [])
        
        # Asignar médico del request user si no viene explícito
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            user = request.user
            if not validated_data.get('medico') and hasattr(user, 'medico') and user.medico:
                validated_data['medico'] = user.medico
        
        # Crear la Consulta
        consulta = Consulta.objects.create(**validated_data)
        
        # Crear diagnósticos
        for diagnostico_data in diagnosticos_data:
            sintomas_ids = diagnostico_data.pop('sintomas_asociados', [])
            diagnostico = Diagnostico.objects.create(consulta=consulta, **diagnostico_data)
            if sintomas_ids:
                diagnostico.sintomas_asociados.set(sintomas_ids)
        
        # Crear tratamientos
        for tratamiento_data in tratamientos_data:
            Tratamiento.objects.create(consulta=consulta, **tratamiento_data)
        
        # Crear prescripciones
        prescripciones_count = 0
        for prescripcion_data in prescripciones_data:
            Prescripcion.objects.create(consulta=consulta, **prescripcion_data)
            prescripciones_count += 1
        
        # Logging para observabilidad
        logger.info(
            f"Consulta creada ID {consulta.id} con "
            f"{len(diagnosticos_data)} diagnósticos, "
            f"{len(tratamientos_data)} tratamientos y "
            f"{prescripciones_count} prescripciones"
        )
        
        return consulta


# ============================================================================
# SERIALIZER DE HISTORIA CLINICA
# ============================================================================

class HistoriaClinicaSerializer(serializers.ModelSerializer):
    """Serializer para HistoriaClinica."""
    paciente_nombre = serializers.CharField(
        source='paciente.nombre_completo',
        read_only=True
    )
    consultas_count = serializers.SerializerMethodField()

    class Meta:
        model = HistoriaClinica
        fields = [
            'paciente',
            'paciente_nombre',
            'fecha_creacion',
            'ultima_actualizacion',
            'consultas_count',
        ]
        read_only_fields = ['fecha_creacion', 'ultima_actualizacion', 'paciente_nombre', 'consultas_count']

    def get_consultas_count(self, obj):
        """Retorna el número de consultas."""
        return obj.consultas.count()
