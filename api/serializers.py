from rest_framework import serializers
from pacientes.models import Paciente
from medicos.models import Medico, Especialidad
from laboratorio.models import TipoExamen, PanelExamen, SolicitudExamen, ResultadoExamen
from historias_clinicas.models import HistoriaClinica, Consulta, Diagnostico, Prescripcion, Internacion
from catalogos.models import DiagnosticoCIE10, Medicamento
from turnos.models import Turno


class PacienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paciente
        fields = '__all__'


class EspecialidadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Especialidad
        fields = '__all__'


class MedicoSerializer(serializers.ModelSerializer):
    especialidad = EspecialidadSerializer(read_only=True)
    nombre = serializers.ReadOnlyField()
    apellido = serializers.ReadOnlyField()
    email = serializers.ReadOnlyField()
    telefono = serializers.ReadOnlyField()
    
    class Meta:
        model = Medico
        fields = '__all__'


class TipoExamenSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoExamen
        fields = '__all__'


class PanelExamenSerializer(serializers.ModelSerializer):
    examenes = TipoExamenSerializer(many=True, read_only=True)
    
    class Meta:
        model = PanelExamen
        fields = '__all__'


class HistoriaClinicaSerializer(serializers.ModelSerializer):
    paciente = PacienteSerializer(read_only=True)
    
    class Meta:
        model = HistoriaClinica
        fields = '__all__'


class ConsultaSerializer(serializers.ModelSerializer):
    historia_clinica = HistoriaClinicaSerializer(read_only=True)
    medico = MedicoSerializer(read_only=True)
    
    class Meta:
        model = Consulta
        fields = '__all__'





class DiagnosticoSerializer(serializers.ModelSerializer):
    diagnostico_cie = serializers.PrimaryKeyRelatedField(
        queryset=DiagnosticoCIE10.objects.all(),
        required=False,
        allow_null=True
    )
    
    class Meta:
        model = Diagnostico
        fields = '__all__'


class MedicamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medicamento
        fields = '__all__'


class PrescripcionSerializer(serializers.ModelSerializer):
    medicamento = MedicamentoSerializer(read_only=True)
    
    class Meta:
        model = Prescripcion
        fields = '__all__'


class SolicitudExamenSerializer(serializers.ModelSerializer):
    paciente = PacienteSerializer(read_only=True)
    medico = MedicoSerializer(read_only=True)
    consulta = ConsultaSerializer(read_only=True)
    examenes_individuales = TipoExamenSerializer(many=True, read_only=True)
    paneles = PanelExamenSerializer(many=True, read_only=True)
    
    class Meta:
        model = SolicitudExamen
        fields = '__all__'


class ResultadoExamenSerializer(serializers.ModelSerializer):
    solicitud = SolicitudExamenSerializer(read_only=True)
    tipo_examen = TipoExamenSerializer(read_only=True)
    validado_por = MedicoSerializer(read_only=True)
    
    class Meta:
        model = ResultadoExamen
        fields = '__all__'


# Serializers para Turnos
class TurnoSerializer(serializers.ModelSerializer):
    paciente = PacienteSerializer(read_only=True)
    medico = MedicoSerializer(read_only=True)
    especialidad = EspecialidadSerializer(read_only=True)
    centro_fisico = serializers.SerializerMethodField()
    tipo_atencion = serializers.SerializerMethodField()
    
    class Meta:
        model = Turno
        fields = '__all__'
    
    def get_centro_fisico(self, obj):
        if obj.centro_fisico:
            return {
                'id': obj.centro_fisico.id,
                'codigo': obj.centro_fisico.codigo,
                'nombre': obj.centro_fisico.nombre
            }
        return None
    
    def get_tipo_atencion(self, obj):
        if obj.tipo_atencion:
            return {
                'id': obj.tipo_atencion.id,
                'codigo': obj.tipo_atencion.codigo,
                'nombre': obj.tipo_atencion.nombre
            }
        return None


class ConsultaCreateSerializer(serializers.ModelSerializer):
    # Campos para escritura (IDs)
    historia_clinica_id = serializers.IntegerField(write_only=True)
    medico_id = serializers.IntegerField(write_only=True)
    turno_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    
    # Campos para lectura (objetos completos)
    historia_clinica = HistoriaClinicaSerializer(read_only=True)
    medico = MedicoSerializer(read_only=True)
    turno = TurnoSerializer(read_only=True)
    
    class Meta:
        model = Consulta
        fields = '__all__'
        extra_kwargs = {
            # Estos campos se proveen vía *_id en create(), por eso no se exigen como input directo
            'historia_clinica': {'required': False, 'read_only': True},
            'medico': {'required': False, 'read_only': True},
            'turno': {'required': False, 'allow_null': True, 'read_only': True},
            'fecha_hora_consulta': {'required': True},
            'motivo_consulta_detalle': {'required': True},
            'anamnesis': {'required': False, 'allow_blank': True},
            'examen_fisico': {'required': False, 'allow_blank': True},
            'diagnostico_presuntivo': {'required': False, 'allow_blank': True},
            'plan_manejo': {'required': False, 'allow_blank': True},
            'notas_medicas': {'required': False, 'allow_blank': True},
        }

    def create(self, validated_data):
        # Mapear IDs write_only a campos reales del modelo
        historia_clinica_id = validated_data.pop('historia_clinica_id')
        medico_id = validated_data.pop('medico_id')
        turno_id = validated_data.pop('turno_id', None)
        validated_data['historia_clinica_id'] = historia_clinica_id
        validated_data['medico_id'] = medico_id
        if turno_id is not None:
            validated_data['turno_id'] = turno_id
        return super().create(validated_data)


class TurnoCreateUpdateSerializer(serializers.ModelSerializer):
    # Campos para escritura (IDs)
    paciente_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    medico_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    especialidad_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    centro_fisico_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    tipo_atencion_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    
    # Campos para lectura (objetos completos)
    paciente = PacienteSerializer(read_only=True)
    medico = MedicoSerializer(read_only=True)
    especialidad = EspecialidadSerializer(read_only=True)
    centro_fisico = serializers.SerializerMethodField()
    tipo_atencion = serializers.SerializerMethodField()
    
    class Meta:
        model = Turno
        fields = '__all__'
        extra_kwargs = {
            'paciente': {'required': False, 'allow_null': True},
            'medico': {'required': False, 'allow_null': True},
            'especialidad': {'required': False, 'allow_null': True},
            'fecha_hora': {'required': False, 'allow_null': True},
            'fecha_hora_inicio': {'required': True},  # Cambiado a requerido
            'fecha_hora_fin': {'required': False, 'allow_null': True},
            'motivo_consulta': {'required': False, 'allow_null': True},
            'estado': {'required': False},
            'notas_administrativas': {'required': False, 'allow_null': True},
        }
    
    def create(self, validated_data):
        # Extraer los IDs de los campos write_only
        paciente_id = validated_data.pop('paciente_id', None)
        medico_id = validated_data.pop('medico_id', None)
        especialidad_id = validated_data.pop('especialidad_id', None)
        centro_fisico_id = validated_data.pop('centro_fisico_id', None)
        tipo_atencion_id = validated_data.pop('tipo_atencion_id', None)
        
        # Asignar los IDs a los campos del modelo
        if paciente_id:
            validated_data['paciente_id'] = paciente_id
        if medico_id:
            validated_data['medico_id'] = medico_id
        if especialidad_id:
            validated_data['especialidad_id'] = especialidad_id
        if centro_fisico_id:
            validated_data['centro_fisico_id'] = centro_fisico_id
        if tipo_atencion_id:
            validated_data['tipo_atencion_id'] = tipo_atencion_id
        
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        # Extraer los IDs de los campos write_only
        paciente_id = validated_data.pop('paciente_id', None)
        medico_id = validated_data.pop('medico_id', None)
        especialidad_id = validated_data.pop('especialidad_id', None)
        centro_fisico_id = validated_data.pop('centro_fisico_id', None)
        tipo_atencion_id = validated_data.pop('tipo_atencion_id', None)
        
        # Asignar los IDs a los campos del modelo
        if paciente_id is not None:
            validated_data['paciente_id'] = paciente_id
        if medico_id is not None:
            validated_data['medico_id'] = medico_id
        if especialidad_id is not None:
            validated_data['especialidad_id'] = especialidad_id
        if centro_fisico_id is not None:
            validated_data['centro_fisico_id'] = centro_fisico_id
        if tipo_atencion_id is not None:
            validated_data['tipo_atencion_id'] = tipo_atencion_id
        
        return super().update(instance, validated_data)
    
    def get_centro_fisico(self, obj):
        if obj.centro_fisico:
            return {
                'id': obj.centro_fisico.id,
                'codigo': obj.centro_fisico.codigo,
                'nombre': obj.centro_fisico.nombre
            }
        return None
    
    def get_tipo_atencion(self, obj):
        if obj.tipo_atencion:
            return {
                'id': obj.tipo_atencion.id,
                'codigo': obj.tipo_atencion.codigo,
                'nombre': obj.tipo_atencion.nombre
            }
        return None


# Serializers para estadísticas del dashboard
class DashboardStatsSerializer(serializers.Serializer):
    total_pacientes = serializers.IntegerField()
    consultas_hoy = serializers.IntegerField()
    solicitudes_pendientes = serializers.IntegerField()
    resultados_listos = serializers.IntegerField()
    consultas_por_especialidad = serializers.DictField()
    solicitudes_por_estado = serializers.DictField()


# Serializers para búsquedas
class PacienteSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paciente
        fields = ['id', 'nombre', 'apellido', 'dni', 'fecha_nacimiento', 'sexo']


class ConsultaSearchSerializer(serializers.ModelSerializer):
    paciente_nombre = serializers.CharField(source='historia_clinica.paciente.nombre', read_only=True)
    paciente_apellido = serializers.CharField(source='historia_clinica.paciente.apellido', read_only=True)
    medico_nombre = serializers.CharField(source='medico.nombre', read_only=True)
    medico_apellido = serializers.CharField(source='medico.apellido', read_only=True)
    
    class Meta:
        model = Consulta
        fields = ['id', 'fecha_hora_consulta', 'motivo_consulta_detalle', 
                 'paciente_nombre', 'paciente_apellido', 'medico_nombre', 'medico_apellido'] 


# NUEVO: Serializer para Internaciones
class InternacionSerializer(serializers.ModelSerializer):
    paciente = PacienteSerializer(read_only=True)
    medico_responsable = MedicoSerializer(read_only=True)
    duracion_dias = serializers.ReadOnlyField()
    
    class Meta:
        model = Internacion
        fields = '__all__' 