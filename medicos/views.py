"""
ViewSets para la app medicos.
"""
from datetime import date

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.permissions import get_normalized_role
from api.serializers import MedicoLightSerializer
from usuarios.roles import ROLES_LIMS_OPERADOR

from .models import Especialidad, Medico
from .serializers import EspecialidadSerializer, MedicoSerializer

_ROLES_ESCRITURA_MEDICO = frozenset(
    {
        "admin",
        "secretaria",
        *ROLES_LIMS_OPERADOR,
    }
)


class CanWriteMedico(IsAuthenticated):
    """Lectura autenticada; alta/edición para admin/secretaría/lab/bio (y staff EMR)."""

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        user = request.user
        if getattr(user, "is_superuser", False):
            return True
        role = get_normalized_role(user)
        if role in _ROLES_ESCRITURA_MEDICO:
            return True
        # Staff administrativo (no operadores LIMS que a veces tienen is_staff).
        if getattr(user, "is_staff", False) and role not in ROLES_LIMS_OPERADOR:
            return True
        return False


class MedicoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar médicos.

    Permisos:
    - Lectura (list, retrieve): autenticados
    - Create/update: admin, secretaría, laboratorio, bioquímico (+ staff EMR)
    - Destroy: solo admin / superuser / staff EMR (no lab/bio)
    """

    queryset = Medico.objects.select_related("especialidad", "user").all()
    serializer_class = MedicoSerializer
    permission_classes = [CanWriteMedico]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["especialidad"]
    search_fields = ["nombre", "apellido", "matricula"]
    ordering_fields = ["apellido", "nombre", "matricula", "fecha_registro"]
    ordering = ["apellido", "nombre"]

    @action(detail=True, methods=["get"])
    def slots(self, request, pk=None):
        from .agenda import slots_disponibles

        medico = self.get_object()
        try:
            fecha = date.fromisoformat(request.query_params.get("fecha", ""))
        except ValueError:
            raise ValidationError("Indique una fecha válida (AAAA-MM-DD).") from None
        tipo = request.query_params.get("tipo", "CONSULTA")
        if tipo not in ("CONSULTA", "ESTUDIO"):
            raise ValidationError("Tipo de atención inválido.")
        return Response(
            {
                "fecha": fecha.isoformat(),
                "medico_id": medico.pk,
                "slots": list(slots_disponibles(medico, fecha, tipo)),
            }
        )

    def get_serializer_class(self):
        if self.action == "list":
            return MedicoLightSerializer
        return MedicoSerializer

    def destroy(self, request, *args, **kwargs):
        user = request.user
        if getattr(user, "is_superuser", False):
            return super().destroy(request, *args, **kwargs)
        role = get_normalized_role(user)
        if role == "admin" or (
            getattr(user, "is_staff", False) and role not in ROLES_LIMS_OPERADOR
        ):
            return super().destroy(request, *args, **kwargs)
        raise PermissionDenied("No tiene permiso para eliminar médicos.")

    def get_queryset(self):
        """
        Filtrado por rol según reglas de negocio.
        - Admin / secretaría / enfermería / operadores LIMS: todos los médicos
        - Médico: solo su propio perfil (evita listar colegas en selects genéricos)
        - Paciente u otros autenticados: todos (p. ej. elegir en turnos / orden LIMS)
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
    """ViewSet de solo lectura para especialidades."""

    queryset = Especialidad.objects.all()
    serializer_class = EspecialidadSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["nombre", "descripcion"]
    ordering = ["nombre"]
