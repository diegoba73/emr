"""
Tests para los modelos de la app usuarios.
"""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date
from usuarios.models import User, UserProfile, Secretaria

User = get_user_model()


@pytest.mark.django_db
class TestUserModel:
    """Tests para el modelo User."""
    
    def test_crear_usuario_medico_y_verificar_propiedades(self):
        """
        Test 1 (Happy Path): Crear un usuario 'medico' y verificar que:
        - es_medico es True
        - Se creó su UserProfile automático (signal)
        """
        # Crear usuario médico
        usuario = User.objects.create_user(
            username='dr_garcia',
            email='dr.garcia@example.com',
            password='testpass123',
            first_name='Juan',
            last_name='García',
            rol='medico'
        )
        
        # Verificar que el rol es médico
        assert usuario.rol == 'medico'
        
        # Verificar propiedad es_medico
        assert usuario.es_medico is True
        assert usuario.es_paciente is False
        assert usuario.es_secretaria is False
        
        # Verificar que se creó el UserProfile automáticamente (signal)
        assert hasattr(usuario, 'profile')
        assert usuario.profile is not None
        assert isinstance(usuario.profile, UserProfile)
        assert usuario.profile.user == usuario
    
    def test_crear_usuario_sin_rol_debe_usar_default_paciente(self):
        """
        Test 2 (Edge Case): Crear usuario sin rol (debe usar default 'paciente').
        """
        # Crear usuario sin especificar rol
        usuario = User.objects.create_user(
            username='paciente_test',
            email='paciente@example.com',
            password='testpass123',
            first_name='María',
            last_name='López'
        )
        
        # Verificar que el rol por defecto es 'paciente'
        assert usuario.rol == 'paciente'
        assert usuario.es_paciente is True
        assert usuario.es_medico is False
        
        # Verificar que también se creó el UserProfile
        assert hasattr(usuario, 'profile')
        assert usuario.profile is not None
    
    def test_userprofile_get_edad_maneja_fecha_nacimiento_nula(self):
        """
        Test 3 (Validation): Verificar que el método get_edad del perfil
        maneje fecha_nacimiento nula sin romper (retornar None).
        """
        # Crear usuario
        usuario = User.objects.create_user(
            username='test_edad',
            email='test@example.com',
            password='testpass123',
            rol='paciente'
        )
        
        # Obtener el perfil (debe existir por la señal)
        perfil = usuario.profile
        
        # Verificar que fecha_nacimiento es None inicialmente
        assert perfil.fecha_nacimiento is None
        
        # Verificar que get_edad retorna None cuando fecha_nacimiento es None
        edad = perfil.get_edad()
        assert edad is None
        
        # Fecha exactamente 30 años atrás (calendario), alineada con UserProfile.get_edad
        today = date.today()
        try:
            fecha_nacimiento = date(today.year - 30, today.month, today.day)
        except ValueError:
            # 29 feb en año no bisiesto → 28 feb
            fecha_nacimiento = date(today.year - 30, today.month, 28)
        perfil.fecha_nacimiento = fecha_nacimiento
        perfil.save()
        
        edad = perfil.get_edad()
        assert edad is not None
        assert edad == 30


@pytest.mark.django_db
class TestUserProfileModel:
    """Tests adicionales para UserProfile."""
    
    def test_userprofile_se_crea_automaticamente_con_signal(self):
        """Verificar que UserProfile se crea automáticamente al crear un User."""
        usuario = User.objects.create_user(
            username='test_auto_profile',
            email='auto@example.com',
            password='testpass123'
        )
        
        # Verificar que el perfil existe
        assert UserProfile.objects.filter(user=usuario).exists()
        assert usuario.profile is not None


@pytest.mark.django_db
class TestSecretariaModel:
    """Tests para el modelo Secretaria."""
    
    def test_crear_secretaria(self):
        """Test para crear una secretaria."""
        usuario = User.objects.create_user(
            username='secretaria_test',
            email='secretaria@example.com',
            password='testpass123',
            rol='secretaria'
        )
        
        secretaria = Secretaria.objects.create(
            user=usuario,
            legajo='SEC-001',
            sector='Recepción'
        )
        
        assert secretaria.user == usuario
        assert secretaria.legajo == 'SEC-001'
        assert secretaria.sector == 'Recepción'
        assert usuario.es_secretaria is True




