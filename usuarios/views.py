from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .serializers import (
    UserSerializer, UserCreateSerializer, UserUpdateSerializer,
    LoginSerializer, ChangePasswordSerializer, AdminUserCreateSerializer
)
from .models import User

class IsAdminUser(permissions.BasePermission):
    """Permiso personalizado para usuarios administradores"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.es_admin

class IsSecretariaOrAdmin(permissions.BasePermission):
    """Permiso para secretarias y administradores"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (
            request.user.es_secretaria or request.user.es_admin
        )

class IsMedicoOrAdmin(permissions.BasePermission):
    """Permiso para médicos y administradores"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (
            request.user.es_medico or request.user.es_admin
        )

class RegisterView(APIView):
    """Vista para registro de pacientes"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = UserCreateSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Auto-login después del registro
            login(request, user)
            return Response({
                'message': 'Usuario registrado exitosamente',
                'user': UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    """Vista para login"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            login(request, user)
            return Response({
                'message': 'Login exitoso',
                'user': UserSerializer(user).data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(APIView):
    """Vista para logout"""
    def post(self, request):
        logout(request)
        return Response({'message': 'Logout exitoso'})

class UserProfileView(APIView):
    """Vista para obtener y actualizar perfil del usuario actual"""
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
    def put(self, request):
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'message': 'Perfil actualizado exitosamente',
                'user': UserSerializer(user).data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ChangePasswordView(APIView):
    """Vista para cambiar contraseña"""
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({'message': 'Contraseña cambiada exitosamente'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AdminUserListView(generics.ListCreateAPIView):
    """Vista para que administradores gestionen usuarios"""
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        return User.objects.all().select_related('profile')
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AdminUserCreateSerializer
        return UserSerializer

class AdminUserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Vista para que administradores gestionen usuarios específicos"""
    queryset = User.objects.all().select_related('profile')
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return AdminUserCreateSerializer
        return UserSerializer

@api_view(['GET'])
def current_user(request):
    """Obtener información del usuario actual"""
    if request.user.is_authenticated:
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    return Response({'error': 'No autenticado'}, status=status.HTTP_401_UNAUTHORIZED)



@api_view(['GET'])
@permission_classes([IsSecretariaOrAdmin])
def list_pacientes(request):
    """Listar pacientes (solo secretarias y administradores)"""
    pacientes = User.objects.filter(rol='paciente').select_related('profile')
    serializer = UserSerializer(pacientes, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsMedicoOrAdmin])
def list_medicos(request):
    """Listar médicos (solo médicos y administradores)"""
    medicos = User.objects.filter(rol='medico').select_related('profile')
    serializer = UserSerializer(medicos, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsSecretariaOrAdmin])
def list_secretarias(request):
    """Listar secretarias (solo administradores)"""
    if not request.user.es_admin:
        return Response({'error': 'Acceso denegado'}, status=status.HTTP_403_FORBIDDEN)
    
    secretarias = User.objects.filter(rol='secretaria').select_related('profile')
    serializer = UserSerializer(secretarias, many=True)
    return Response(serializer.data)
