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
        - Admin / secretaría / enfermería / operadores LIMS: todos los médicos
        - Médico: solo su propio perfil (evita listar colegas en selects genéricos)
        - Paciente u otros autenticados: todos (p. ej. elegir en turnos / orden LIMS)

        Optimización: en listados se hace defer de campos pesados.
        """
        queryset = super().get_queryset()
        user = self.request.user
        user_rol = (getattr(user, "rol", None) or "").lower()

        roles_ven_todos = {
            "admin",
            "secretaria",
            "enfermeria",
            "laboratorio",
            "bioquimico",
        }

        medico = getattr(user, "medico", None)
        paciente = getattr(user, "paciente", None)

        if (
            user.is_superuser
            or user_rol in roles_ven_todos
            # Staff administrativo (no operadores LIMS con is_staff)
            or (user.is_staff and user_rol not in {"laboratorio", "bioquimico", "medico"})
        ):
            base_queryset = queryset
        elif medico is not None:
            base_queryset = queryset.filter(id=medico.id)
        elif paciente is not None:
            base_queryset = queryset
        else:
            base_queryset = queryset

        if self.action == "list":
            base_queryset = base_queryset.defer("areas_interes_ia")

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
