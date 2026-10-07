from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from api.permissions import get_normalized_role
from usuarios.roles import ROLES_LIMS_OPERADOR

from .models import Profesional
from .serializers import ProfesionalLightSerializer, ProfesionalSerializer

_ROLES_ESCRITURA = frozenset({'admin', 'secretaria', *ROLES_LIMS_OPERADOR})


class CanWriteProfesional(IsAuthenticated):
    """Misma barra que médicos: lectura autenticada; escritura admin/secretaria/lab/bio."""

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        user = request.user
        if getattr(user, 'is_superuser', False):
            return True
        role = get_normalized_role(user)
        if role in _ROLES_ESCRITURA:
            return True
        if getattr(user, 'is_staff', False) and role not in ROLES_LIMS_OPERADOR:
            return True
        return False


class ProfesionalViewSet(viewsets.ModelViewSet):
    queryset = Profesional.objects.select_related('especialidad', 'user').all()
    serializer_class = ProfesionalSerializer
    permission_classes = [CanWriteProfesional]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['especialidad']
    search_fields = ['nombre', 'apellido', 'matricula']
    ordering_fields = ['apellido', 'nombre', 'matricula', 'fecha_registro']
    ordering = ['apellido', 'nombre']

    def get_serializer_class(self):
        if self.action == 'list':
            return ProfesionalLightSerializer
        return ProfesionalSerializer

    def destroy(self, request, *args, **kwargs):
        user = request.user
        if getattr(user, 'is_superuser', False):
            return super().destroy(request, *args, **kwargs)
        role = get_normalized_role(user)
        if role == 'admin' or (
            getattr(user, 'is_staff', False) and role not in ROLES_LIMS_OPERADOR
        ):
            return super().destroy(request, *args, **kwargs)
        raise PermissionDenied('No tiene permiso para eliminar profesionales.')
