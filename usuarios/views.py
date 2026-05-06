from rest_framework import viewsets, status, permissions, generics, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction, models
from django.conf import settings
import logging
from .models import UserProfile
from .serializers import (
    UserSerializer, UserListSerializer, UserDetailSerializer,
    CustomTokenObtainPairSerializer, ChangePasswordSerializer,
    RefreshTokenSerializer, PacienteRegistrationSerializer
)

User = get_user_model()


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Vista personalizada para obtener tokens JWT
    """
    serializer_class = CustomTokenObtainPairSerializer


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet para la gestión de usuarios por administradores
    """
    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    pagination_class = None  # Deshabilitar paginación para obtener todos los usuarios
    
    def get_serializer_class(self):
        if self.action == 'list':
            return UserListSerializer
        elif self.action == 'retrieve':
            return UserDetailSerializer
        return UserSerializer
    
    def get_queryset(self):
        """
        Filtrar usuarios según el rol del administrador
        """
        if self.request.user.is_superuser:
            return User.objects.all()
        else:
            # Administradores regulares solo pueden ver usuarios no-admin
            return User.objects.filter(is_superuser=False)
    
    @action(detail=True, methods=['post'])
    def change_password(self, request, pk=None):
        """
        Cambiar contraseña de un usuario
        """
        user = self.get_object()
        serializer = ChangePasswordSerializer(data=request.data)
        
        if serializer.is_valid():
            if user.check_password(serializer.validated_data['old_password']):
                user.set_password(serializer.validated_data['new_password'])
                user.save()
                return Response({'message': 'Contraseña actualizada correctamente'})
            else:
                return Response(
                    {'error': 'La contraseña actual es incorrecta'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """
        Activar un usuario
        """
        user = self.get_object()
        user.is_active = True
        user.save()
        return Response({'message': 'Usuario activado correctamente'})
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """
        Desactivar un usuario
        """
        user = self.get_object()
        user.is_active = False
        user.save()
        return Response({'message': 'Usuario desactivado correctamente'})
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Estadísticas de usuarios
        """
        stats = {
            'total_users': User.objects.count(),
            'active_users': User.objects.filter(is_active=True).count(),
            'inactive_users': User.objects.filter(is_active=False).count(),
            'by_role': {}
        }
        
        for role, _ in User.ROL_CHOICES:
            stats['by_role'][role] = User.objects.filter(rol=role).count()
        
        return Response(stats)
    
    @action(detail=False, methods=['post'])
    def bulk_activate(self, request):
        """
        Activar múltiples usuarios
        """
        user_ids = request.data.get('user_ids', [])
        User.objects.filter(id__in=user_ids).update(is_active=True)
        return Response({'message': f'{len(user_ids)} usuarios activados'})
    
    @action(detail=False, methods=['post'])
    def bulk_deactivate(self, request):
        """
        Desactivar múltiples usuarios
        """
        user_ids = request.data.get('user_ids', [])
        User.objects.filter(id__in=user_ids).update(is_active=False)
        return Response({'message': f'{len(user_ids)} usuarios desactivados'})


class UserProfileViewSet(viewsets.ModelViewSet):
    """
    ViewSet para la gestión de perfiles de usuario
    """
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    
    def get_queryset(self):
        """
        Los usuarios pueden ver su propio perfil, los staff pueden ver todos
        """
        if self.request.user.is_staff:
            return UserProfile.objects.all()
        else:
            return UserProfile.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        """
        Asignar el usuario actual al perfil
        """
        serializer.save(user=self.request.user)


class AuthViewSet(viewsets.ViewSet):
    """
    ViewSet para operaciones de autenticación
    """
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    
    @action(detail=False, methods=['post'])
    def logout(self, request):
        """
        Cerrar sesión (invalidar refresh token)
        """
        try:
            refresh_token = request.data.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({'message': 'Sesión cerrada correctamente'})
        except Exception:
            return Response(
                {'error': 'Error al cerrar sesión'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """
        Obtener información del usuario actual
        """
        serializer = UserDetailSerializer(request.user)
        return Response(serializer.data)


class PacienteRegisterView(generics.CreateAPIView):
    """
    Vista pública para el auto-registro de pacientes.
    Permite que los pacientes se registren sin autenticación previa.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = PacienteRegistrationSerializer
    logger = logging.getLogger(__name__)
    
    def create(self, request, *args, **kwargs):
        """
        Crear un nuevo paciente con su usuario asociado.
        
        Args:
            request: Request HTTP con los datos del paciente
            
        Returns:
            Response: Respuesta con el resultado del registro
        """
        # Log de solicitud recibida (sin password)
        data_log = {k: v for k, v in request.data.items() if k != 'password'}
        self.logger.info(f"Registro de paciente solicitado. Datos recibidos: {data_log}")
        
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            
            self.logger.info(f"Paciente registrado exitosamente. User ID: {user.id}, Email: {user.email}")
            
            return Response(
                {
                    'message': 'Registro exitoso. Ya puedes iniciar sesión.',
                    'user_id': user.id,
                    'email': user.email
                },
                status=status.HTTP_201_CREATED
            )
            
        except serializers.ValidationError as e:
            self.logger.warning(f"Error de validación en registro: {e.detail}")
            return Response(
                {'error': 'Error de validación', 'details': e.detail},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            self.logger.error(
                f"Error inesperado durante el registro de paciente: {str(e)}",
                exc_info=True
            )
            return Response(
                {
                    'error': 'Error interno del servidor. Por favor, intenta nuevamente más tarde.',
                    'details': str(e) if settings.DEBUG else None
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
