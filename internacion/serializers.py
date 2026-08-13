from rest_framework import serializers
from turnos.situacion_paciente import (
    SituacionPacienteConflictError,
    assert_puede_admitir_internacion,
    finalizar_atencion_por_derivacion,
)
from .models import Sector, Cama, Internacion, TipoDieta
from pacientes.models import Paciente
from medicos.models import Medico
from catalogos.models import DiagnosticoCIE10


class SectorSerializer(serializers.ModelSerializer):
    """Serializer para Sector con todos los campos"""
    class Meta:
        model = Sector
        fields = '__all__'


class DiagnosticoCIESerializer(serializers.ModelSerializer):
    """Serializer anidado para DiagnosticoCIE10"""
    class Meta:
        model = DiagnosticoCIE10
        fields = ['id', 'codigo', 'descripcion', 'categoria', 'capitulo', 'enfermedad']


class TipoDietaSerializer(serializers.ModelSerializer):
    """Catálogo de tipos terapéuticos de dieta."""

    class Meta:
        model = TipoDieta
        fields = ['id', 'nombre', 'descripcion', 'activo']


class InternacionSerializer(serializers.ModelSerializer):
    """Serializer para Internación con validaciones críticas de admisión"""
    nombre_paciente = serializers.SerializerMethodField()
    paciente_nombre = serializers.SerializerMethodField(
        help_text="Nombre del paciente (solo lectura)"
    )
    nombre_medico = serializers.SerializerMethodField()
    cama_nombre = serializers.CharField(
        source='cama.nombre',
        read_only=True,
        help_text="Nombre de la cama (solo lectura)"
    )
    dias_internacion = serializers.ReadOnlyField()
    diagnostico_cie = DiagnosticoCIESerializer(read_only=True)
    diagnostico_cie_id = serializers.PrimaryKeyRelatedField(
        queryset=DiagnosticoCIE10.objects.all(),
        source='diagnostico_cie',
        write_only=True,
        required=False,
        allow_null=True
    )
    tipo_dieta = TipoDietaSerializer(read_only=True)
    tipo_dieta_id = serializers.PrimaryKeyRelatedField(
        queryset=TipoDieta.objects.all(),
        source='tipo_dieta',
        write_only=True,
        required=False,
        allow_null=True,
    )
    
    class Meta:
        model = Internacion
        fields = [
            'id',
            'numero_internacion',
            'paciente',
            'cama',
            'medico',
            'atencion_origen',
            'motivo_ingreso',
            'fecha_ingreso',
            'fecha_alta',
            'diagnostico_cie',
            'diagnostico_cie_id',
            'diagnostico_ingreso',
            'tipo_dieta',
            'tipo_dieta_id',
            'activo',
            'nombre_paciente',
            'paciente_nombre',
            'cama_nombre',
            'nombre_medico',
            'dias_internacion',
        ]
        read_only_fields = [
            'fecha_ingreso',
            'dias_internacion',
            'paciente_nombre',
            'cama_nombre',
            'numero_internacion',
        ]
    
    def get_nombre_paciente(self, obj):
        """Retorna 'Apellido, Nombre' del paciente"""
        if obj.paciente:
            return f"{obj.paciente.apellido}, {obj.paciente.nombre}"
        return None
    
    def get_paciente_nombre(self, obj):
        """Retorna nombre completo del paciente (alias para compatibilidad)"""
        if obj.paciente:
            return f"{obj.paciente.apellido}, {obj.paciente.nombre}"
        return None
    
    def get_nombre_medico(self, obj):
        """Retorna nombre completo del médico"""
        if obj.medico:
            if obj.medico.apellido and obj.medico.nombre:
                return f"{obj.medico.apellido}, {obj.medico.nombre}"
            elif obj.medico.user:
                return f"{obj.medico.user.last_name}, {obj.medico.user.first_name}"
        return None
    
    def validate(self, data):
        """
        Validaciones críticas para el proceso de admisión:
        1. Cama disponible: Verifica que la cama esté en estado 'DISPONIBLE'
        2. Paciente libre: Verifica que el paciente NO tenga una internación activa
        3. Diagnóstico: Al menos diagnostico_cie o diagnostico_ingreso debe estar presente
        """
        # Validación 1: Cama disponible
        cama = data.get('cama')
        if cama:
            # Si es una creación (no tiene pk) o si se está cambiando la cama
            if not self.instance or (self.instance and self.instance.cama != cama):
                if cama.estado != 'DISPONIBLE':
                    raise serializers.ValidationError({
                        'cama': f'La cama {cama.nombre} no está disponible. Estado actual: {cama.estado}'
                    })
        
        # Validación 2: exclusividad de situación (solo para nuevas internaciones)
        paciente = data.get('paciente')
        if paciente and not self.instance:  # Solo validar en creación
            atencion_origen = data.get('atencion_origen')
            atencion_origen_id = (
                atencion_origen.pk if atencion_origen is not None else None
            )
            try:
                assert_puede_admitir_internacion(
                    paciente.pk,
                    atencion_origen_id=atencion_origen_id,
                )
            except SituacionPacienteConflictError as exc:
                raise serializers.ValidationError({'paciente': str(exc)}) from exc
        
        # Validación 3: Diagnóstico (al menos uno debe estar presente)
        diagnostico_cie = data.get('diagnostico_cie')
        diagnostico_ingreso = data.get('diagnostico_ingreso')
        if self.instance is not None:
            if 'diagnostico_cie' not in data:
                diagnostico_cie = self.instance.diagnostico_cie
            if 'diagnostico_ingreso' not in data:
                diagnostico_ingreso = self.instance.diagnostico_ingreso
        
        if not diagnostico_cie and not diagnostico_ingreso:
            raise serializers.ValidationError({
                'diagnostico_cie': 'Debe proporcionar un diagnóstico CIE-10 o un diagnóstico de ingreso (texto libre).',
                'diagnostico_ingreso': 'Debe proporcionar un diagnóstico CIE-10 o un diagnóstico de ingreso (texto libre).'
            })
        
        return data


    def create(self, validated_data):
        """Crea la internación y cierra la atención de origen si hubo derivación."""
        atencion_origen = validated_data.get('atencion_origen')
        internacion = super().create(validated_data)
        if atencion_origen is not None:
            finalizar_atencion_por_derivacion(atencion_origen)
        return internacion



class CamaSerializer(serializers.ModelSerializer):
    """Serializer para Cama con representación anidada del sector"""
    sector = SectorSerializer(read_only=True)
    sector_nombre = serializers.CharField(
        source='sector.nombre',
        read_only=True,
        help_text="Nombre del sector (solo lectura)"
    )
    sector_id = serializers.PrimaryKeyRelatedField(
        queryset=Sector.objects.all(),
        source='sector',
        write_only=True,
        help_text="ID del sector"
    )
    internacion_actual = serializers.SerializerMethodField()
    
    class Meta:
        model = Cama
        fields = '__all__'
        read_only_fields = ['internacion_actual', 'sector_nombre']
    
    def get_internacion_actual(self, obj):
        """Retorna la internación activa si la cama está ocupada"""
        if obj.estado == 'OCUPADA':
            try:
                internacion = Internacion.objects.filter(
                    cama=obj,
                    activo=True
                ).select_related('paciente', 'medico', 'diagnostico_cie', 'tipo_dieta').first()
                
                if internacion:
                    from datetime import datetime
                    from django.utils import timezone
                    
                    # Calcular días de internación
                    if internacion.fecha_alta:
                        dias = (internacion.fecha_alta - internacion.fecha_ingreso).days
                    else:
                        dias = (timezone.now() - internacion.fecha_ingreso).days
                    
                    diagnostico_display = None
                    if internacion.diagnostico_cie:
                        diagnostico_display = f"{internacion.diagnostico_cie.codigo} - {internacion.diagnostico_cie.descripcion}"
                    elif internacion.diagnostico_ingreso:
                        diagnostico_display = internacion.diagnostico_ingreso[:100] + '...' if len(internacion.diagnostico_ingreso) > 100 else internacion.diagnostico_ingreso
                    
                    return {
                        'id_internacion': internacion.id,
                        'nombre_paciente': f"{internacion.paciente.apellido}, {internacion.paciente.nombre}",
                        'nombre_medico': self._get_nombre_medico(internacion.medico) if internacion.medico else None,
                        'diagnostico': diagnostico_display,
                        'fecha_ingreso': internacion.fecha_ingreso,
                        'dias_internacion': dias,
                        'tipo_dieta': internacion.tipo_dieta.nombre if internacion.tipo_dieta else None,
                    }
            except Exception:
                pass
        
        return None
    
    def _get_nombre_medico(self, medico):
        """Helper para obtener nombre del médico"""
        if medico.apellido and medico.nombre:
            return f"{medico.apellido}, {medico.nombre}"
        elif medico.user:
            return f"{medico.user.last_name}, {medico.user.first_name}"
        return None

