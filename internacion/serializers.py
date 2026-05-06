from rest_framework import serializers
from .models import Sector, Cama, Internacion
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
    
    class Meta:
        model = Internacion
        fields = [
            'id',
            'paciente',
            'cama',
            'medico',
            'fecha_ingreso',
            'fecha_alta',
            'diagnostico_cie',
            'diagnostico_cie_id',
            'diagnostico_ingreso',
            'activo',
            'nombre_paciente',
            'paciente_nombre',
            'cama_nombre',
            'nombre_medico',
            'dias_internacion',
        ]
        read_only_fields = ['fecha_ingreso', 'dias_internacion', 'paciente_nombre', 'cama_nombre']
    
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
        
        # Validación 2: Paciente libre (solo para nuevas internaciones)
        paciente = data.get('paciente')
        if paciente and not self.instance:  # Solo validar en creación
            internacion_activa = Internacion.objects.filter(
                paciente=paciente,
                activo=True
            ).first()
            
            if internacion_activa:
                cama_actual = internacion_activa.cama
                raise serializers.ValidationError({
                    'paciente': f'El paciente ya está internado en la cama {cama_actual.nombre} (Sector: {cama_actual.sector.nombre}). '
                               f'Debe dar de alta al paciente antes de ingresarlo a otra cama.'
                })
        
        # Validación 3: Diagnóstico (al menos uno debe estar presente)
        diagnostico_cie = data.get('diagnostico_cie')
        diagnostico_ingreso = data.get('diagnostico_ingreso')
        
        if not diagnostico_cie and not diagnostico_ingreso:
            raise serializers.ValidationError({
                'diagnostico_cie': 'Debe proporcionar un diagnóstico CIE-10 o un diagnóstico de ingreso (texto libre).',
                'diagnostico_ingreso': 'Debe proporcionar un diagnóstico CIE-10 o un diagnóstico de ingreso (texto libre).'
            })
        
        return data


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
                ).select_related('paciente', 'medico').first()
                
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

