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
# DETALLE DE CONSULTA (eje documental)
# ============================================================================

class ArchivoConsultaResumenSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    titulo = serializers.CharField()
    tipo_archivo = serializers.CharField()
    descripcion = serializers.CharField(allow_null=True)
    fecha_subida = serializers.DateTimeField()
    archivo_nombre = serializers.CharField(allow_null=True)
    download_url = serializers.CharField(allow_null=True)


class EstudioConsultaResumenSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    modalidad = serializers.CharField()
    estado = serializers.CharField()
    tipo_estudio_nombre = serializers.CharField(allow_null=True)
    fecha_solicitud = serializers.DateTimeField(allow_null=True)
    descripcion_clinica = serializers.CharField(allow_blank=True)


class ResultadoLaboratorioResumenSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    tipo_examen_nombre = serializers.CharField(allow_null=True)
    valor_obtenido = serializers.CharField(allow_null=True, allow_blank=True)
    unidad = serializers.CharField(allow_null=True, allow_blank=True)
    estado = serializers.CharField(allow_null=True)
    es_patologico = serializers.BooleanField(allow_null=True)


class SolicitudLaboratorioResumenSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    numero = serializers.CharField(allow_null=True)
    estado = serializers.CharField()
    fecha_solicitud = serializers.DateTimeField()
    tipos_examen_nombres = serializers.ListField(child=serializers.CharField())
    paneles_nombres = serializers.ListField(child=serializers.CharField())
    resultados = ResultadoLaboratorioResumenSerializer(many=True)


class ConsultaDetalleSerializer(ConsultaSerializer):
    """Consulta con archivos, pedidos de laboratorio y estudios complementarios vinculados."""

    paciente_id = serializers.IntegerField(source='historia_clinica_id', read_only=True)
    archivos = serializers.SerializerMethodField()
    estudios_complementarios = serializers.SerializerMethodField()
    solicitudes_laboratorio = serializers.SerializerMethodField()

    class Meta(ConsultaSerializer.Meta):
        fields = ConsultaSerializer.Meta.fields + [
            'paciente_id',
            'archivos',
            'estudios_complementarios',
            'solicitudes_laboratorio',
        ]

    def get_archivos(self, obj):
        from archivos_medicos.models import ArchivoMedico
        request = self.context.get('request')
        items = ArchivoMedico.objects.filter(consulta_id=obj.pk).order_by('-fecha_subida')
        result = []
        for ar in items:
            nombre = None
            if ar.archivo:
                import os
                nombre = os.path.basename(ar.archivo.name)
            download_url = None
            if request and ar.pk:
                download_url = request.build_absolute_uri(
                    f'/api/archivos-medicos/archivos/{ar.pk}/download/'
                )
            result.append({
                'id': ar.id,
                'titulo': ar.titulo,
                'tipo_archivo': ar.tipo_archivo,
                'descripcion': ar.descripcion,
                'fecha_subida': ar.fecha_subida,
                'archivo_nombre': nombre,
                'download_url': download_url,
            })
        return ArchivoConsultaResumenSerializer(result, many=True).data

    def get_estudios_complementarios(self, obj):
        from estudios.models import EstudioComplementario
        estudios = (
            EstudioComplementario.objects.filter(consulta_hc_id=obj.pk)
            .select_related('tipo_estudio')
            .order_by('-fecha_solicitud', '-created_at')
        )
        data = []
        for est in estudios:
            data.append({
                'id': est.id,
                'modalidad': est.modalidad,
                'estado': est.estado,
                'tipo_estudio_nombre': est.tipo_estudio.nombre if est.tipo_estudio else None,
                'fecha_solicitud': est.fecha_solicitud,
                'descripcion_clinica': est.descripcion_clinica or '',
            })
        return EstudioConsultaResumenSerializer(data, many=True).data

    def get_solicitudes_laboratorio(self, obj):
        from laboratorio.models import SolicitudExamen
        solicitudes = (
            SolicitudExamen.objects.filter(consulta_hc_id=obj.pk)
            .prefetch_related('tipos_examen', 'paneles', 'resultados__tipo_examen')
            .order_by('-fecha_solicitud')
        )
        data = []
        for sol in solicitudes:
            resultados = []
            for res in sol.resultados.all():
                valor = (res.valor_obtenido or '').strip()
                resultados.append({
                    'id': res.id,
                    'tipo_examen_nombre': res.tipo_examen.nombre if res.tipo_examen else None,
                    'valor_obtenido': res.valor_obtenido,
                    'unidad': (res.unidad or getattr(res.tipo_examen, 'unidad', None) or '') if res.tipo_examen else res.unidad,
                    'estado': 'CARGADO' if valor else 'PENDIENTE',
                    'es_patologico': res.es_patologico,
                })
            data.append({
                'id': sol.id,
                'numero': sol.numero,
                'estado': sol.estado,
                'fecha_solicitud': sol.fecha_solicitud,
                'tipos_examen_nombres': [te.nombre for te in sol.tipos_examen.all()],
                'paneles_nombres': [p.nombre for p in sol.paneles.all()],
                'resultados': resultados,
            })
        return SolicitudLaboratorioResumenSerializer(data, many=True).data


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
