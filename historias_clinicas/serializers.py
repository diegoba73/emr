from rest_framework import serializers
from .models import Consulta, Internacion
from pacientes.serializers import PacienteSerializer
from medicos.serializers import MedicoSerializer
from turnos.serializers import TurnoSerializer
from catalogos.serializers import CamaInternacionSerializer

class ConsultaSerializer(serializers.ModelSerializer):
    historia_clinica = serializers.SerializerMethodField()
    medico = MedicoSerializer(read_only=True)
    turno = TurnoSerializer(read_only=True)
    
    class Meta:
        model = Consulta
        fields = '__all__'
    
    def get_historia_clinica(self, obj):
        return {
            'id': obj.historia_clinica.id,
            'paciente': {
                'id': obj.historia_clinica.paciente.id,
                'nombre': obj.historia_clinica.paciente.user.first_name,
                'apellido': obj.historia_clinica.paciente.user.last_name,
                'dni': obj.historia_clinica.paciente.dni
            }
        }

class InternacionSerializer(serializers.ModelSerializer):
    paciente = PacienteSerializer(read_only=True)
    medico_responsable = MedicoSerializer(read_only=True)
    cama = CamaInternacionSerializer(read_only=True)
    turno_origen = TurnoSerializer(read_only=True)
    duracion_dias = serializers.ReadOnlyField()
    centro_fisico = serializers.SerializerMethodField()
    area_internacion = serializers.SerializerMethodField()
    
    class Meta:
        model = Internacion
        fields = '__all__'
    
    def get_centro_fisico(self, obj):
        return {
            'codigo': obj.centro_fisico.codigo,
            'nombre': obj.centro_fisico.nombre
        }
    
    def get_area_internacion(self, obj):
        return {
            'codigo': obj.area_internacion.codigo,
            'nombre': obj.area_internacion.nombre
        }

class InternacionCreateSerializer(serializers.ModelSerializer):
    paciente_id = serializers.IntegerField(write_only=True)
    medico_responsable_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    cama_id = serializers.IntegerField(write_only=True)
    turno_origen_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    
    paciente = PacienteSerializer(read_only=True)
    medico_responsable = MedicoSerializer(read_only=True)
    cama = CamaInternacionSerializer(read_only=True)
    turno_origen = TurnoSerializer(read_only=True)
    
    class Meta:
        model = Internacion
        fields = '__all__'
        extra_kwargs = {
            'numero_internacion': {'read_only': True},
            'fecha_registro': {'read_only': True},
            'ultima_actualizacion': {'read_only': True},
        }


