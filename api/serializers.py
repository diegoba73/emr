from rest_framework import serializers
from django.contrib.auth import get_user_model
from pacientes.models import Paciente
from medicos.models import Medico, Especialidad
from medicos.models import DisponibilidadMedico, ExcepcionMedico

User = get_user_model()
# from laboratorio.models import TipoExamen, PanelExamen, SolicitudExamen, ResultadoExamen
from historias_clinicas.models import HistoriaClinica, Consulta, Diagnostico, Prescripcion, Internacion
from catalogos.models import DiagnosticoCIE10, Medicamento
from turnos.models import Turno, Recurso, Atencion, ConsultaAmbulatoria, RegistroProcedimiento, RegistroQuirurgico
from catalogos.models import EstudioDiagnostico, ProcedimientoCatalogo
from emr.models import SignosVitales, Documento


class DiagnosticoCIE10Serializer(serializers.ModelSerializer):
    """Serializer para diagnósticos CIE-10"""
    class Meta:
        model = DiagnosticoCIE10
        fields = ['id', 'codigo', 'descripcion', 'categoria', 'capitulo', 'enfermedad', 'tipo_enfermedad', 'activo']


class PacienteSerializer(serializers.ModelSerializer):
    """
    Serializer para Paciente que lee datos directamente de la tabla pacientes_paciente
    sin depender de la tabla usuarios.
    """
    class Meta:
        model = Paciente
        fields = '__all__'


class EspecialidadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Especialidad
        fields = '__all__'


class MedicoLightSerializer(serializers.ModelSerializer):
    """
    Serializer ligero para búsquedas y dropdowns.
    Excluye campos pesados como areas_interes_ia.
    """
    especialidad_nombre = serializers.CharField(source='especialidad.nombre', read_only=True)
    nombre_completo = serializers.ReadOnlyField()
    
    class Meta:
        model = Medico
        fields = [
            'id',
            'nombre',
            'apellido',
            'nombre_completo',
            'matricula',
            'especialidad_nombre',
        ]
        read_only_fields = fields


class MedicoSerializer(serializers.ModelSerializer):
    especialidad = EspecialidadSerializer(read_only=True)
    especialidad_id = serializers.PrimaryKeyRelatedField(
        queryset=Especialidad.objects.all(),
        source='especialidad',
        write_only=True,
        required=False,
        allow_null=True,
    )
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True,
    )
    nombre_completo = serializers.ReadOnlyField()
    email = serializers.SerializerMethodField()
    telefono = serializers.SerializerMethodField()

    class Meta:
        model = Medico
        fields = [
            'id',
            'nombre',
            'apellido',
            'nombre_completo',
            'matricula',
            'especialidad',
            'especialidad_id',
            'user',
            'areas_interes_ia',
            'email',
            'telefono',
            'fecha_registro',
            'ultima_actualizacion',
        ]
        read_only_fields = (
            'id',
            'especialidad',
            'nombre_completo',
            'email',
            'telefono',
            'fecha_registro',
            'ultima_actualizacion',
        )

    @staticmethod
    def _clean_name(value):
        if value is None:
            return None
        value = value.strip()
        return value or None

    def validate(self, attrs):
        attrs = super().validate(attrs)
        nombre = attrs.get('nombre') or (self.instance.nombre if self.instance else '')
        apellido = attrs.get('apellido') or (self.instance.apellido if self.instance else '')
        user = attrs.get('user') or (self.instance.user if self.instance else None)

        if not (apellido or (user and user.last_name)):
            raise serializers.ValidationError(
                "Debe indicar un apellido o asociar un usuario con apellido cargado."
            )
        return attrs

    def create(self, validated_data):
        validated_data['nombre'] = self._clean_name(validated_data.get('nombre'))
        validated_data['apellido'] = self._clean_name(validated_data.get('apellido'))
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if 'nombre' in validated_data:
            validated_data['nombre'] = self._clean_name(validated_data.get('nombre'))
        if 'apellido' in validated_data:
            validated_data['apellido'] = self._clean_name(validated_data.get('apellido'))
        return super().update(instance, validated_data)

    def get_email(self, obj):
        return obj.email

    def get_telefono(self, obj):
        return obj.telefono


class DisponibilidadMedicoSerializer(serializers.ModelSerializer):
    medico_detalle = MedicoSerializer(source='medico', read_only=True)

    class Meta:
        model = DisponibilidadMedico
        fields = '__all__'


class ExcepcionMedicoSerializer(serializers.ModelSerializer):
    medico_detalle = MedicoSerializer(source='medico', read_only=True)

    class Meta:
        model = ExcepcionMedico
        fields = '__all__'


# class TipoExamenSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = TipoExamen
#         fields = '__all__'


# class PanelExamenSerializer(serializers.ModelSerializer):
#     examenes = TipoExamenSerializer(many=True, read_only=True)
#     
#     class Meta:
#         model = PanelExamen
#         fields = '__all__'


class HistoriaClinicaSerializer(serializers.ModelSerializer):
    paciente = PacienteSerializer(read_only=True)
    
    class Meta:
        model = HistoriaClinica
        fields = '__all__'


class ConsultaSerializer(serializers.ModelSerializer):
    """
    Serializer optimizado para consultas con relaciones eficientes.
    Incluye paciente resumido y médico completo para evitar N+1 queries.
    """
    # Paciente resumido (solo campos esenciales para display)
    paciente_nombre = serializers.CharField(source='historia_clinica.paciente.nombre', read_only=True)
    paciente_apellido = serializers.CharField(source='historia_clinica.paciente.apellido', read_only=True)
    paciente_dni = serializers.CharField(source='historia_clinica.paciente.dni', read_only=True)
    paciente_id = serializers.IntegerField(source='historia_clinica.paciente.id', read_only=True)
    
    # Historia clínica completa (para compatibilidad)
    historia_clinica = HistoriaClinicaSerializer(read_only=True)
    
    # Médico completo
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


# class SolicitudExamenSerializer(serializers.ModelSerializer):
#     paciente = PacienteSerializer(read_only=True)
#     medico = MedicoSerializer(read_only=True)
#     consulta = ConsultaSerializer(read_only=True)
#     examenes_individuales = TipoExamenSerializer(many=True, read_only=True)
#     paneles = PanelExamenSerializer(many=True, read_only=True)
#     
#     class Meta:
#         model = SolicitudExamen
#         fields = '__all__'


# class ResultadoExamenSerializer(serializers.ModelSerializer):
#     solicitud = SolicitudExamenSerializer(read_only=True)
#     tipo_examen = TipoExamenSerializer(read_only=True)
#     validado_por = MedicoSerializer(read_only=True)
#     
#     class Meta:
#         model = ResultadoExamen
#         fields = '__all__'


# Serializers para Turnos
class RecursoSerializer(serializers.ModelSerializer):
    """Serializer para recursos físicos agendables"""
    tipo_recurso_display = serializers.CharField(source='get_tipo_recurso_display', read_only=True)
    ubicacion_display = serializers.CharField(source='get_ubicacion_display', read_only=True)
    
    class Meta:
        model = Recurso
        fields = ['id', 'nombre', 'ubicacion', 'ubicacion_display', 'tipo_recurso', 'tipo_recurso_display', 'activo']


class TurnoSerializer(serializers.ModelSerializer):
    paciente = PacienteSerializer(read_only=True, allow_null=True)
    paciente_id = serializers.IntegerField(read_only=True, allow_null=True)
    medico = MedicoSerializer(read_only=True, allow_null=True)
    medico_id = serializers.IntegerField(read_only=True, allow_null=True)
    recurso = RecursoSerializer(read_only=True, allow_null=True)
    recurso_id = serializers.IntegerField(read_only=True, allow_null=True)
    atencion = serializers.SerializerMethodField()
    
    class Meta:
        model = Turno
        fields = ['id', 'paciente', 'paciente_id', 'medico', 'medico_id', 'recurso', 'recurso_id',
                  'fecha_hora_inicio', 'fecha_hora_fin', 'estado', 'motivo_reserva', 'atencion']
    
    def to_representation(self, instance):
        """Sobrescribir para asegurar que los objetos relacionados se serialicen correctamente"""
        data = super().to_representation(instance)
        
        # Si los objetos relacionados no están cargados pero tenemos IDs, intentar cargarlos
        # Esto es solo para asegurar que los datos se serialicen correctamente
        if instance:
            # Si paciente_id existe pero paciente no está serializado, intentar cargarlo
            if instance.paciente_id and not data.get('paciente'):
                try:
                    from pacientes.models import Paciente
                    paciente = Paciente.objects.get(pk=instance.paciente_id)
                    data['paciente'] = PacienteSerializer(paciente).data
                except Exception:
                    pass
            
            # Si medico_id existe pero medico no está serializado, intentar cargarlo
            if instance.medico_id and not data.get('medico'):
                try:
                    from medicos.models import Medico
                    medico = Medico.objects.get(pk=instance.medico_id)
                    data['medico'] = MedicoSerializer(medico).data
                except Exception:
                    pass
            
            # Si recurso_id existe pero recurso no está serializado, intentar cargarlo
            if instance.recurso_id and not data.get('recurso'):
                try:
                    from turnos.models import Recurso
                    recurso = Recurso.objects.get(pk=instance.recurso_id)
                    data['recurso'] = RecursoSerializer(recurso).data
                except Exception:
                    pass
        
        return data
    
    
    def get_atencion(self, obj):
        """Retorna información básica de la atención si existe, incluyendo registros"""
        if not obj:
            return None
        try:
            # Usar hasattr para verificar si existe la relación sin causar una consulta adicional
            if hasattr(obj, 'atencion') and obj.atencion:
                atencion = obj.atencion
                result = {
                    'id': atencion.id,
                    'fecha_admision': atencion.fecha_admision,
                    'tipo_atencion': atencion.tipo_atencion,
                    'tipo_intervencion': atencion.tipo_intervencion,
                    'estado_clinico': atencion.estado_clinico,
                }
                
                # Incluir información sobre los registros si existen
                # Esto ayuda al frontend a determinar si debe mostrar "Crear" o "Editar"
                try:
                    if hasattr(atencion, 'consulta_ambulatoria') and atencion.consulta_ambulatoria:
                        result['consulta_ambulatoria'] = {'id': atencion.consulta_ambulatoria.id}
                except (AttributeError, TypeError):
                    pass
                
                try:
                    if hasattr(atencion, 'registro_procedimiento') and atencion.registro_procedimiento:
                        result['registro_procedimiento'] = {'id': atencion.registro_procedimiento.id}
                except (AttributeError, TypeError):
                    pass
                
                try:
                    if hasattr(atencion, 'registro_quirurgico') and atencion.registro_quirurgico:
                        result['registro_quirurgico'] = {'id': atencion.registro_quirurgico.id}
                except (AttributeError, TypeError):
                    pass
                
                return result
        except (Atencion.DoesNotExist, AttributeError, TypeError):
            pass
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
    recurso_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    
    # Campos para lectura (objetos completos)
    paciente = PacienteSerializer(read_only=True)
    medico = MedicoSerializer(read_only=True)
    recurso = RecursoSerializer(read_only=True)
    
    class Meta:
        model = Turno
        fields = ['id', 'paciente', 'paciente_id', 'medico', 'medico_id', 'recurso', 'recurso_id',
                  'fecha_hora_inicio', 'fecha_hora_fin', 'estado', 'motivo_reserva']
        extra_kwargs = {
            'fecha_hora_inicio': {'required': True},
            'fecha_hora_fin': {'required': False, 'allow_null': True},
            'motivo_reserva': {'required': False, 'allow_null': True},
            'estado': {'required': False},
        }
    
    def create(self, validated_data):
        # Extraer los IDs de los campos write_only
        paciente_id = validated_data.pop('paciente_id', None)
        medico_id = validated_data.pop('medico_id', None)
        recurso_id = validated_data.pop('recurso_id', None)
        
        # Crear la instancia primero
        instance = super().create(validated_data)
        
        # Asignar los IDs directamente a la instancia después de crearla
        if paciente_id is not None:
            instance.paciente_id = paciente_id
        if medico_id is not None:
            instance.medico_id = medico_id
        if recurso_id is not None:
            instance.recurso_id = recurso_id
        
        # Guardar la instancia con los IDs actualizados
        if paciente_id is not None or medico_id is not None or recurso_id is not None:
            instance.save()
        
        return instance
    
    def update(self, instance, validated_data):
        # Extraer los IDs de los campos write_only
        paciente_id = validated_data.pop('paciente_id', None)
        medico_id = validated_data.pop('medico_id', None)
        recurso_id = validated_data.pop('recurso_id', None)
        
        # Asignar los IDs a los campos del modelo
        if paciente_id is not None:
            validated_data['paciente_id'] = paciente_id
        if medico_id is not None:
            validated_data['medico_id'] = medico_id
        if recurso_id is not None:
            validated_data['recurso_id'] = recurso_id
        
        return super().update(instance, validated_data)


# Serializers para Atencion y modelos relacionados
class EstudioDiagnosticoSerializer(serializers.ModelSerializer):
    """Serializer para catálogo de estudios diagnósticos"""
    class Meta:
        model = EstudioDiagnostico
        fields = ['id', 'nombre', 'descripcion', 'activo']


class ProcedimientoCatalogoSerializer(serializers.ModelSerializer):
    """Serializer para catálogo de procedimientos"""
    class Meta:
        model = ProcedimientoCatalogo
        fields = ['id', 'nombre', 'descripcion', 'activo']


class DocumentoSerializer(serializers.ModelSerializer):
    """Serializer para documentos clínicos asociados a una atención"""
    atencion_id = serializers.PrimaryKeyRelatedField(
        source='atencion',
        queryset=Atencion.objects.all(),
        write_only=True
    )
    usuario_cargador_id = serializers.IntegerField(source='usuario_cargador.id', read_only=True)
    usuario_cargador_nombre = serializers.SerializerMethodField()
    # Campo para lectura: devuelve la URL del archivo
    archivo_url = serializers.SerializerMethodField()
    # Campo para escritura: recibe el archivo subido
    archivo = serializers.FileField(write_only=True)

    class Meta:
        model = Documento
        fields = [
            'id',
            'atencion_id',
            'tipo_documento',
            'archivo',
            'archivo_url',
            'descripcion',
            'fecha_subida',
            'usuario_cargador_id',
            'usuario_cargador_nombre',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['fecha_subida', 'usuario_cargador_id', 'usuario_cargador_nombre', 'created_at', 'updated_at']

    def get_archivo_url(self, obj):
        """Retornar la URL del archivo de forma segura"""
        if obj.archivo:
            request = self.context.get('request')
            if request:
                try:
                    return request.build_absolute_uri(obj.archivo.url)
                except Exception:
                    # Si falla (ej: host inválido en tests), devolver URL relativa
                    return obj.archivo.url
            # Si no hay request, retornar la URL relativa
            return obj.archivo.url
        return None

    def get_usuario_cargador_nombre(self, obj):
        if obj.usuario_cargador:
            full_name = obj.usuario_cargador.get_full_name()
            return full_name or obj.usuario_cargador.username
        return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['atencion_id'] = instance.atencion_id
        # Mantener compatibilidad: devolver archivo como la URL para el frontend
        data['archivo'] = self.get_archivo_url(instance)
        return data


class SignosVitalesSerializer(serializers.ModelSerializer):
    """
    Serializer para registros de signos vitales con validaciones clínicas y normalización.
    Usa EXCLUSIVAMENTE 'atencion_id' para escritura y lectura (sin atencion_id_write).
    """
    # Campo atencion_id: acepta ID en escritura, devuelve ID en lectura
    atencion_id = serializers.PrimaryKeyRelatedField(
        queryset=Atencion.objects.all(),
        source='atencion',
        write_only=True,
        required=True,
        error_messages={
            'required': 'El campo atencion_id es obligatorio.',
            'does_not_exist': 'La atención especificada no existe.',
            'incorrect_type': 'El campo atencion_id debe ser un número entero válido.'
        }
    )
    registrado_por_id = serializers.IntegerField(source='registrado_por.id', read_only=True)
    registrado_por_nombre = serializers.SerializerMethodField()

    class Meta:
        model = SignosVitales
        fields = [
            'id',
            'atencion_id',  # Escritura: acepta ID, Lectura: devuelve ID (via to_representation)
            'rol_registrador',
            'fecha_registro',
            'tension_arterial',
            'frecuencia_cardiaca',
            'frecuencia_respiratoria',
            'temperatura',
            'saturacion_oxigeno',
            'indice_masa_corporal',
            'peso',
            'talla',
            'registrado_por_id',
            'registrado_por_nombre',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['registrado_por_id', 'registrado_por_nombre', 'created_at', 'updated_at']

    def get_registrado_por_nombre(self, obj):
        if obj.registrado_por:
            full_name = obj.registrado_por.get_full_name()
            return full_name or obj.registrado_por.username
        return None

    def validate_indice_masa_corporal(self, value):
        """
        Normalizar IMC a 2 decimales (sin validación de rango).
        Validaciones de rango deshabilitadas temporalmente para evaluación del flujo.
        """
        if value is None:
            return value
        
        # Solo normalizar a 2 decimales (sin validar rango)
        from decimal import Decimal, ROUND_HALF_UP
        return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def validate_temperatura(self, value):
        """Normalizar temperatura a 1 decimal"""
        if value is None:
            return value
        
        from decimal import Decimal, ROUND_HALF_UP
        return Decimal(str(value)).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)

    def validate_saturacion_oxigeno(self, value):
        """Normalizar saturación de oxígeno a 1 decimal"""
        if value is None:
            return value
        
        from decimal import Decimal, ROUND_HALF_UP
        return Decimal(str(value)).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)

    def validate_peso(self, value):
        """Normalizar peso a 2 decimales"""
        if value is None:
            return value
        
        from decimal import Decimal, ROUND_HALF_UP
        return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def validate_talla(self, value):
        """Normalizar talla a 2 decimales"""
        if value is None:
            return value
        
        from decimal import Decimal, ROUND_HALF_UP
        return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def validate(self, data):
        """
        Validaciones clínicas DESHABILITADAS temporalmente para evaluación del flujo.
        Solo se realiza normalización de datos sin rechazar valores.
        
        Rangos clínicos de referencia (para futuro):
        - Frecuencia cardíaca: 30-220 bpm
        - Frecuencia respiratoria: 8-60 rpm
        - Temperatura: 30-45 °C
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"✅ SignosVitalesSerializer.validate - data recibida (sin validaciones de rango): {data}")
        
        # Validaciones de rango deshabilitadas para evaluación del flujo
        # Los datos se aceptan tal como vienen
        
        return data

    def to_representation(self, instance):
        """
        Asegurar que atencion_id siempre esté presente como entero en la respuesta.
        Como atencion_id es write_only en el campo, necesitamos agregarlo manualmente en lectura.
        """
        data = super().to_representation(instance)
        # Como atencion_id es write_only, no aparece en la representación por defecto
        # Lo agregamos manualmente como entero
        data['atencion_id'] = instance.atencion_id if hasattr(instance, 'atencion_id') else None
        return data


class ConsultaAmbulatoriaSerializer(serializers.ModelSerializer):
    """Serializer para consultas ambulatorias"""
    atencion_id = serializers.IntegerField(source='atencion.id', read_only=True)
    id = serializers.IntegerField(source='atencion_id', read_only=True)  # Campo calculado para compatibilidad
    
    class Meta:
        model = ConsultaAmbulatoria
        fields = [
            'id',
            'atencion_id',
            'anamnesis',
            'examen_fisico',
            'diagnostico_presuntivo',
            'plan_manejo',
            'antecedentes_relevantes',
            'alergias',
            'medicacion_actual',
            'diagnostico_definitivo',
            'observaciones_medicas',
        ]


class RegistroProcedimientoSerializer(serializers.ModelSerializer):
    """Serializer para registros de procedimientos/estudios"""
    atencion_id = serializers.IntegerField(source='atencion.id', read_only=True)
    id = serializers.IntegerField(source='atencion_id', read_only=True)  # Campo calculado para compatibilidad
    estudio = EstudioDiagnosticoSerializer(read_only=True)
    estudio_id = serializers.PrimaryKeyRelatedField(
        source='estudio',
        queryset=EstudioDiagnostico.objects.filter(activo=True),
        write_only=True,
        required=False,
        allow_null=True
    )
    procedimiento = ProcedimientoCatalogoSerializer(read_only=True)
    procedimiento_id = serializers.PrimaryKeyRelatedField(
        source='procedimiento',
        queryset=ProcedimientoCatalogo.objects.filter(activo=True),
        write_only=True,
        required=False,
        allow_null=True
    )
    profesional_asistente = MedicoSerializer(read_only=True)
    profesional_asistente_id = serializers.PrimaryKeyRelatedField(
        source='profesional_asistente',
        queryset=Medico.objects.all(),
        write_only=True,
        required=False,
        allow_null=True
    )
    tipo_procedimiento = serializers.ChoiceField(
        choices=RegistroProcedimiento.TipoProcedimiento.choices,
        required=False,
        allow_null=True
    )
    adjunto_resultado = serializers.FileField(required=False, allow_null=True)
    
    class Meta:
        model = RegistroProcedimiento
        fields = [
            'id',
            'atencion_id',
            'estudio',
            'estudio_id',
            'procedimiento',
            'procedimiento_id',
            'descripcion_procedimiento',
            'tipo_procedimiento',
            'informe_medico',
            'hallazgos',
            'profesional_asistente',
            'profesional_asistente_id',
            'complicaciones',
            'adjunto_resultado',
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['atencion_id'] = instance.atencion_id
        return data


class RegistroQuirurgicoSerializer(serializers.ModelSerializer):
    """Serializer para registros quirúrgicos"""
    atencion_id = serializers.IntegerField(source='atencion.id', read_only=True)
    id = serializers.IntegerField(source='atencion_id', read_only=True)  # Campo calculado para compatibilidad
    anestesista = MedicoSerializer(read_only=True)
    anestesista_id = serializers.IntegerField(write_only=True, required=True)
    procedimiento = ProcedimientoCatalogoSerializer(read_only=True)
    procedimiento_id = serializers.PrimaryKeyRelatedField(
        source='procedimiento',
        queryset=ProcedimientoCatalogo.objects.filter(activo=True),
        write_only=True,
        required=False,
        allow_null=True
    )
    documentos_adjuntos = DocumentoSerializer(many=True, read_only=True)
    documentos_adjuntos_ids = serializers.PrimaryKeyRelatedField(
        source='documentos_adjuntos',
        queryset=Documento.objects.all(),
        many=True,
        required=False
    )
    equipo_quirurgico = serializers.JSONField(required=False)
    consentimiento_informado = serializers.FileField(required=False, allow_null=True)
    
    class Meta:
        model = RegistroQuirurgico
        fields = [
            'id',
            'atencion_id',
            'anestesista',
            'anestesista_id',
            'procedimiento',
            'procedimiento_id',
            'diagnostico_preoperatorio',
            'diagnostico_postoperatorio',
            'protocolo_quirurgico',
            'hallazgos_operatorios',
            'complicaciones',
            'recuento_instrumental_ok',
            'equipo_quirurgico',
            'consentimiento_informado',
            'documentos_adjuntos',
            'documentos_adjuntos_ids',
        ]
    
    def create(self, validated_data):
        anestesista_id = validated_data.pop('anestesista_id')
        documentos = validated_data.pop('documentos_adjuntos', [])
        validated_data['anestesista_id'] = anestesista_id
        instance = super().create(validated_data)
        if documentos:
            instance.documentos_adjuntos.set(documentos)
        return instance
    
    def update(self, instance, validated_data):
        anestesista_id = validated_data.pop('anestesista_id', None)
        if anestesista_id is not None:
            validated_data['anestesista_id'] = anestesista_id
        documentos = validated_data.pop('documentos_adjuntos', None)
        instance = super().update(instance, validated_data)
        if documentos is not None:
            instance.documentos_adjuntos.set(documentos)
        return instance

    def validate_documentos_adjuntos_ids(self, value):
        if self.instance:
            atencion_id = self.instance.atencion_id
        else:
            atencion = self.context.get('atencion')
            if isinstance(atencion, Atencion):
                atencion_id = atencion.id
            else:
                atencion_id = self.initial_data.get('atencion_id') or None
        expected_id = int(atencion_id) if atencion_id is not None else None
        for documento in value:
            if expected_id is not None and documento.atencion_id != expected_id:
                raise serializers.ValidationError(
                    f'El documento {documento.id} no pertenece a la atención especificada.'
                )
        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Asegurar que id esté presente (calculado desde atencion_id)
        data['id'] = instance.atencion_id
        data['atencion_id'] = instance.atencion_id
        # Incluir anestesista_id y procedimiento_id para que el frontend pueda usarlos
        # Estos campos están marcados como write_only, pero el frontend los necesita para prellenar el formulario
        data['anestesista_id'] = getattr(instance, 'anestesista_id', None)
        data['procedimiento_id'] = getattr(instance, 'procedimiento_id', None)
        return data


class AtencionSerializer(serializers.ModelSerializer):
    """Serializer completo para Atencion con sus registros relacionados.
    SIEMPRE devuelve IDs explícitos junto con objetos anidados."""
    paciente = PacienteSerializer(read_only=True)
    paciente_id = serializers.IntegerField(read_only=True)
    medico_principal = MedicoSerializer(read_only=True)
    medico_principal_id = serializers.IntegerField(read_only=True)
    turno = TurnoSerializer(read_only=True, allow_null=True)
    turno_id = serializers.IntegerField(read_only=True, allow_null=True)
    consulta_ambulatoria = ConsultaAmbulatoriaSerializer(read_only=True, allow_null=True)
    registro_procedimiento = RegistroProcedimientoSerializer(read_only=True, allow_null=True)
    registro_quirurgico = RegistroQuirurgicoSerializer(read_only=True, allow_null=True)
    tipo_atencion_display = serializers.CharField(source='get_tipo_atencion_display', read_only=True)
    documentos = DocumentoSerializer(many=True, read_only=True)
    
    def to_representation(self, instance):
        """Sobrescribir para asegurar que los IDs siempre estén presentes"""
        if not instance:
            return {'error': 'Instancia de atención no válida'}
        
        # Serializar normalmente
        data = super().to_representation(instance)
        
        # Asegurar que los IDs siempre estén presentes
        if 'paciente_id' not in data or data['paciente_id'] is None:
            data['paciente_id'] = getattr(instance, 'paciente_id', None)
        
        if 'medico_principal_id' not in data or data['medico_principal_id'] is None:
            data['medico_principal_id'] = getattr(instance, 'medico_principal_id', None)
        
        if 'turno_id' not in data or data['turno_id'] is None:
            data['turno_id'] = getattr(instance, 'turno_id', None)
        
        return data
    
    class Meta:
        model = Atencion
        fields = [
            'id',
            'turno',
            'turno_id',
            'paciente',
            'paciente_id',
            'medico_principal',
            'medico_principal_id',
            'fecha_admision',
            'fecha_cierre',
            'tipo_atencion',
            'tipo_atencion_display',
            'tipo_intervencion',
            'estado_clinico',
            'observaciones_generales',
            'consulta_ambulatoria',
            'registro_procedimiento',
            'registro_quirurgico',
            'documentos',
            'created_at',
            'updated_at',
        ]


class AtencionUpdateSerializer(serializers.ModelSerializer):
    """Serializer para actualizar estados y notas de la atención"""

    class Meta:
        model = Atencion
        fields = ['tipo_intervencion', 'estado_clinico', 'observaciones_generales', 'fecha_cierre']


class AtencionCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear Atencion desde un turno"""
    turno_id = serializers.PrimaryKeyRelatedField(
        queryset=Turno.objects.all(),
        source='turno',
        write_only=True,
        required=True
    )
    paciente_id = serializers.PrimaryKeyRelatedField(
        queryset=Paciente.objects.all(),
        source='paciente',
        write_only=True,
        required=True
    )
    medico_principal_id = serializers.PrimaryKeyRelatedField(
        queryset=Medico.objects.all(),
        source='medico_principal',
        write_only=True,
        required=True
    )
    
    class Meta:
        model = Atencion
        fields = [
            'turno_id',
            'paciente_id',
            'medico_principal_id',
            'tipo_atencion',
            'tipo_intervencion',
            'estado_clinico',
            'observaciones_generales',
            'fecha_cierre',
        ]
        extra_kwargs = {
            'paciente': {'required': False, 'read_only': True},
            'medico_principal': {'required': False, 'read_only': True},
            'turno': {'required': False, 'read_only': True},
        }
    
    def to_internal_value(self, data):
        """Sobrescribir para excluir los campos del modelo que no queremos validar"""
        # Remover los campos del modelo si están presentes
        if isinstance(data, dict):
            print(f"🔍 AtencionCreateSerializer.to_internal_value - datos recibidos: {data}")
            data = data.copy()
            data.pop('paciente', None)
            data.pop('medico_principal', None)
            data.pop('turno', None)
            print(f"🔍 Datos después de limpiar: {data}")
        return super().to_internal_value(data)
    
    
    def create(self, validated_data):
        # Los campos ya están mapeados correctamente por PrimaryKeyRelatedField con source
        # validated_data ya contiene 'turno', 'paciente', 'medico_principal' como objetos
        print(f"📝 Creando Atencion - validated_data: {validated_data}")
        
        instance = super().create(validated_data)
        
        print(f"✅ Atencion {instance.id} creada - paciente_id: {instance.paciente_id}, medico_principal_id: {instance.medico_principal_id}")
        
        return instance


# Serializers para estadísticas del panel
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
        fields = ['id', 'nombre', 'apellido', 'dni', 'fecha_nacimiento', 'sexo', 'email', 'telefono', 'direccion', 'obra_social']


class MedicoSearchSerializer(serializers.ModelSerializer):
    especialidad = EspecialidadSerializer(read_only=True)
    email = serializers.SerializerMethodField()
    telefono = serializers.SerializerMethodField()

    class Meta:
        model = Medico
        fields = ['id', 'nombre', 'apellido', 'matricula', 'especialidad', 'email', 'telefono']
    
    def get_email(self, obj):
        """Obtener email del usuario asociado si existe"""
        if obj.user and obj.user.email:
            return obj.user.email
        return None
    
    def get_telefono(self, obj):
        """Obtener teléfono del usuario asociado si existe"""
        if obj.user and obj.user.telefono:
            return obj.user.telefono
        return None


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