from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, UserProfile

class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer para el perfil de usuario"""
    edad = serializers.SerializerMethodField()
    
    class Meta:
        model = UserProfile
        fields = [
            'fecha_nacimiento', 'genero', 'direccion', 'ciudad', 'codigo_postal',
            'grupo_sanguineo', 'alergias', 'medicamentos_actuales',
            'contacto_emergencia_nombre', 'contacto_emergencia_telefono', 
            'contacto_emergencia_relacion', 'edad'
        ]
    
    def get_edad(self, obj):
        return obj.get_edad()

class UserSerializer(serializers.ModelSerializer):
    """Serializer para mostrar información del usuario"""
    profile = UserProfileSerializer(read_only=True)
    rol_display = serializers.CharField(source='get_rol_display', read_only=True)
    
    # Campos para perfiles específicos
    medico = serializers.SerializerMethodField()
    paciente = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'rol', 'rol_display',
            'telefono', 'email_verificado', 'telefono_verificado', 
            'fecha_registro', 'ultima_actividad', 'profile', 'medico', 'paciente'
        ]
        read_only_fields = ['id', 'fecha_registro', 'ultima_actividad']
    
    def get_medico(self, obj):
        """Obtener información del médico si el usuario es médico"""
        try:
            medico = obj.medico
            return {
                'id': medico.id,
                'matricula': medico.matricula,
                'especialidad': {
                    'id': medico.especialidad.id,
                    'nombre': medico.especialidad.nombre
                } if medico.especialidad else None
            }
        except Exception as e:
            print(f"Error en get_medico para usuario {obj.username}: {str(e)}")
            return None
    
    def get_paciente(self, obj):
        """Obtener información del paciente si el usuario es paciente"""
        try:
            paciente = obj.paciente
            return {
                'id': paciente.id,
                'dni': paciente.dni,
                'fecha_nacimiento': paciente.fecha_nacimiento,
                'sexo': paciente.sexo
            }
        except Exception as e:
            print(f"Error en get_paciente para usuario {obj.username}: {str(e)}")
            return None

class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear usuarios (registro de pacientes)"""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    profile = UserProfileSerializer(required=False)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm', 'first_name', 
            'last_name', 'telefono', 'profile'
        ]
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Las contraseñas no coinciden")
        return attrs
    
    def create(self, validated_data):
        # Remover password_confirm y profile
        validated_data.pop('password_confirm')
        profile_data = validated_data.pop('profile', None)
        
        # Crear usuario con rol de paciente por defecto
        validated_data['rol'] = 'paciente'
        user = User.objects.create_user(**validated_data)
        
        # Crear perfil si se proporciona
        if profile_data:
            UserProfile.objects.create(user=user, **profile_data)
        else:
            UserProfile.objects.create(user=user)
        
        return user

class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer para actualizar información del usuario"""
    profile = UserProfileSerializer(required=False)
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'telefono', 'profile'
        ]
    
    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', None)
        
        # Actualizar usuario
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Actualizar perfil si se proporciona
        if profile_data:
            profile = instance.profile
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()
        
        return instance

class LoginSerializer(serializers.Serializer):
    """Serializer para autenticación"""
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError('Credenciales inválidas')
            if not user.is_active:
                raise serializers.ValidationError('Usuario inactivo')
            attrs['user'] = user
        else:
            raise serializers.ValidationError('Debe proporcionar username y password')
        
        return attrs

class ChangePasswordSerializer(serializers.Serializer):
    """Serializer para cambiar contraseña"""
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("Las nuevas contraseñas no coinciden")
        return attrs
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Contraseña actual incorrecta')
        return value

class AdminUserCreateSerializer(serializers.ModelSerializer):
    """Serializer para que los administradores creen usuarios"""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    profile = UserProfileSerializer(required=False)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'first_name', 'last_name', 
            'rol', 'telefono', 'is_active', 'is_staff', 'profile'
        ]
    
    def create(self, validated_data):
        profile_data = validated_data.pop('profile', None)
        
        # Crear usuario
        user = User.objects.create_user(**validated_data)
        
        # Crear perfil si se proporciona
        if profile_data:
            UserProfile.objects.create(user=user, **profile_data)
        else:
            UserProfile.objects.create(user=user)
        
        return user
