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
            'sedes': list(getattr(self.user, 'sedes', None) or []),
            'is_active': self.user.is_active,
            'is_staff': self.user.is_staff,
            'is_superuser': self.user.is_superuser,
        }
        
        return data


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer para la gestión de usuarios por administradores.

    **Política de hardening (anti privilege-escalation):**

    - ``is_superuser``, ``is_staff`` y ``rol='admin'`` solo pueden ser asignados
      o modificados por un usuario que ya es ``superuser``.
    - Un staff regular (``is_staff=True`` pero no superuser) puede crear/editar
      usuarios no privilegiados (roles ``paciente``/``medico``/``secretaria``/
      ``enfermeria``/``laboratorio``) pero NO escalar privilegios propios ni
      ajenos.
    - El password es ``write_only`` y se valida con ``validate_password``.
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
            'rol', 'telefono', 'sedes', 'is_active', 'is_staff', 'is_superuser',
            'password', 'password_confirm', 'date_joined', 'last_login',
            'medico_id', 'paciente_id', 'medico_data', 'paciente_data'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']
        extra_kwargs = {
            'password': {'write_only': True, 'required': False},
            'password_confirm': {'write_only': True, 'required': False},
        }

    # ------------------------------------------------------------------
    # Helpers internos (anti privilege-escalation)
    # ------------------------------------------------------------------
    def _request_user(self):
        """Devuelve el ``request.user`` del context, o ``None`` si no aplica.

        Cuando el serializer se invoca desde un test/script sin request,
        ``context['request']`` puede no existir. En ese caso devolvemos
        ``None`` y los validadores de privilegio bloquean por defecto
        cualquier intento de escalada (modo seguro).
        """
        request = self.context.get('request') if hasattr(self, 'context') else None
        return getattr(request, 'user', None)

    def _is_actor_superuser(self) -> bool:
        actor = self._request_user()
        return bool(actor and getattr(actor, 'is_authenticated', False) and getattr(actor, 'is_superuser', False))

    def validate_sedes(self, value):
        from usuarios.sedes import SEDES, normalize_sedes

        if value is None:
            return []
        if not isinstance(value, (list, tuple)):
            raise serializers.ValidationError('Debe ser una lista de sedes.')
        bad = [s for s in value if str(s).strip().upper() not in SEDES]
        if bad:
            raise serializers.ValidationError(f'Sedes inválidas: {bad}. Use CEHTA y/o ICPL.')
        return normalize_sedes(value)

    def _value_changes(self, attrs: dict, field: str, target_value) -> bool:
        """``True`` si el set explícito de ``field`` cambia respecto a la instancia.

        Para creación (``self.instance is None``) considera "cambio" cualquier
        valor truthy distinto del default seguro. Para edición, compara con
        el valor actual de la instancia.
        """
        if field not in attrs:
            return False
        new_value = attrs[field]
        if self.instance is None:
            # Creación: marcar como escalada si se intenta True (booleans) o
            # 'admin' (rol). El default seguro se asume falsy/no-admin.
            if isinstance(target_value, bool):
                return bool(new_value) is True
            return new_value == target_value
        current = getattr(self.instance, field, None)
        return new_value != current and (
            (isinstance(target_value, bool) and bool(new_value) is True) or
            new_value == target_value
        )

    # ------------------------------------------------------------------
    # Validators contextuales (require superuser)
    # ------------------------------------------------------------------
    def validate(self, attrs):
        """
        Validación personalizada para el serializer
        """
        # ----- Anti privilege-escalation -----
        # Solo un superuser puede crear o promover otro superuser, otorgar
        # ``is_staff`` o asignar ``rol='admin'``. Esto se verifica antes de
        # cualquier otra validación para que un actor no privilegiado reciba
        # un 400 explícito y nunca llegue a persistir.
        actor_is_superuser = self._is_actor_superuser()

        if not actor_is_superuser:
            if self._value_changes(attrs, 'is_superuser', True):
                raise serializers.ValidationError({
                    'is_superuser': 'Solo un superuser puede asignar este flag.'
                })
            if self._value_changes(attrs, 'is_staff', True):
                raise serializers.ValidationError({
                    'is_staff': 'Solo un superuser puede asignar este flag.'
                })
            if self._value_changes(attrs, 'rol', 'admin'):
                raise serializers.ValidationError({
                    'rol': "Solo un superuser puede asignar el rol 'admin'."
                })

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
                if paciente_data:
                    pd_errors = {}
                    dni = (paciente_data.get('dni') or '').strip() if isinstance(paciente_data.get('dni'), str) else paciente_data.get('dni')
                    if not dni:
                        pd_errors['dni'] = 'El DNI es obligatorio al crear un paciente.'
                    fecha_nac = paciente_data.get('fecha_nacimiento')
                    if not fecha_nac:
                        pd_errors['fecha_nacimiento'] = (
                            'La fecha de nacimiento es obligatoria al crear un paciente.'
                        )
                    obra = paciente_data.get('obra_social')
                    if obra is None or (isinstance(obra, str) and not obra.strip()):
                        pd_errors['obra_social'] = (
                            'La obra social es obligatoria al crear un paciente.'
                        )
                    nombre = (
                        (attrs.get('first_name') or '').strip()
                        or (str(paciente_data.get('nombre') or '').strip())
                    )
                    apellido = (
                        (attrs.get('last_name') or '').strip()
                        or (str(paciente_data.get('apellido') or '').strip())
                    )
                    if not nombre:
                        pd_errors['nombre'] = (
                            'El nombre es obligatorio (nombre del usuario o paciente_data.nombre).'
                        )
                    if not apellido:
                        pd_errors['apellido'] = (
                            'El apellido es obligatorio (apellido del usuario o paciente_data.apellido).'
                        )
                    if pd_errors:
                        raise serializers.ValidationError({'paciente_data': pd_errors})
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
    Serializer simplificado para listar usuarios.

    Incluye ``sedes`` / ``telefono`` / ``is_staff`` porque la UI de gestión
    edita desde el listado (sin retrieve previo); omitirlos hacía que al
    guardar se enviaran defaults vacíos y se borrara la asignación.
    """
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'rol', 'telefono', 'sedes', 'is_active', 'is_staff', 'is_superuser',
        ]


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
            'rol', 'telefono', 'sedes', 'is_active', 'is_staff', 'is_superuser',
            'date_joined', 'last_login', 'medico', 'paciente'
        ]
    
    def get_medico(self, obj):
        """Obtener información del médico si existe"""
        try:
            if hasattr(obj, 'medico') and obj.medico:
                return {
                    'id': obj.medico.id,
                    'matricula': obj.medico.matricula,
                    'nombre': obj.medico.nombre,
                    'apellido': obj.medico.apellido,
                    'ambito_atencion': obj.medico.ambito_atencion,
                    'duracion_slot_min': obj.medico.duracion_slot_min,
                    'especialidad': {
                        'id': obj.medico.especialidad.id,
                        'nombre': obj.medico.especialidad.nombre
                    } if obj.medico.especialidad else None
                }
        except Exception:
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
    obra_social = serializers.CharField(max_length=100, required=True, allow_blank=False)

    def validate_obra_social(self, value: str) -> str:
        text = (value or '').strip()
        if not text:
            raise serializers.ValidationError(
                'La obra social es obligatoria al crear un paciente.'
            )
        return text.upper()

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
    
    # Mensaje neutro: no revelar si ya existe ficha clínica u otra cuenta.
    MSG_DNI_NO_AUTO_VINCULA = (
        'No pudimos completar el registro con esos datos. '
        'Si ya tenés ficha en el centro, acercate a secretaría para activar tu acceso al portal.'
    )

    def validate_dni(self, value: str) -> str:
        """Rechaza DNI ya usado en User o Paciente sin auto-vincular fichas existentes."""
        dni_clean = (value or '').strip()
        if not dni_clean:
            raise serializers.ValidationError('El DNI es obligatorio.')

        # Conflicto de cuenta o ficha: misma respuesta genérica (sin enumerar).
        if User.objects.filter(username=dni_clean).exists() or Paciente.objects.filter(dni=dni_clean).exists():
            raise serializers.ValidationError(self.MSG_DNI_NO_AUTO_VINCULA)

        return dni_clean

    def create(self, validated_data: dict) -> User:
        """
        Alta pública atómica de User + Paciente nuevos.
        No vincula fichas clínicas preexistentes (eso lo hace personal autorizado).
        """
        import logging

        from django.db import IntegrityError

        logger = logging.getLogger(__name__)

        dni = validated_data['dni'].strip()
        email = validated_data['email']
        password = validated_data['password']
        nombre = validated_data.get('nombre', '')
        apellido = validated_data.get('apellido', '')
        telefono = validated_data.get('telefono', '')
        fecha_nacimiento = validated_data.get('fecha_nacimiento')
        obra_social = validated_data.get('obra_social', '')

        try:
            with transaction.atomic():
                # Re-chequear dentro de la TX (carrera concurrente del mismo DNI).
                if (
                    User.objects.select_for_update().filter(username=dni).exists()
                    or Paciente.objects.select_for_update().filter(dni=dni).exists()
                ):
                    raise serializers.ValidationError({'dni': self.MSG_DNI_NO_AUTO_VINCULA})

                user = User.objects.create_user(
                    username=dni,
                    email=email,
                    password=password,
                    first_name=nombre,
                    last_name=apellido,
                    telefono=telefono,
                    rol='paciente',
                    is_active=True,
                )
                Paciente.objects.create(
                    user=user,
                    dni=dni,
                    nombre=nombre,
                    apellido=apellido,
                    fecha_nacimiento=fecha_nacimiento,
                    telefono=telefono,
                    email=email,
                    obra_social=obra_social,
                )
                return user
        except serializers.ValidationError:
            raise
        except IntegrityError:
            logger.warning('Registro público: IntegrityError (posible DNI concurrente)')
            raise serializers.ValidationError({'dni': self.MSG_DNI_NO_AUTO_VINCULA})
        except Exception as e:
            logger.exception('Fallo en registro público de paciente')
            raise serializers.ValidationError(
                'No se pudo completar el registro. Intentá nuevamente más tarde.'
            ) from e
