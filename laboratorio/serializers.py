"""
Serializers para la app laboratorio (LIMS).
"""
import logging
from rest_framework import serializers
from django.db import transaction
from .models import (
    TipoMuestra,
    TipoExamen,
    PanelExamen,
    SolicitudExamen,
    ResultadoExamen,
)
from pacientes.models import Paciente
from medicos.models import Medico

logger = logging.getLogger(__name__)


# ============================================================================
# SERIALIZERS DE INFRAESTRUCTURA
# ============================================================================

class TipoMuestraSerializer(serializers.ModelSerializer):
    """Serializer para TipoMuestra."""
    
    class Meta:
        model = TipoMuestra
        fields = [
            'id',
            'codigo',
            'nombre',
            'color_tubo',
            'activo',
        ]
        read_only_fields = ['id']


class TipoExamenSerializer(serializers.ModelSerializer):
    """Serializer para TipoExamen."""
    tipo_muestra_nombre = serializers.CharField(
        source='tipo_muestra_requerida.nombre',
        read_only=True
    )
    tipo_muestra_codigo = serializers.CharField(
        source='tipo_muestra_requerida.codigo',
        read_only=True
    )
    tipo_muestra_requerida = serializers.PrimaryKeyRelatedField(
        queryset=TipoMuestra.objects.all(),
        help_text="ID del tipo de muestra requerida"
    )
    
    class Meta:
        model = TipoExamen
        fields = [
            'id',
            'codigo',
            'nombre',
            'abreviatura',
            'tipo_muestra_requerida',
            'tipo_muestra_nombre',
            'tipo_muestra_codigo',
            'precio',
            'rango_referencia_texto',
            'activo',
        ]
        read_only_fields = ['id', 'tipo_muestra_nombre', 'tipo_muestra_codigo']


class PanelExamenSerializer(serializers.ModelSerializer):
    """Serializer para PanelExamen."""
    tipos_examen_nombres = serializers.SerializerMethodField()
    tipos_examen_ids = serializers.PrimaryKeyRelatedField(
        queryset=TipoExamen.objects.all(),
        many=True,
        write_only=True,
        required=False,
        source='tipos_examen'
    )
    
    class Meta:
        model = PanelExamen
        fields = [
            'id',
            'codigo',
            'nombre',
            'tipos_examen',
            'tipos_examen_ids',
            'tipos_examen_nombres',
            'activo',
        ]
        read_only_fields = ['id', 'tipos_examen_nombres']
    
    def get_tipos_examen_nombres(self, obj):
        """Retorna los nombres de los tipos de examen del panel."""
        return [te.nombre for te in obj.tipos_examen.all()]


# ============================================================================
# SERIALIZERS DE RESULTADOS
# ============================================================================

class ResultadoExamenSerializer(serializers.ModelSerializer):
    """
    Serializer para ResultadoExamen.
    Lectura: Incluye datos del tipo_examen (nested).
    Escritura: Campos valor_obtenido, es_patologico, observaciones.
    """
    tipo_examen_nombre = serializers.CharField(
        source='tipo_examen.nombre',
        read_only=True
    )
    tipo_examen_codigo = serializers.CharField(
        source='tipo_examen.codigo',
        read_only=True
    )
    tipo_examen_rango_referencia = serializers.CharField(
        source='tipo_examen.rango_referencia_texto',
        read_only=True
    )
    validado_por_nombre = serializers.CharField(
        source='validado_por.username',
        read_only=True
    )
    muestra_id = serializers.IntegerField(read_only=True, allow_null=True)
    
    class Meta:
        model = ResultadoExamen
        fields = [
            'id',
            'solicitud',
            'tipo_examen',
            'tipo_examen_nombre',
            'tipo_examen_codigo',
            'tipo_examen_rango_referencia',
            'valor_obtenido',
            'es_patologico',
            'validado_por',
            'validado_por_nombre',
            'fecha_validacion',
            'observaciones',
            'muestra_id',
        ]
        read_only_fields = [
            'id',
            'solicitud',
            'tipo_examen',
            'tipo_examen_nombre',
            'tipo_examen_codigo',
            'tipo_examen_rango_referencia',
            'validado_por_nombre',
            'fecha_validacion',
            'muestra_id',
        ]


# ============================================================================
# SERIALIZERS DE SOLICITUDES
# ============================================================================

class SolicitudExamenSerializer(serializers.ModelSerializer):
    """
    Serializer de lectura para SolicitudExamen.
    Incluye paciente (nombre, dni), medico (lógica híbrida), y resultados (nested many=True).
    """
    paciente_nombre = serializers.CharField(
        source='paciente.nombre_completo',
        read_only=True
    )
    paciente_dni = serializers.CharField(
        source='paciente.dni',
        read_only=True
    )
    medico_display = serializers.CharField(read_only=True)
    medico_interno_nombre = serializers.CharField(
        source='medico_interno.nombre_completo',
        read_only=True
    )
    resultados = ResultadoExamenSerializer(many=True, read_only=True)
    tipos_examen_nombres = serializers.SerializerMethodField()
    paneles_nombres = serializers.SerializerMethodField()
    
    class Meta:
        model = SolicitudExamen
        fields = [
            'id',
            'numero',
            'paciente',
            'paciente_nombre',
            'paciente_dni',
            'medico_interno',
            'medico_interno_nombre',
            'medico_externo_nombre',
            'medico_display',
            'origen_solicitud',
            'tipos_examen',
            'tipos_examen_nombres',
            'paneles',
            'paneles_nombres',
            'estado',
            'fecha_solicitud',
            'fecha_entrega_prometida',
            'observaciones',
            'resultados',
        ]
        read_only_fields = [
            'id',
            'numero',
            'fecha_solicitud',
            'estado',
            'paciente_nombre',
            'paciente_dni',
            'medico_display',
            'medico_interno_nombre',
            'tipos_examen_nombres',
            'paneles_nombres',
        ]
    
    def get_tipos_examen_nombres(self, obj):
        """Retorna los nombres de los tipos de examen."""
        return [te.nombre for te in obj.tipos_examen.all()]
    
    def get_paneles_nombres(self, obj):
        """Retorna los nombres de los paneles."""
        return [p.nombre for p in obj.paneles.all()]


class SolicitudExamenCreateSerializer(serializers.ModelSerializer):
    """
    Serializer de escritura para SolicitudExamen.
    Campos: paciente_id, medico_id (opcional), medico_externo_nombre (opcional),
    origen_solicitud, examenes_ids (ListField de ints), paneles_ids (ListField de ints).
    Método create: Crea la Solicitud y los ResultadoExamen asociados en estado PENDIENTE.
    """
    paciente_id = serializers.PrimaryKeyRelatedField(
        queryset=Paciente.objects.all(),
        source='paciente',
        write_only=True,
        help_text="ID del paciente"
    )
    medico_id = serializers.PrimaryKeyRelatedField(
        queryset=Medico.objects.all(),
        source='medico_interno',
        write_only=True,
        required=False,
        allow_null=True,
        help_text="ID del médico interno (opcional)"
    )
    examenes_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        allow_empty=True
    )
    paneles_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        allow_empty=True
    )
    
    class Meta:
        model = SolicitudExamen
        fields = [
            'id',
            'paciente_id',
            'medico_id',
            'medico_externo_nombre',
            'origen_solicitud',
            'examenes_ids',
            'paneles_ids',
            'fecha_entrega_prometida',
            'observaciones',
        ]
        read_only_fields = ['id']
    
    @transaction.atomic
    def create(self, validated_data):
        """
        Método create atómico:
        - Crea la Solicitud
        - Itera examenes_ids y crea los ResultadoExamen asociados en estado PENDIENTE
        - Itera paneles_ids, busca sus exámenes componentes y crea los ResultadoExamen
          correspondientes (evitando duplicados)
        """
        # Extraer datos anidados
        examenes_ids = validated_data.pop('examenes_ids', [])
        paneles_ids = validated_data.pop('paneles_ids', [])
        
        # Crear la Solicitud
        solicitud = SolicitudExamen.objects.create(**validated_data)
        
        # Asociar tipos_examen y paneles
        if examenes_ids:
            solicitud.tipos_examen.set(examenes_ids)
        
        if paneles_ids:
            solicitud.paneles.set(paneles_ids)
        
        # Crear ResultadoExamen para cada tipo_examen directo
        tipos_examen_creados = set()
        for tipo_examen_id in examenes_ids:
            try:
                tipo_examen = TipoExamen.objects.get(id=tipo_examen_id)
                ResultadoExamen.objects.create(
                    solicitud=solicitud,
                    tipo_examen=tipo_examen,
                    valor_obtenido='',  # Vacío inicialmente
                    es_patologico=False
                )
                tipos_examen_creados.add(tipo_examen_id)
            except TipoExamen.DoesNotExist:
                logger.warning(f"TipoExamen con ID {tipo_examen_id} no existe")
        
        # Crear ResultadoExamen para exámenes de paneles (evitando duplicados)
        for panel_id in paneles_ids:
            try:
                panel = PanelExamen.objects.get(id=panel_id)
                tipos_examen_panel = panel.tipos_examen.all()
                
                for tipo_examen in tipos_examen_panel:
                    # Evitar duplicados: si ya se creó un resultado para este tipo_examen, no crear otro
                    if tipo_examen.id not in tipos_examen_creados:
                        ResultadoExamen.objects.create(
                            solicitud=solicitud,
                            tipo_examen=tipo_examen,
                            valor_obtenido='',  # Vacío inicialmente
                            es_patologico=False
                        )
                        tipos_examen_creados.add(tipo_examen.id)
            except PanelExamen.DoesNotExist:
                logger.warning(f"PanelExamen con ID {panel_id} no existe")
        
        return solicitud



