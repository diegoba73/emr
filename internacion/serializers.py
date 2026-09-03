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
from internacion.serializers_hc import MedicacionHabitualInternacionSerializer


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
    tiene_alergias = serializers.BooleanField(required=False, allow_null=True)
    paciente_cabecera = serializers.SerializerMethodField()
    medicaciones_habituales = MedicacionHabitualInternacionSerializer(many=True, read_only=True)
    estado_civil = serializers.CharField(write_only=True, required=False, allow_blank=True)
    familiar_nombre = serializers.CharField(write_only=True, required=False, allow_blank=True)
    familiar_telefono = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
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
            'alergias',
            'tiene_alergias',
            'anamnesis_ingreso',
            'examen_fisico_ingreso',
            'medicacion_habitual',
            'plan_estudio_tratamiento',
            'paciente_cabecera',
            'medicaciones_habituales',
            'estado_civil',
            'familiar_nombre',
            'familiar_telefono',
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

    def get_paciente_cabecera(self, obj):
        paciente = obj.paciente
        cama = obj.cama
        sector = cama.sector.nombre if cama and cama.sector_id else None
        return {
            'paciente_id': paciente.pk if paciente else None,
            'nombre': getattr(paciente, 'nombre', '') or '',
            'apellido': getattr(paciente, 'apellido', '') or '',
            'dni': getattr(paciente, 'dni', '') or '',
            'edad': getattr(paciente, 'edad', None),
            'estado_civil': getattr(paciente, 'estado_civil', '') or '',
            'obra_social': getattr(paciente, 'obra_social', None),
            'numero_afiliado': getattr(paciente, 'numero_afiliado', None),
            'direccion': getattr(paciente, 'direccion', None),
            'telefono': getattr(paciente, 'telefono', None),
            'familiar_nombre': getattr(paciente, 'familiar_nombre', '') or '',
            'familiar_telefono': getattr(paciente, 'familiar_telefono', '') or '',
            'numero_internacion': obj.numero_internacion,
            'cama': cama.nombre if cama else None,
            'sector': sector,
            'fecha_ingreso': obj.fecha_ingreso.isoformat() if obj.fecha_ingreso else None,
            'fecha_alta': obj.fecha_alta.isoformat() if obj.fecha_alta else None,
        }
    
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

        if self.instance is not None:
            hc_keys = (
                'alergias',
                'tiene_alergias',
                'anamnesis_ingreso',
                'examen_fisico_ingreso',
                'medicacion_habitual',
                'plan_estudio_tratamiento',
                'motivo_ingreso',
                'estado_civil',
                'familiar_nombre',
                'familiar_telefono',
            )
            if any(key in data for key in hc_keys):
                from api.permissions import get_normalized_role
                request = self.context.get('request')
                user = getattr(request, 'user', None)
                rol = get_normalized_role(user) if user else ''
                allowed = bool(user and (user.is_superuser or rol in ('admin', 'medico')))
                if not allowed:
                    raise serializers.ValidationError(
                        'Solo el médico puede cargar o editar anamnesis, examen físico, alergias y medicación habitual.'
                    )

        return data

    def update(self, instance, validated_data):
        estado_civil = validated_data.pop('estado_civil', None)
        familiar_nombre = validated_data.pop('familiar_nombre', None)
        familiar_telefono = validated_data.pop('familiar_telefono', None)
        internacion = super().update(instance, validated_data)
        paciente = internacion.paciente
        if paciente is None:
            return internacion
        changed = []
        if estado_civil is not None:
            paciente.estado_civil = estado_civil
            changed.append('estado_civil')
        if familiar_nombre is not None:
            paciente.familiar_nombre = familiar_nombre
            changed.append('familiar_nombre')
        if familiar_telefono is not None:
            paciente.familiar_telefono = familiar_telefono
            changed.append('familiar_telefono')
        if changed:
            paciente.save(update_fields=changed)
        return internacion


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

