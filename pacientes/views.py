"""ViewSets para la app ``pacientes``.

Reglas de negocio aplicadas:

- ``Paciente`` es la fuente de verdad de los datos personales del paciente.
- La ficha es información sensible: el listado y la búsqueda están filtrados
  por rol y nunca relajan permisos vía query params.
- DELETE físico está bloqueado en este viewset; un futuro bloque introducirá
  soft-delete con auditoría dedicada.
- Las altas y modificaciones quedan auditadas vía ``auditoria.audit_service``
  cuando el módulo está disponible (best-effort, no bloquea la operación si
  falla la auditoría; cubierto por tests en ``pacientes/tests/test_audit.py``).
"""
import logging

from django.db.models import Case, IntegerField, Q, When
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Paciente
from .serializers import PacienteLightSerializer, PacienteSerializer

logger = logging.getLogger(__name__)


try:  # Auditoría opcional: el viewset no debe romperse si el módulo falta.
    from auditoria.audit_service import log_create, log_update
    from auditoria.snapshot import safe_model_snapshot
except Exception:  # pragma: no cover - defensa por si la app no está cargada
    log_create = None
    log_update = None

    def safe_model_snapshot(_instance):  # type: ignore[misc]
        return None


_AUDIT_AVAILABLE = log_create is not None and log_update is not None

from usuarios.roles import ROLES_LECTURA_OPERATIVA

_ROLES_LECTURA_GLOBAL = frozenset({"admin", "secretaria", "enfermeria"})


def _user_rol(user) -> str:
    return (getattr(user, "rol", "") or "").lower()


def _user_tiene_lectura_global(user) -> bool:
    if getattr(user, "is_superuser", False):
        return True
    rol = _user_rol(user)
    if rol in ROLES_LECTURA_OPERATIVA:
        return True
    if getattr(user, "is_staff", False):
        return True
    return rol in _ROLES_LECTURA_GLOBAL


class PacienteViewSet(viewsets.ModelViewSet):
    """CRUD de pacientes con filtros estrictos por rol.

    - Admin / staff / secretaría / enfermería / laboratorio / profesionales de estudio: ven todos.
    - Médico: solo pacientes con los que tenga turnos o consultas.
      ``?all=true`` está deshabilitado por privacidad.
    - Paciente: solo su propia ficha.
    - Cualquier otro rol: queryset vacío.
    """

    queryset = Paciente.objects.select_related(
        "user", "creado_por", "modificado_por"
    ).all()
    serializer_class = PacienteSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["nombre", "apellido", "dni"]
    ordering_fields = ["apellido", "nombre", "dni", "fecha_registro"]
    ordering = ["apellido", "nombre"]

    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    def get_serializer_class(self):
        if self.action in ("list", "buscar"):
            return PacienteLightSerializer
        return PacienteSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        if _user_tiene_lectura_global(user):
            base_queryset = queryset
        elif getattr(user, "medico", None):
            base_queryset = self._queryset_para_medico(queryset, user)
        elif getattr(user, "paciente", None):
            base_queryset = queryset.filter(id=user.paciente.id)
        else:
            return queryset.none()

        if self.action in ("list", "buscar"):
            base_queryset = base_queryset.defer(
                "antecedentes_personales",
                "antecedentes_familiares",
                "observaciones",
            )

        return base_queryset

    @staticmethod
    def _queryset_para_medico(queryset, user):
        """Pacientes vinculados al médico vía turnos o consultas.

        Imports diferidos: ``turnos`` e ``historias_clinicas`` no son
        prerequisitos a nivel de módulo y pueden estar en distintos estados de
        rescate. Si fallan, se devuelve queryset vacío en lugar de propagar.
        """
        pacientes_ids = set()
        try:
            from turnos.models import Turno

            pacientes_ids.update(
                Turno.objects.filter(medico=user.medico).values_list(
                    "paciente_id", flat=True
                )
            )
        except Exception:
            logger.exception(
                "PacienteViewSet: no se pudieron resolver turnos para el médico %s",
                user.id,
            )
        try:
            from historias_clinicas.models import Consulta

            pacientes_ids.update(
                Consulta.objects.filter(medico=user.medico).values_list(
                    "historia_clinica__paciente_id", flat=True
                )
            )
        except Exception:
            logger.exception(
                "PacienteViewSet: no se pudieron resolver consultas para el médico %s",
                user.id,
            )

        pacientes_ids.discard(None)
        if not pacientes_ids:
            return queryset.none()
        return queryset.filter(id__in=pacientes_ids)

    def _queryset_busqueda_operativa(self, queryset):
        """Búsqueda por DNI/nombre para guardia, turnos y agenda (sin listado global).

        Médico/enfermería: pueden localizar cualquier paciente al atender (mín. 2 chars
        en ``buscar``), pero el listado completo sigue restringido por rol.
        """
        user = self.request.user
        if _user_tiene_lectura_global(user):
            return queryset
        if getattr(user, "medico", None) or _user_rol(user) == "enfermeria":
            return queryset
        return self.get_queryset()

    def _deny_operativo_solo_lectura(self) -> None:
        if _user_rol(self.request.user) in ROLES_LECTURA_OPERATIVA:
            raise PermissionDenied('Su rol solo tiene permiso de lectura sobre pacientes.')

    def _deny_paciente_mutations(self) -> None:
        if _user_rol(self.request.user) == 'paciente':
            raise PermissionDenied(
                'Los pacientes no pueden modificar datos demográficos.'
            )

    def update(self, request, *args, **kwargs):
        self._deny_operativo_solo_lectura()
        self._deny_paciente_mutations()
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        self._deny_operativo_solo_lectura()
        self._deny_paciente_mutations()
        return super().partial_update(request, *args, **kwargs)

    def perform_create(self, serializer):
        self._deny_operativo_solo_lectura()
        self._deny_paciente_mutations()
        instance = serializer.save(
            creado_por=self.request.user,
            modificado_por=self.request.user,
        )
        if _AUDIT_AVAILABLE:
            try:
                log_create(
                    actor=self.request.user,
                    entity=instance,
                    module="pacientes",
                    metadata={"view": "PacienteViewSet.perform_create"},
                )
            except Exception:
                logger.exception("Audit log_create failed for Paciente %s", instance.pk)

    def perform_update(self, serializer):
        self._deny_operativo_solo_lectura()
        self._deny_paciente_mutations()
        before = safe_model_snapshot(self.get_object()) if _AUDIT_AVAILABLE else None
        instance = serializer.save(modificado_por=self.request.user)
        if _AUDIT_AVAILABLE:
            try:
                log_update(
                    actor=self.request.user,
                    entity=instance,
                    before=before,
                    module="pacientes",
                    metadata={"view": "PacienteViewSet.perform_update"},
                )
            except Exception:
                logger.exception("Audit log_update failed for Paciente %s", instance.pk)

    def destroy(self, request, *args, **kwargs):
        """DELETE físico bloqueado para todos los roles.

        El borrado de pacientes implica pérdida de datos clínicos asociados y
        debe resolverse en un bloque dedicado de soft-delete con auditoría
        explícita y verificación de relaciones (turnos, consultas, etc.).
        """
        logger.warning(
            "Intento de DELETE físico de Paciente %s por usuario %s (bloqueado)",
            kwargs.get("pk"),
            getattr(request.user, "username", "anon"),
        )
        raise MethodNotAllowed(
            method="DELETE",
            detail=(
                "El borrado físico de pacientes está deshabilitado. "
                "Esta operación requiere soft-delete con auditoría."
            ),
        )

    @action(detail=False, methods=["get"], url_path="buscar")
    def buscar(self, request):
        """Búsqueda por DNI o nombre/apellido para guardia, turnos y agenda.

        Médico/enfermería: pueden localizar cualquier paciente (mín. 2 chars).
        El listado paginado completo sigue restringido por rol vía ``get_queryset()``.
        """
        q = request.query_params.get("q", "").strip()
        if not q:
            return Response(
                {"error": 'Parámetro "q" requerido'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        logger.info(
            "Búsqueda de paciente realizada por usuario %s: término=%r",
            getattr(request.user, "username", "anon"),
            q,
        )

        queryset = self._queryset_busqueda_operativa(super().get_queryset())

        try:
            int(q)
            es_numerico = True
        except ValueError:
            es_numerico = False

        if es_numerico:
            queryset = queryset.filter(dni__icontains=q)
        else:
            queryset = queryset.filter(
                Q(apellido__icontains=q) | Q(nombre__icontains=q)
            )

        queryset = queryset.annotate(
            orden_prioridad=Case(
                When(apellido__iexact=q, then=1),
                When(nombre__iexact=q, then=1),
                When(apellido__istartswith=q, then=2),
                When(nombre__istartswith=q, then=2),
                default=3,
                output_field=IntegerField(),
            )
        ).order_by("orden_prioridad", "apellido", "nombre")

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
