"""ViewSets para la app ``historias_clinicas``.

Decisiones funcionales clave (rescate del bloque):

- ``HistoriaClinicaViewSet`` es ``ReadOnlyModelViewSet``: sin POST/PUT/DELETE
  por diseño.
- ``ConsultaViewSet`` es ``ModelViewSet`` pero **bloquea DELETE físico** vía
  ``destroy()`` → 405 ``MethodNotAllowed``. La consulta es un registro clínico
  cuya eliminación destruye trazabilidad. Para corregir errores se debe
  registrar una observación o, en última instancia, marcar/anotar.
- ``get_queryset`` accede a ``user.medico``/``user.paciente`` con manejo
  defensivo de ``DoesNotExist`` (al ser ``OneToOne`` inverso).
- Auditoría best-effort en ``perform_create``/``perform_update`` siguiendo
  el patrón usado en ``turnos`` y ``pacientes``: ``log_create`` /
  ``log_update`` envueltos en ``try/except`` para no romper el flujo.
- Sin ``AllowAny``.
"""
import logging

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.permissions import IsMedicoOrEnfermeriaOrAdmin, emr_staff_or_admin_global
from auditoria.audit_service import log_create, log_update
from auditoria.snapshot import safe_model_snapshot

from .models import Consulta, HistoriaClinica
from .serializers import (
    ConsultaCreateSerializer,
    ConsultaSerializer,
    HistoriaClinicaSerializer,
)

logger = logging.getLogger(__name__)


def _safe_audit(callable_, *args, **kwargs):
    """Wrapper best-effort: una falla de auditoría nunca debe romper el flujo."""
    try:
        callable_(*args, **kwargs)
    except Exception:  # pragma: no cover - auditoría es defensiva
        logger.exception(
            "Fallo silencioso en auditoría: %s", getattr(callable_, "__name__", "audit")
        )


def _resolve_user_medico(user):
    """Devuelve ``user.medico`` o ``None`` sin lanzar ``DoesNotExist``."""
    try:
        return user.medico
    except ObjectDoesNotExist:
        return None


def _resolve_user_paciente(user):
    """Devuelve ``user.paciente`` o ``None`` sin lanzar ``DoesNotExist``."""
    try:
        return user.paciente
    except ObjectDoesNotExist:
        return None


class HistoriaClinicaViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet de solo lectura para ``HistoriaClinica``.

    Solo permite buscar por ``paciente_id``. No expone POST/PUT/DELETE por
    diseño (al heredar de ``ReadOnlyModelViewSet``), de modo que no hace
    falta sobrescribir ``destroy``.
    """

    queryset = HistoriaClinica.objects.select_related('paciente').prefetch_related('consultas').all()
    serializer_class = HistoriaClinicaSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['paciente']

    def get_queryset(self):
        """Filtrado por rol según reglas de negocio.

        - Admin / staff: ven todo.
        - Médico: solo historias de pacientes con consultas suyas.
        - Paciente: solo su propia historia clínica.
        - Otros: queryset vacío.
        """
        queryset = super().get_queryset()
        user = self.request.user

        if emr_staff_or_admin_global(user):
            return queryset

        medico = _resolve_user_medico(user)
        if medico is not None:
            pacientes_ids = (
                Consulta.objects
                .filter(medico=medico)
                .values_list('historia_clinica__paciente_id', flat=True)
                .distinct()
            )
            return queryset.filter(paciente_id__in=pacientes_ids)

        paciente = _resolve_user_paciente(user)
        if paciente is not None:
            return queryset.filter(paciente=paciente)

        return queryset.none()

    @action(detail=True, methods=['get'], url_path='resumen')
    def resumen(self, request, pk=None):
        """Resumen JSON con últimas 5 consultas y diagnósticos asociados."""
        historia_clinica = self.get_object()

        ultimas_consultas = historia_clinica.consultas.order_by('-fecha_hora_consulta')[:5]
        consultas_data = ConsultaSerializer(ultimas_consultas, many=True).data

        diagnosticos_activos = []
        for consulta in ultimas_consultas:
            for diagnostico in consulta.diagnosticos.all():
                diagnosticos_activos.append({
                    'id': diagnostico.id,
                    'nombre': diagnostico.nombre_diagnostico,
                    'fecha': diagnostico.fecha_diagnostico.isoformat() if diagnostico.fecha_diagnostico else None,
                    'consulta_id': consulta.id,
                })

        return Response({
            'historia_clinica_id': historia_clinica.paciente_id,
            'paciente': historia_clinica.paciente.nombre_completo,
            'ultimas_consultas': consultas_data,
            'diagnosticos_activos': diagnosticos_activos,
            'total_consultas': historia_clinica.consultas.count(),
        })


class ConsultaViewSet(viewsets.ModelViewSet):
    """ViewSet para ``Consulta`` con DELETE físico bloqueado.

    Permite create/list/retrieve/update/partial_update bajo
    ``IsMedicoOrEnfermeriaOrAdmin``. El borrado físico está deshabilitado
    porque las consultas son registros clínicos.
    """

    queryset = (
        Consulta.objects
        .select_related(
            'historia_clinica',
            'historia_clinica__paciente',
            'medico',
            'turno',
        )
        .prefetch_related('diagnosticos', 'tratamientos', 'prescripciones')
        .all()
    )
    permission_classes = [IsMedicoOrEnfermeriaOrAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['historia_clinica', 'medico', 'turno']
    ordering = ['-fecha_hora_consulta']

    def get_serializer_class(self):
        if self.action == 'create':
            return ConsultaCreateSerializer
        return ConsultaSerializer

    def get_queryset(self):
        """Filtrado por rol.

        - Admin/staff: ven todo.
        - Rol ``admin``/``enfermeria``: ven todo.
        - Médico: solo sus consultas.
        - Paciente: solo consultas de su historia clínica.
        - Otros: vacío.
        """
        queryset = super().get_queryset()
        user = self.request.user

        # Filtro por historia_clinica_id es seguro y se aplica primero.
        historia_clinica_id = self.request.query_params.get('historia_clinica_id')
        if historia_clinica_id:
            try:
                queryset = queryset.filter(historia_clinica_id=int(historia_clinica_id))
            except (ValueError, TypeError):
                pass

        if emr_staff_or_admin_global(user):
            return queryset

        user_rol = (getattr(user, 'rol', '') or '').lower()
        if user_rol in {'admin', 'enfermeria'}:
            return queryset

        medico = _resolve_user_medico(user)
        if medico is not None:
            return queryset.filter(medico=medico)

        paciente = _resolve_user_paciente(user)
        if paciente is not None:
            return queryset.filter(historia_clinica__paciente=paciente)

        return queryset.none()

    def perform_create(self, serializer):
        """Crea la ``Consulta``, asegura ``HistoriaClinica`` y audita best-effort.

        El ``ConsultaCreateSerializer.create`` ya envuelve la persistencia en
        ``transaction.atomic``; aquí mantenemos la auditoría dentro de ese
        contexto agregando un atomic adicional para que ``log_create`` se
        agende vía ``transaction.on_commit`` en el mismo bloque.
        """
        with transaction.atomic():
            historia_clinica_obj = serializer.validated_data.get('historia_clinica')
            if historia_clinica_obj is not None:
                # Asegura existencia de la HC: si el front envió el id de un
                # paciente sin HC, la creamos al vuelo. ``get_or_create`` es
                # idempotente y no introduce condiciones de carrera porque
                # ``HistoriaClinica.paciente`` es PK del modelo.
                historia_clinica, _ = HistoriaClinica.objects.get_or_create(
                    paciente=historia_clinica_obj.paciente
                )
                instance = serializer.save(historia_clinica=historia_clinica)
            else:
                instance = serializer.save()

            _safe_audit(
                log_create,
                actor=self.request.user,
                entity=instance,
                module="historias_clinicas",
                metadata={"view": "ConsultaViewSet.perform_create"},
            )

    def perform_update(self, serializer):
        """Actualiza la ``Consulta`` y audita best-effort el cambio.

        Captura snapshot ``before`` antes del save; el ``log_update`` queda
        dentro del mismo ``transaction.atomic`` para que el on_commit de
        auditoría se persista sólo si la actualización commitea.
        """
        before = safe_model_snapshot(self.get_object())
        with transaction.atomic():
            instance = serializer.save()
            _safe_audit(
                log_update,
                actor=self.request.user,
                entity=instance,
                before=before,
                module="historias_clinicas",
                metadata={"view": "ConsultaViewSet.perform_update"},
            )

    def destroy(self, request, *args, **kwargs):
        """Bloquea el DELETE físico de consultas.

        Las consultas son registros clínicos: su eliminación destruye
        trazabilidad y el linaje de diagnósticos/prescripciones/tratamientos
        asociados (todos en CASCADE). Para corregir información debe usarse
        update; para anular, registrar una observación clínica.
        """
        raise MethodNotAllowed(
            "DELETE",
            detail=(
                "El borrado físico de consultas no está permitido. "
                "Edite la consulta o registre una observación correctiva."
            ),
        )
