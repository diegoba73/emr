from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import transaction
from .models import UserProfile
from medicos.models import Medico, Especialidad
from pacientes.models import Paciente

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Serializer personalizado para obtener tokens JWT con información adicional del usuario
    """
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Agregar información adicional del usuario al token
        data['user'] = {
            'id': self.user.id,
            'username': self.user.username,
            'email': self.user.email,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'rol': self.user.rol,
            'is_active': self.user.is_active,
            'is_staff': self.user.is_staff,
            'is_superuser': self.user.is_superuser,
        }
        
        return data


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer para la gestión de usuarios por administradores
    """
    password = serializers.CharField(
        write_only=True,
        required=False,
        validators=[validate_password],
        help_text='Contraseña del usuario'
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=False,
        help_text='Confirmación de la contraseña'
    )
    # Campos para asociar con médico o paciente existente
    medico_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    paciente_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    # Campos para crear nuevo médico
    medico_data = serializers.DictField(write_only=True, required=False, allow_null=True)
    # Campos para crear nuevo paciente
    paciente_data = serializers.DictField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'rol', 'telefono', 'is_active', 'is_staff', 'is_superuser',
            'password', 'password_confirm', 'date_joined', 'last_login',
            'medico_id', 'paciente_id', 'medico_data', 'paciente_data'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']
        extra_kwargs = {
            'password': {'write_only': True, 'required': False},
            'password_confirm': {'write_only': True, 'required': False},
        }
    
    def validate(self, attrs):
        """
        Validación personalizada para el serializer
        """
        # Verificar que las contraseñas coincidan (solo si se proporcionan)
        password = attrs.get('password')
        password_confirm = attrs.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            raise serializers.ValidationError({
                'password_confirm': 'Las contraseñas no coinciden.'
            })
        
        # Si es creación y no hay password, requerirlo
        if not self.instance and not password:
            raise serializers.ValidationError({
                'password': 'La contraseña es requerida para nuevos usuarios.'
            })
        
        # Validar que el username sea único
        username = attrs.get('username')
        if username and User.objects.filter(username=username).exists():
            if self.instance and self.instance.username == username:
                pass  # Es el mismo usuario, no hay problema
            else:
                raise serializers.ValidationError({
                    'username': 'Este nombre de usuario ya está en uso.'
                })
        
        # Validar que el email sea único
        email = attrs.get('email')
        if email and User.objects.filter(email=email).exists():
            if self.instance and self.instance.email == email:
                pass  # Es el mismo usuario, no hay problema
            else:
                raise serializers.ValidationError({
                    'email': 'Este email ya está en uso.'
                })
        
        # Validar asociación médico/paciente según el rol (solo para creación, no para edición)
        rol = attrs.get('rol', self.instance.rol if self.instance else None)
        medico_id = attrs.get('medico_id')
        paciente_id = attrs.get('paciente_id')
        medico_data = attrs.get('medico_data')
        paciente_data = attrs.get('paciente_data')
        
        # Solo validar si es creación de usuario (no edición)
        if not self.instance:
            if rol == 'medico':
                if not medico_id and not medico_data:
                    raise serializers.ValidationError({
                        'medico_id': 'Debe proporcionar un médico existente (medico_id) o datos para crear uno nuevo (medico_data).'
                    })
                if medico_id and medico_data:
                    raise serializers.ValidationError({
                        'medico_id': 'No puede proporcionar tanto medico_id como medico_data. Use solo uno.'
                    })
                if medico_id:
                    try:
                        medico = Medico.objects.get(id=medico_id)
                        if medico.user:
                            raise serializers.ValidationError({
                                'medico_id': 'Este médico ya está asociado a otro usuario.'
                            })
                    except Medico.DoesNotExist:
                        raise serializers.ValidationError({
                            'medico_id': 'El médico especificado no existe.'
                        })
            
            if rol == 'paciente':
                if not paciente_id and not paciente_data:
                    raise serializers.ValidationError({
                        'paciente_id': 'Debe proporcionar un paciente existente (paciente_id) o datos para crear uno nuevo (paciente_data).'
                    })
                if paciente_id and paciente_data:
                    raise serializers.ValidationError({
                        'paciente_id': 'No puede proporcionar tanto paciente_id como paciente_data. Use solo uno.'
                    })
                if paciente_id:
                    try:
                        paciente = Paciente.objects.get(id=paciente_id)
                        if paciente.user:
                            raise serializers.ValidationError({
                                'paciente_id': 'Este paciente ya está asociado a otro usuario.'
                            })
                    except Paciente.DoesNotExist:
                        raise serializers.ValidationError({
                            'paciente_id': 'El paciente especificado no existe.'
                        })
        
        return attrs
    
    def create(self, validated_data):
        """
        Crear un nuevo usuario con contraseña hasheada y asociar con médico/paciente si corresponde
        """
        # Extraer datos de médico/paciente
        medico_id = validated_data.pop('medico_id', None)
        paciente_id = validated_data.pop('paciente_id', None)
        medico_data = validated_data.pop('medico_data', None)
        paciente_data = validated_data.pop('paciente_data', None)
        rol = validated_data.get('rol')
        
        # Remover password_confirm del validated_data
        validated_data.pop('password_confirm', None)
        
        with transaction.atomic():
            # Sincronizar datos desde médico/paciente si se está asociando con uno existente
            if rol == 'medico' and medico_id:
                medico = Medico.objects.get(id=medico_id)
                # Si el usuario no tiene nombre/apellido, tomarlos del médico
                if not validated_data.get('first_name') and medico.nombre:
                    validated_data['first_name'] = medico.nombre
                if not validated_data.get('last_name') and medico.apellido:
                    validated_data['last_name'] = medico.apellido
                # Email y teléfono del médico vienen del user, así que no hay que sincronizar
            
            elif rol == 'paciente' and paciente_id:
                paciente = Paciente.objects.get(id=paciente_id)
                # Si el usuario no tiene nombre/apellido, tomarlos del paciente
                if not validated_data.get('first_name') and paciente.nombre:
                    validated_data['first_name'] = paciente.nombre
                if not validated_data.get('last_name') and paciente.apellido:
                    validated_data['last_name'] = paciente.apellido
                # Si el usuario no tiene email, tomarlo del paciente
                if not validated_data.get('email') and paciente.email:
                    validated_data['email'] = paciente.email
                # Si el usuario no tiene teléfono, tomarlo del paciente
                if not validated_data.get('telefono') and paciente.telefono:
                    validated_data['telefono'] = paciente.telefono
            
            # Crear usuario
            user = User.objects.create_user(**validated_data)
            
            # Asociar o crear médico si el rol es médico
            if rol == 'medico':
                if medico_id:
                    # Asociar con médico existente
                    medico = Medico.objects.get(id=medico_id)
                    medico.user = user
                    # Sincronizar nombres desde usuario hacia médico si el médico no los tiene
                    if not medico.nombre and user.first_name:
                        medico.nombre = user.first_name
                    if not medico.apellido and user.last_name:
                        medico.apellido = user.last_name
                    medico.save()
                elif medico_data:
                    # Crear nuevo médico
                    especialidad_id = medico_data.pop('especialidad_id', None)
                    matricula = medico_data.pop('matricula', None)
                    if not matricula:
                        raise serializers.ValidationError({
                            'medico_data': {'matricula': 'La matrícula es requerida para crear un médico.'}
                        })
                    
                    especialidad = None
                    if especialidad_id:
                        try:
                            especialidad = Especialidad.objects.get(id=especialidad_id)
                        except Especialidad.DoesNotExist:
                            raise serializers.ValidationError({
                                'medico_data': {'especialidad_id': 'La especialidad especificada no existe.'}
                            })
                    
                    # Sincronizar nombres desde usuario hacia médico
                    medico = Medico.objects.create(
                        user=user,
                        matricula=matricula,
                        especialidad=especialidad,
                        nombre=user.first_name or medico_data.pop('nombre', None),
                        apellido=user.last_name or medico_data.pop('apellido', None),
                        **medico_data
                    )
            
            # Asociar o crear paciente si el rol es paciente
            elif rol == 'paciente':
                if paciente_id:
                    # Asociar con paciente existente
                    paciente = Paciente.objects.get(id=paciente_id)
                    paciente.user = user
                    # Sincronizar nombres desde usuario hacia paciente si el paciente no los tiene
                    if not paciente.nombre and user.first_name:
                        paciente.nombre = user.first_name
                    if not paciente.apellido and user.last_name:
                        paciente.apellido = user.last_name
                    # Sincronizar email y teléfono desde usuario hacia paciente si el paciente no los tiene
                    if not paciente.email and user.email:
                        paciente.email = user.email
                    if not paciente.telefono and user.telefono:
                        paciente.telefono = user.telefono
                    paciente.save()
                elif paciente_data:
                    # Crear nuevo paciente
                    dni = paciente_data.pop('dni', None)
                    if not dni:
                        raise serializers.ValidationError({
                            'paciente_data': {'dni': 'El DNI es requerido para crear un paciente.'}
                        })
                    
                    # Verificar que el DNI no esté en uso
                    if Paciente.objects.filter(dni=dni).exists():
                        raise serializers.ValidationError({
                            'paciente_data': {'dni': 'Ya existe un paciente con este DNI.'}
                        })
                    
                    # Sincronizar datos desde usuario hacia paciente
                    paciente = Paciente.objects.create(
                        user=user,
                        dni=dni,
                        nombre=user.first_name or paciente_data.pop('nombre', None),
                        apellido=user.last_name or paciente_data.pop('apellido', None),
                        email=user.email or paciente_data.pop('email', None),
                        telefono=user.telefono or paciente_data.pop('telefono', None),
                        **paciente_data
                    )
            
            return user
    
    def update(self, instance, validated_data):
        """
        Actualizar un usuario existente
        """
        # Remover password_confirm del validated_data
        validated_data.pop('password_confirm', None)
        
        # Manejar la contraseña por separado
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)
        
        # Actualizar los demás campos
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer para el perfil de usuario
    """
    class Meta:
        model = UserProfile
        fields = '__all__'
        read_only_fields = ['user', 'fecha_creacion', 'fecha_actualizacion']


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer para cambiar contraseña
    """
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': 'Las contraseñas no coinciden.'
            })
        return attrs


class RefreshTokenSerializer(serializers.Serializer):
    """
    Serializer para refrescar tokens
    """
    refresh = serializers.CharField()
    
    def save(self, **kwargs):
        try:
            refresh_token = RefreshToken(self.validated_data['refresh'])
            return {
                'access': str(refresh_token.access_token),
                'refresh': str(refresh_token)
            }
        except Exception:
            raise serializers.ValidationError('Token de refresco inválido')


class UserListSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listar usuarios
    """
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'rol', 'is_active']


class UserDetailSerializer(serializers.ModelSerializer):
    """
    Serializer detallado para usuarios
    """
    medico = serializers.SerializerMethodField()
    paciente = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'rol', 'telefono', 'is_active', 'is_staff', 'is_superuser',
            'date_joined', 'last_login', 'medico', 'paciente'
        ]
    
    def get_medico(self, obj):
        """Obtener información del médico si existe"""
        try:
            if hasattr(obj, 'medico') and obj.medico:
                return {
                    'id': obj.medico.id,
                    'matricula': obj.medico.matricula,
                    'especialidad': {
                        'id': obj.medico.especialidad.id,
                        'nombre': obj.medico.especialidad.nombre
                    } if obj.medico.especialidad else None
                }
        except:
            pass
        return None
    
    def get_paciente(self, obj):
        """Obtener información del paciente si existe"""
        try:
            if hasattr(obj, 'paciente') and obj.paciente:
                return {
                    'id': obj.paciente.id,
                    'dni': obj.paciente.dni,
                    'fecha_nacimiento': obj.paciente.fecha_nacimiento,
                    'sexo': obj.paciente.sexo
                }
        except:
            pass
        return None


class PacienteRegistrationSerializer(serializers.Serializer):
    """
    Serializer para el auto-registro público de pacientes.
    Crea tanto el User como el Paciente asociado en una transacción atómica.
    
    IMPORTANTE: Este serializer FORZA que user.username == dni para permitir
    que los pacientes inicien sesión usando su DNI como nombre de usuario.
    
    Verificación Manual:
    - Después de registrar un paciente, verificar en Django Admin o DB que:
      User.username == Paciente.dni
    - El paciente debe poder iniciar sesión usando su DNI como username.
    """
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'},
        help_text='Contraseña del usuario'
    )
    nombre = serializers.CharField(max_length=100, required=True)
    apellido = serializers.CharField(max_length=100, required=True)
    dni = serializers.CharField(max_length=20, required=True)
    telefono = serializers.CharField(max_length=25, required=True, allow_blank=False)
    fecha_nacimiento = serializers.DateField(required=True)
    
    def validate_email(self, value: str) -> str:
        """
        Validar que el email sea único en el modelo User.
        IMPORTANTE: Si el email ya existe, el usuario debe iniciar sesión o usar otro email.
        No permitimos registro con email duplicado para evitar cuentas duplicadas.
        """
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "Este email ya está registrado. Si ya tienes cuenta, por favor inicia sesión. Si no, usa otro email."
            )
        return value
    
    def validate_dni(self, value: str) -> str:
        """
        Validar el DNI. 
        IMPORTANTE: Ya NO rechazamos pacientes existentes con este DNI, 
        porque implementamos lógica de VINCULACIÓN en el método create().
        Solo rechazamos si ya existe un User con username = DNI (ya registrado).
        """
        dni_clean = value.strip()  # Limpiar espacios
        
        # Verificar que no exista un usuario con username = DNI (CRÍTICO)
        # Si ya existe un User con este username, significa que ya está registrado
        if User.objects.filter(username=dni_clean).exists():
            raise serializers.ValidationError(
                "Este DNI ya está registrado. Por favor, inicia sesión con tu DNI y contraseña."
            )
        
        # NOTA: Ya NO rechazamos si existe un Paciente con este DNI,
        # porque en create() implementamos la lógica de vinculación
        
        return dni_clean
    
    def create(self, validated_data: dict) -> User:
        """
        Crear el User y vincular/crear el Paciente asociado en una transacción atómica.
        FORZA que user.username == dni para permitir login de pacientes con DNI.
        
        LÓGICA DE VINCULACIÓN:
        - Si existe un Paciente con este DNI:
          * Si ya tiene user asociado -> Error (ya registrado)
          * Si NO tiene user -> Vincular el nuevo user al paciente existente
        - Si NO existe un Paciente -> Crear nuevo User y nuevo Paciente
        
        Args:
            validated_data: Datos validados del serializer
            
        Returns:
            User: Usuario creado con rol='paciente' y username=dni
            
        Raises:
            serializers.ValidationError: Si falla la creación
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # 1. Extraer y limpiar datos
        dni = validated_data['dni'].strip()  # Limpiar espacios
        email = validated_data['email']
        password = validated_data['password']
        nombre = validated_data.get('nombre', '')
        apellido = validated_data.get('apellido', '')
        telefono = validated_data.get('telefono', '')
        fecha_nacimiento = validated_data.get('fecha_nacimiento')
        
        # LOG DE DEBUG
        logger.info(f"INTENTO REGISTRO: DNI={dni}, Email={email}")
        
        try:
            with transaction.atomic():
                # 2. Verificar si existe un Paciente con este DNI
                paciente_existente = Paciente.objects.filter(dni=dni).first()
                
                if paciente_existente:
                    # CASO 1: Existe un Paciente con este DNI
                    logger.info(f"PACIENTE EXISTENTE ENCONTRADO: DNI={dni}, ID={paciente_existente.id}")
                    
                    # Verificar si ya tiene un user asociado
                    if paciente_existente.user:
                        # Ya está registrado, no permitir duplicado
                        raise serializers.ValidationError(
                            "Este DNI ya está registrado como usuario. Por favor, inicia sesión o contacta al administrador."
                        )
                    
                    # El paciente existe pero NO tiene user -> VINCULAR
                    logger.info(f"VINCULANDO usuario nuevo al paciente existente ID={paciente_existente.id}")
                    
                    # Crear Usuario FORZANDO username = dni
                    user = User.objects.create_user(
                        username=dni,  # <--- PUNTO CRÍTICO: username = dni
                        email=email,
                        password=password,
                        first_name=nombre or paciente_existente.nombre or '',
                        last_name=apellido or paciente_existente.apellido or '',
                        telefono=telefono or paciente_existente.telefono or '',
                        rol='paciente',
                        is_active=True
                    )
                    
                    # Vincular el user al paciente existente
                    paciente_existente.user = user
                    
                    # Actualizar datos del paciente si están vacíos
                    if not paciente_existente.email:
                        paciente_existente.email = email
                    if not paciente_existente.nombre and nombre:
                        paciente_existente.nombre = nombre
                    if not paciente_existente.apellido and apellido:
                        paciente_existente.apellido = apellido
                    if not paciente_existente.telefono and telefono:
                        paciente_existente.telefono = telefono
                    if not paciente_existente.fecha_nacimiento and fecha_nacimiento:
                        paciente_existente.fecha_nacimiento = fecha_nacimiento
                    
                    paciente_existente.save()
                    
                    logger.info(f"EXITO VINCULACIÓN: Usuario {dni} vinculado al paciente existente. User.id={user.id}, Paciente.id={paciente_existente.id}")
                    
                else:
                    # CASO 2: NO existe un Paciente con este DNI -> Crear nuevo
                    logger.info(f"CREANDO NUEVO PACIENTE: DNI={dni}")
                    
                    # Crear Usuario FORZANDO username = dni
                    user = User.objects.create_user(
                        username=dni,  # <--- PUNTO CRÍTICO: username = dni
                        email=email,
                        password=password,
                        first_name=nombre,
                        last_name=apellido,
                        telefono=telefono,
                        rol='paciente',
                        is_active=True
                    )
                    
                    # Crear nuevo Perfil Paciente
                    paciente = Paciente.objects.create(
                        user=user,
                        dni=dni,
                        nombre=nombre,
                        apellido=apellido,
                        fecha_nacimiento=fecha_nacimiento,
                        telefono=telefono,
                        email=email
                    )
                    
                    logger.info(f"EXITO CREACIÓN: Usuario {dni} y Paciente creados. User.id={user.id}, Paciente.id={paciente.id}")
                
                return user
                
        except serializers.ValidationError:
            # Re-lanzar errores de validación sin modificar
            raise
        except Exception as e:
            logger.error(f"FALLO EN TRANSACCIÓN REGISTRO: {str(e)}", exc_info=True)
            # Si ocurre cualquier error, la transacción se revierte automáticamente
            raise serializers.ValidationError(
                f"Error al crear el registro: {str(e)}"
            )
