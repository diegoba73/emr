"""
ViewSets para la app medicos.
"""
from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import Medico, Especialidad
from .serializers import MedicoSerializer, EspecialidadSerializer
from api.serializers import MedicoLightSerializer


class IsAdminOrReadOnly(IsAuthenticated):
    """
    Permiso personalizado: Solo Admin/Staff puede escribir,
    todos los autenticados pueden leer.
    """
    def has_permission(self, request, view):
        # Lectura: todos los autenticados
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return super().has_permission(request, view)
        
        # Escritura: solo staff
        return request.user.is_authenticated and request.user.is_staff


class MedicoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar médicos.
    
    Permisos:
    - Lectura (list, retrieve): Todos los autenticados
    - Escritura (create, update, destroy): Solo Admin/Secretaria (is_staff)
    """
    queryset = Medico.objects.select_related('especialidad', 'user').all()
    serializer_class = MedicoSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['especialidad']
    search_fields = ['nombre', 'apellido', 'matricula']
    ordering_fields = ['apellido', 'nombre', 'matricula', 'fecha_registro']
    ordering = ['apellido', 'nombre']
    
    def get_serializer_class(self):
        """
        Usar serializer ligero para listados.
        Usar serializer completo para retrieve, create, update.
        """
        if self.action == 'list':
            return MedicoLightSerializer
        return MedicoSerializer
    
    def get_queryset(self):
        """
        Filtrado por rol según reglas de negocio.
        - Admin/Secretaria/Enfermería: Todos los médicos
        - Médico: Solo su propio perfil
        - Paciente: Todos los médicos (para elegir en turnos)
        
        Optimización: Para listados, usa defer() para excluir campos pesados.
        """
        queryset = super().get_queryset()
        user = self.request.user
        
        # Normalizar rol a minúsculas para comparación
        user_rol = (user.rol or '').lower()
        
        # Superusuarios, staff, admin, secretaria y enfermería ven todo
        if user.is_superuser or user.is_staff or user_rol in ['admin', 'secretaria', 'enfermeria']:
            base_queryset = queryset
        # Médico: solo su propio perfil
        elif hasattr(user, 'medico') and user.medico:
            base_queryset = queryset.filter(id=user.medico.id)
        # Paciente: puede ver todos los médicos (para elegir en turnos)
        elif hasattr(user, 'paciente') and user.paciente:
            base_queryset = queryset
        else:
            # Por defecto, todos los autenticados pueden ver
            base_queryset = queryset
        
        # Optimización: Para listados, excluir campos pesados
        if self.action == 'list':
            base_queryset = base_queryset.defer(
                'areas_interes_ia'  # Campo de texto largo
            )
        
        return base_queryset


class EspecialidadViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet de solo lectura para especialidades.
    """
    queryset = Especialidad.objects.all()
    serializer_class = EspecialidadSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nombre', 'descripcion']
    ordering = ['nombre']
