"""
ViewSets para la app turnos.
"""
import logging
from rest_framework import viewsets, filters, status
from rest_framework.exceptions import MethodNotAllowed, NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from datetime import datetime
from pacientes.services import ensure_paciente_linked_to_user

from medicos.models import Medico
from .models import Turno, Recurso, Atencion, ConsultaAmbulatoria
from . import turno_estado
from .services import AtencionService, BusinessLogicError
from .serializers import (
    TurnoSerializer,
    RecursoSerializer,
    ConsultaAmbulatoriaSerializer,
    consulta_ambulatoria_tiene_contenido,
)
# Usar el AtencionSerializer completo de api.serializers que incluye documentos
from api.serializers import AtencionSerializer
from api.permissions import (
    AtencionPermission,
    IsMedicoOrEnfermeriaOrAdmin,
    filter_atencion_queryset_for_user,
    get_normalized_role,
)
from auditoria.audit_service import log_create, log_delete, log_update
from auditoria.snapshot import safe_model_snapshot

logger = logging.getLogger(__name__)

_ROLES_AGENDA_GLOBAL_TURNOS = frozenset({'admin', 'secretaria', 'enfermeria'})


def _puede_ver_agenda_global_turnos(user) -> bool:
    """Agenda institucional de turnos: staff operativo, no médico estándar."""
    if getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False):
        return True
    return (getattr(user, 'rol', '') or '').lower() in _ROLES_AGENDA_GLOBAL_TURNOS


def _rol_usuario(user) -> str:
    return (getattr(user, 'rol', '') or '').lower()


def _puede_gestionar_turnos_global(user) -> bool:
    """Crear/modificar turnos en agenda institucional (no incluye enfermería en C5.8.1)."""
    if getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False):
        return True
    return _rol_usuario(user) in {'admin', 'secretaria'}


def _es_enfermeria(user) -> bool:
    return _rol_usuario(user) == 'enfermeria'


def _es_laboratorio(user) -> bool:
    return _rol_usuario(user) == 'laboratorio'


def _reject_foreign_medico_assignment(serializer, medico) -> None:
    if 'medico' not in serializer.validated_data:
        return
    nuevo = serializer.validated_data['medico']
    nuevo_id = nuevo.id if nuevo else None
    if nuevo_id != medico.id:
        raise PermissionDenied('No puede reasignar el turno a otro médico.')


def _reject_foreign_paciente_assignment(serializer, paciente) -> None:
    if 'paciente' not in serializer.validated_data:
        return
    nuevo = serializer.validated_data['paciente']
    nuevo_id = nuevo.id if nuevo else None
    if nuevo_id != paciente.id:
        raise PermissionDenied('No puede reasignar el turno a otro paciente.')


def _safe_audit(callable_, *args, **kwargs):
    """Best-effort wrapper para auditoría: no debe romper el request."""
    try:
        callable_(*args, **kwargs)
    except Exception:  # pragma: no cover - auditoría no debe afectar el flujo
        logger.exception("Fallo silencioso en auditoría: %s", getattr(callable_, "__name__", "audit"))


class RecursoViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar Recursos.

    - Lectura: cualquier usuario autenticado.
    - Escritura (POST/PUT/PATCH): solo administradores.
    - DELETE: NO realiza borrado físico. Hace baja lógica (``activo=False``)
      para preservar la trazabilidad de turnos asociados (``Turno.recurso``
      usa ``CASCADE`` a nivel de base de datos).
    """

    queryset = Recurso.objects.filter(activo=True)
    serializer_class = RecursoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['ubicacion', 'tipo_recurso', 'activo']
    search_fields = ['nombre']
    ordering = ['nombre']

    def get_permissions(self):
        """Solo Admin puede escribir o dar de baja; el resto, sólo leer."""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return super().get_permissions()

    def perform_create(self, serializer):
        with transaction.atomic():
            instance = serializer.save()
            _safe_audit(
                log_create,
                actor=self.request.user,
                entity=instance,
                module="turnos",
                metadata={"view": "RecursoViewSet.perform_create"},
            )

    def perform_update(self, serializer):
        before = safe_model_snapshot(self.get_object())
        with transaction.atomic():
            instance = serializer.save()
            _safe_audit(
                log_update,
                actor=self.request.user,
                entity=instance,
                before=before,
                module="turnos",
                metadata={"view": "RecursoViewSet.perform_update"},
            )

    def destroy(self, request, *args, **kwargs):
        """Baja lógica del recurso para evitar la cascada destructiva.

        ``Turno.recurso`` está definido con ``on_delete=CASCADE``, por lo que
        un DELETE físico borraría todos los turnos históricos asociados y
        rompería la trazabilidad clínica/operativa. En su lugar marcamos el
        recurso como ``activo=False`` y lo registramos en auditoría como
        actualización (no como delete).
        """
        instance = self.get_object()
        before = safe_model_snapshot(instance)

        if not instance.activo:
            return Response(status=status.HTTP_204_NO_CONTENT)

        with transaction.atomic():
            instance.activo = False
            instance.save(update_fields=["activo", "updated_at"])
            _safe_audit(
                log_update,
                actor=request.user,
                entity=instance,
                before=before,
                module="turnos",
                metadata={
                    "view": "RecursoViewSet.destroy",
                    "action": "soft_delete",
                },
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class TurnoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar Turnos.
    Incluye filtros por fecha, médico, paciente y estado.
    """
    queryset = (
        Turno.objects.select_related(
            'paciente',
            'medico',
            'recurso',
            'atencion',
            'atencion__consulta_ambulatoria',
            'atencion__registro_procedimiento',
            'atencion__registro_quirurgico',
        )
        .all()
    )
    serializer_class = TurnoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['medico', 'paciente', 'estado', 'recurso']
    search_fields = ['motivo_reserva']
    ordering_fields = ['fecha_hora_inicio', 'fecha_hora_fin', 'estado']
    ordering = ['fecha_hora_inicio']
    
    def get_queryset(self):
        """
        Filtrado por rol según reglas de negocio:
        - Admin, staff, secretaría, enfermería: agenda global (``?all=true`` ignorado)
        - Médico: solo turnos propios; ``?all=true`` no escala; sin ficha Medico: vacío
        - Paciente vinculado: solo sus turnos
        - Otros roles (p. ej. laboratorio): ninguno
        """
        queryset = super().get_queryset()
        user = self.request.user
        user_rol = (user.rol or '').lower()

        if _puede_ver_agenda_global_turnos(user):
            return queryset

        if user_rol == 'medico':
            try:
                med = user.medico
            except ObjectDoesNotExist:
                return queryset.none()
            return queryset.filter(medico=med)

        pac = ensure_paciente_linked_to_user(user)
        if not pac:
            return queryset.none()
        return queryset.filter(paciente=pac)

    def _deny_readonly_roles_on_write(self) -> None:
        """Enfermería y laboratorio: lectura global sin mutación (C5.8.1)."""
        user = self.request.user
        if _es_enfermeria(user) or _es_laboratorio(user):
            raise PermissionDenied('No tiene permiso para modificar turnos.')
        if not _puede_gestionar_turnos_global(user) and _rol_usuario(user) not in {
            'medico',
            'paciente',
        }:
            raise PermissionDenied('No tiene permiso para modificar turnos.')

    def update(self, request, *args, **kwargs):
        self._deny_readonly_roles_on_write()
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        self._deny_readonly_roles_on_write()
        return super().partial_update(request, *args, **kwargs)

    def perform_create(self, serializer):
        """
        Matriz de creación (C5.8.1): no confiar en IDs del cliente para médico/paciente
        cuando el rol exige turno propio.
        """
        user = self.request.user
        rol = _rol_usuario(user)

        if 'estado' in serializer.validated_data:
            try:
                turno_estado.validate_estado_en_creacion(
                    serializer.validated_data['estado'],
                )
            except turno_estado.TurnoEstadoTransitionError as exc:
                raise ValidationError({'estado': str(exc)}) from exc

        with transaction.atomic():
            if _puede_gestionar_turnos_global(user):
                instance = serializer.save()
            elif _es_enfermeria(user) or _es_laboratorio(user):
                raise PermissionDenied('No tiene permiso para crear turnos.')
            elif rol == 'medico':
                try:
                    med = user.medico
                except ObjectDoesNotExist:
                    raise PermissionDenied(
                        'El usuario médico no tiene ficha profesional vinculada.'
                    )
                instance = serializer.save(medico=med)
            elif rol == 'paciente':
                pac = ensure_paciente_linked_to_user(user)
                if not pac:
                    raise PermissionDenied(
                        'El usuario paciente no tiene ficha de paciente vinculada.'
                    )
                instance = serializer.save(paciente=pac)
            else:
                raise PermissionDenied('No tiene permiso para crear turnos.')

            _safe_audit(
                log_create,
                actor=user,
                entity=instance,
                module="turnos",
                metadata={"view": "TurnoViewSet.perform_create"},
            )

    def _reject_direct_estado_change(self, serializer) -> None:
        """C5.9.2: ningún rol cambia estado por PATCH/PUT; usar acciones de negocio."""
        if 'estado' not in serializer.validated_data:
            return
        raise ValidationError({
            'estado': (
                'El estado del turno debe modificarse mediante acciones específicas '
                '(confirmar, cancelar, reprogramar, marcar-realizado, marcar-no-asistio).'
            ),
        })

    def perform_update(self, serializer):
        """Matriz de modificación (C5.8.1) además del acotamiento por ``get_queryset``."""
        user = self.request.user
        rol = _rol_usuario(user)
        instance = self.get_object()
        self._reject_direct_estado_change(serializer)
        before = safe_model_snapshot(instance)

        with transaction.atomic():
            if _puede_gestionar_turnos_global(user):
                instance = serializer.save()
            elif _es_enfermeria(user) or _es_laboratorio(user):
                raise PermissionDenied('No tiene permiso para modificar turnos.')
            elif rol == 'medico':
                try:
                    med = user.medico
                except ObjectDoesNotExist:
                    raise PermissionDenied(
                        'El usuario médico no tiene ficha profesional vinculada.'
                    )
                if instance.medico_id != med.id:
                    raise PermissionDenied('No puede modificar turnos de otro médico.')
                _reject_foreign_medico_assignment(serializer, med)
                instance = serializer.save(medico=med)
            elif rol == 'paciente':
                pac = ensure_paciente_linked_to_user(user)
                if not pac:
                    raise PermissionDenied(
                        'El usuario paciente no tiene ficha de paciente vinculada.'
                    )
                if instance.paciente_id != pac.id:
                    raise PermissionDenied('No puede modificar turnos de otro paciente.')
                _reject_foreign_paciente_assignment(serializer, pac)
                instance = serializer.save(paciente=pac)
            else:
                raise PermissionDenied('No tiene permiso para modificar turnos.')

            _safe_audit(
                log_update,
                actor=user,
                entity=instance,
                before=before,
                module="turnos",
                metadata={"view": "TurnoViewSet.perform_update"},
            )

    def destroy(self, request, *args, **kwargs):
        """Bloquea el DELETE físico de turnos.

        Los turnos son registros clínico-operativos; su eliminación física
        afecta la trazabilidad. La cancelación o el cierre debe resolverse
        por estado (``CANCELADO`` / ``REALIZADO``), no por DELETE.
        """
        raise MethodNotAllowed(
            "DELETE",
            detail=(
                "El borrado físico de turnos no está permitido. "
                "Cancele o finalice el turno cambiando su estado."
            ),
        )

    def _get_turno_locked_for_estado_action(self, pk: int) -> Turno:
        """Visibilidad por ``get_queryset``; bloqueo en tabla base sin OUTER JOIN."""
        if not self.get_queryset().filter(pk=pk).exists():
            raise NotFound()
        return Turno.objects.select_for_update().get(pk=pk)

    def _estado_action_response(self, outcome: turno_estado.TurnoEstadoOutcome) -> Response:
        serializer = self.get_serializer(outcome.turno)
        return Response(
            {
                'message': outcome.message,
                'applied': outcome.applied,
                'estado_anterior': outcome.estado_anterior,
                'estado_nuevo': outcome.estado_nuevo,
                'turno': serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='confirmar')
    def confirmar(self, request, pk=None):
        """Confirma un turno: RESERVADO → CONFIRMADO (idempotente si ya confirmado)."""
        with transaction.atomic():
            turno = self._get_turno_locked_for_estado_action(pk)
            if not turno_estado.puede_confirmar_turno(request.user, turno):
                raise PermissionDenied('No tiene permiso para confirmar este turno.')
            try:
                outcome = turno_estado.confirmar_turno(
                    turno,
                    actor=request.user,
                    view_name='TurnoViewSet.confirmar',
                )
            except turno_estado.TurnoEstadoTransitionError as exc:
                raise ValidationError({'detail': str(exc)}) from exc

        return self._estado_action_response(outcome)

    @action(detail=True, methods=['post'], url_path='cancelar')
    def cancelar(self, request, pk=None):
        """Cancela un turno (motivo obligatorio en body). Idempotente si ya cancelado."""
        motivo = request.data.get('motivo', '')
        with transaction.atomic():
            turno = self._get_turno_locked_for_estado_action(pk)
            if not turno_estado.puede_cancelar_turno(request.user, turno):
                raise PermissionDenied('No tiene permiso para cancelar este turno.')
            try:
                outcome = turno_estado.cancelar_turno(
                    turno,
                    actor=request.user,
                    motivo=motivo,
                    view_name='TurnoViewSet.cancelar',
                )
            except turno_estado.TurnoEstadoTransitionError as exc:
                raise ValidationError({'detail': str(exc)}) from exc

        return self._estado_action_response(outcome)

    @action(detail=True, methods=['post'], url_path='reprogramar')
    def reprogramar(self, request, pk=None):
        """Reprograma fecha/hora (y opcionalmente médico/recurso) sin cambiar estado."""
        fecha_hora_inicio = request.data.get('fecha_hora_inicio')
        fecha_hora_fin = request.data.get('fecha_hora_fin')
        motivo = request.data.get('motivo', '')
        medico_obj = None
        recurso_obj = None
        medico_id = request.data.get('medico_id')
        recurso_id = request.data.get('recurso_id')

        if medico_id is not None:
            try:
                medico_obj = Medico.objects.get(pk=medico_id)
            except (Medico.DoesNotExist, ValueError, TypeError):
                raise ValidationError({'medico_id': 'Médico no válido.'}) from None
        if recurso_id is not None:
            try:
                recurso_obj = Recurso.objects.get(pk=recurso_id)
            except (Recurso.DoesNotExist, ValueError, TypeError):
                raise ValidationError({'recurso_id': 'Recurso no válido.'}) from None

        with transaction.atomic():
            turno = self._get_turno_locked_for_estado_action(pk)
            if not turno_estado.puede_reprogramar_turno(request.user, turno):
                raise PermissionDenied('No tiene permiso para reprogramar este turno.')
            try:
                outcome = turno_estado.reprogramar_turno(
                    turno,
                    actor=request.user,
                    fecha_hora_inicio=fecha_hora_inicio,
                    fecha_hora_fin=fecha_hora_fin,
                    motivo=motivo,
                    medico=medico_obj,
                    recurso=recurso_obj,
                    view_name='TurnoViewSet.reprogramar',
                )
            except turno_estado.TurnoEstadoTransitionError as exc:
                raise ValidationError({'detail': str(exc)}) from exc

        return self._estado_action_response(outcome)

    @action(detail=True, methods=['post'], url_path='marcar-realizado')
    def marcar_realizado(self, request, pk=None):
        """Marca turno como REALIZADO (transiciones según rol)."""
        motivo = request.data.get('motivo')
        with transaction.atomic():
            turno = self._get_turno_locked_for_estado_action(pk)
            if not turno_estado.puede_marcar_realizado_turno(request.user, turno):
                raise PermissionDenied(
                    'No tiene permiso para marcar este turno como realizado.'
                )
            try:
                outcome = turno_estado.marcar_realizado_turno(
                    turno,
                    actor=request.user,
                    motivo=motivo,
                    view_name='TurnoViewSet.marcar_realizado',
                )
            except turno_estado.TurnoEstadoTransitionError as exc:
                raise ValidationError({'detail': str(exc)}) from exc

        return self._estado_action_response(outcome)

    @action(detail=True, methods=['post'], url_path='marcar-no-asistio')
    def marcar_no_asistio(self, request, pk=None):
        """Registra no asistencia → CANCELADO con metadata ``marcar_no_asistio``."""
        motivo = request.data.get('motivo', '')
        with transaction.atomic():
            turno = self._get_turno_locked_for_estado_action(pk)
            if not turno_estado.puede_marcar_no_asistio_turno(request.user, turno):
                raise PermissionDenied(
                    'No tiene permiso para registrar no asistencia en este turno.'
                )
            try:
                outcome = turno_estado.marcar_no_asistio_turno(
                    turno,
                    actor=request.user,
                    motivo=motivo,
                    view_name='TurnoViewSet.marcar_no_asistio',
                )
            except turno_estado.TurnoEstadoTransitionError as exc:
                raise ValidationError({'detail': str(exc)}) from exc

        return self._estado_action_response(outcome)

    @action(detail=True, methods=['post'], url_path='iniciar-atencion')
    def iniciar_atencion(self, request, pk=None):
        """
        Inicia atención clínica desde turno (C5.10.1): crea/obtiene Atención y pasa turno a REALIZADO.
        """
        with transaction.atomic():
            turno = self._get_turno_locked_for_estado_action(pk)
            if not turno_estado.puede_iniciar_atencion_turno(request.user, turno):
                raise PermissionDenied(
                    'No tiene permiso para iniciar atención clínica en este turno.'
                )
            before_turno = safe_model_snapshot(turno)
            try:
                outcome = AtencionService.iniciar_atencion_clinica_desde_turno(turno)
            except BusinessLogicError as exc:
                raise ValidationError({'detail': str(exc)}) from exc

            if outcome.created_new:
                _safe_audit(
                    log_create,
                    actor=request.user,
                    entity=outcome.atencion,
                    module='turnos',
                    metadata={
                        'view': 'TurnoViewSet.iniciar_atencion',
                        'accion': 'iniciar_atencion_turno',
                        'turno_id': turno.pk,
                        'atencion_id': outcome.atencion.pk,
                        'created_new': True,
                    },
                )

            if outcome.turno_estado_changed:
                turno.refresh_from_db()
                _safe_audit(
                    log_update,
                    actor=request.user,
                    entity=turno,
                    before=before_turno,
                    module='turnos',
                    metadata={
                        'accion': 'iniciar_atencion_turno',
                        'turno_id': turno.pk,
                        'atencion_id': outcome.atencion.pk,
                        'estado_anterior': outcome.turno_estado_anterior,
                        'estado_nuevo': outcome.turno_estado_nuevo,
                        'view': 'TurnoViewSet.iniciar_atencion',
                    },
                )

        serializer = AtencionSerializer(
            outcome.atencion,
            context=self.get_serializer_context(),
        )
        http_status = status.HTTP_201_CREATED if outcome.created_new else status.HTTP_200_OK
        return Response(
            {
                'atencion': serializer.data,
                'created_new': outcome.created_new,
                'turno_estado': outcome.turno_estado_nuevo,
                'message': (
                    'Atención iniciada correctamente.'
                    if outcome.created_new
                    else 'Atención ya existente para este turno.'
                ),
            },
            status=http_status,
        )

    def filter_queryset(self, queryset):
        """
        Filtros adicionales por query params:
        - start: Fecha de inicio (fecha_hora_inicio >= start)
        - end: Fecha de fin (fecha_hora_inicio <= end)
        """
        queryset = super().filter_queryset(queryset)
        
        # Filtro por rango de fechas (vital para vista mensual/semanal del calendario)
        start = self.request.query_params.get('start')
        end = self.request.query_params.get('end')
        
        if start:
            try:
                # Intentar parsear como ISO datetime o date
                start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                queryset = queryset.filter(fecha_hora_inicio__gte=start_dt)
            except (ValueError, AttributeError):
                try:
                    # Intentar como date solamente
                    start_dt = datetime.strptime(start, '%Y-%m-%d')
                    queryset = queryset.filter(fecha_hora_inicio__date__gte=start_dt.date())
                except ValueError:
                    pass  # Ignorar si no se puede parsear
        
        if end:
            try:
                end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                queryset = queryset.filter(fecha_hora_inicio__lte=end_dt)
            except (ValueError, AttributeError):
                try:
                    end_dt = datetime.strptime(end, '%Y-%m-%d')
                    queryset = queryset.filter(fecha_hora_inicio__date__lte=end_dt.date())
                except ValueError:
                    pass  # Ignorar si no se puede parsear
        
        return queryset


_ATENCIONES_COMPAT_DEPRECATED_ENDPOINT = "POST /api/atenciones/"
_ATENCIONES_COMPAT_REPLACEMENT_ENDPOINT = "POST /api/turnos/{id}/iniciar-atencion/"
_ATENCIONES_COMPAT_WARNING = (
    '299 - "POST /api/atenciones/ is compatibility-only; '
    'use POST /api/turnos/{id}/iniciar-atencion/ for clinical start"'
)


def _atenciones_compat_deprecation_headers() -> dict[str, str]:
    """Headers HTTP no disruptivos para POST /api/atenciones/ (C5.10.2). Sin PHI."""
    return {
        "Deprecation": "true",
        "X-Synesis-Deprecated-Endpoint": _ATENCIONES_COMPAT_DEPRECATED_ENDPOINT,
        "X-Synesis-Replacement-Endpoint": _ATENCIONES_COMPAT_REPLACEMENT_ENDPOINT,
        "Warning": _ATENCIONES_COMPAT_WARNING,
    }


class AtencionViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar Atenciones.
    Permisos: AtencionPermission (QA-ROLE-01).
    """
    queryset = Atencion.objects.select_related(
        'paciente', 'medico_principal', 'turno'
    ).prefetch_related(
        'documentos', 'documentos__usuario_cargador',
        'consulta_ambulatoria', 'registro_procedimiento', 'registro_quirurgico'
    ).all()
    serializer_class = AtencionSerializer
    permission_classes = [AtencionPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['paciente', 'medico_principal', 'estado_clinico', 'tipo_atencion']
    search_fields = ['paciente__nombre', 'paciente__apellido', 'paciente__dni']
    ordering_fields = ['fecha_admision', 'fecha_cierre', 'estado_clinico']
    ordering = ['-fecha_admision']

    def get_queryset(self):
        """Filtrado por rol (QA-ROLE-01): ver ``filter_atencion_queryset_for_user``."""
        return filter_atencion_queryset_for_user(
            self.request.user,
            super().get_queryset(),
        )

    def destroy(self, request, *args, **kwargs):
        """Bloquea el DELETE físico de atenciones.

        Las atenciones son registros clínicos. Para "anularlas" debe usarse
        el flujo de cierre/observación, no el DELETE.
        """
        raise MethodNotAllowed(
            "DELETE",
            detail=(
                "El borrado físico de atenciones no está permitido. "
                "Use el cierre clínico o registre una observación."
            ),
        )

    def create(self, request, *args, **kwargs):
        """
        Compat/deprecated (C5.10.2): crea u obtiene Atención sin mover el turno a REALIZADO.

        Flujo clínico desde agenda: POST /api/turnos/{id}/iniciar-atencion/.
        Respuesta incluye headers Deprecation / X-Synesis-* / Warning (sin cambiar el JSON).
        """
        turno_raw = request.data.get("turno")
        if not turno_raw:
            return Response(
                {"error": "Se requiere el ID del turno para crear una atención."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        if not (
            user.is_superuser
            or user.is_staff
            or get_normalized_role(user) == 'admin'
        ):
            try:
                medico = user.medico
            except ObjectDoesNotExist:
                medico = None
            if medico is None:
                return Response(
                    {'error': 'No tiene permisos para crear atenciones.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
            try:
                turno = Turno.objects.get(pk=turno_raw)
            except (Turno.DoesNotExist, ValueError, TypeError):
                turno = None
            if turno is None or turno.medico_id != medico.id:
                return Response(
                    {'error': 'No tiene permisos para crear atenciones en este turno.'},
                    status=status.HTTP_403_FORBIDDEN,
                )

        try:
            outcome = AtencionService.iniciar_atencion_desde_turno(
                turno_raw,
                usuario_solicitante=request.user,
                observaciones_generales=request.data.get("observaciones_generales", ""),
                api_post_compat=True,
                actor=request.user,
            )
        except BusinessLogicError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(outcome.atencion)
        headers = _atenciones_compat_deprecation_headers()
        if outcome.created_new:
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
                headers=headers,
            )
        return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)
    
    @action(detail=True, methods=['post'], url_path='cerrar')
    @transaction.atomic
    def cerrar(self, request, pk=None):
        """Cierra una atención (estado_clinico=FINALIZADA, fecha_cierre=now).

        Solo aplica si la atención está ``ABIERTA``. Operación atómica para
        que el cambio de estado y la auditoría se persistan juntas.
        """
        atencion = self.get_object()

        if atencion.estado_clinico != Atencion.EstadoClinico.ABIERTA:
            return Response(
                {'error': 'Solo se puede cerrar una atención que esté en estado ABIERTA.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        before = safe_model_snapshot(atencion)
        atencion.estado_clinico = Atencion.EstadoClinico.FINALIZADA
        atencion.fecha_cierre = timezone.now()
        atencion.save(update_fields=['estado_clinico', 'fecha_cierre', 'updated_at'])

        _safe_audit(
            log_update,
            actor=request.user,
            entity=atencion,
            before=before,
            module="turnos",
            metadata={"action": "cerrar", "view": "AtencionViewSet.cerrar"},
        )

        serializer = self.get_serializer(atencion)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'], url_path='registrar-consulta')
    @transaction.atomic
    def registrar_consulta(self, request, pk=None):
        """Crea o actualiza una ``ConsultaAmbulatoria`` asociada a una ``Atencion``.

        Reglas de negocio:

        - Solo el médico asignado a la atención (o un admin/staff) puede registrar.
        - Si ya existe ``ConsultaAmbulatoria`` se actualiza (PATCH semántico).
        - Si no existe, se crea (INSERT).
        - No se puede registrar sobre atenciones cerradas (``fecha_cierre`` set).
        - El tipo de intervención debe ser ``CONSULTA``.
        - Si ``estado_clinico`` se marca como ``FINALIZADA``, ``anamnesis`` es obligatoria
          (validado en el serializer).

        Notas:

        - Las excepciones inesperadas NO se atrapan en bloque genérico para
          no enmascarar 404/403/405. ``@transaction.atomic`` garantiza rollback.
        - El filtro ``get_queryset`` ya restringe por rol; un médico que no es
          el asignado recibe 404 antes de llegar acá (decisión deliberada para
          no leakear la existencia de la atención).
        """
        atencion = self.get_object()
        user = request.user

        logger.info(
            "Iniciando registro de consulta ambulatoria para Atención ID: %s, Usuario: %s, Rol: %s",
            atencion.id, user.username, getattr(user, 'rol', 'N/A')
        )

        # Verificación defensiva: aunque get_queryset ya filtra, dejamos el
        # check explícito para los casos en que un admin reutilice este action
        # con un usuario médico vinculado a otro Medico distinto del de la
        # atención. No se reporta el detalle para no leakear información.
        if not (user.is_superuser or user.is_staff):
            try:
                user_medico = user.medico
            except ObjectDoesNotExist:
                user_medico = None
            if user_medico is None:
                return Response(
                    {'error': 'No tiene permisos para registrar consultas.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
            if atencion.medico_principal_id != user_medico.id:
                logger.warning(
                    "Intento de registro de consulta por médico no asignado. "
                    "Atención ID: %s, Médico asignado: %s, Usuario: %s, Médico usuario: %s",
                    atencion.id, atencion.medico_principal_id, user.username, user_medico.id,
                )
                return Response(
                    {'error': 'Solo el médico asignado a esta atención puede registrar la consulta.'},
                    status=status.HTTP_403_FORBIDDEN,
                )

        if atencion.fecha_cierre:
            return Response(
                {'error': 'No se puede editar una consulta de una atención ya cerrada.'},
                status=status.HTTP_409_CONFLICT,
            )

        if atencion.tipo_intervencion != Atencion.TipoIntervencion.CONSULTA:
            return Response(
                {'error': 'Este tipo de atención no corresponde a consulta ambulatoria.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        before_atencion = safe_model_snapshot(atencion)
        before_turno = safe_model_snapshot(atencion.turno) if atencion.turno_id else None

        nuevo_estado = request.data.get('estado_clinico')
        if nuevo_estado:
            estados_validos = [choice[0] for choice in Atencion.EstadoClinico.choices]
            if nuevo_estado not in estados_validos:
                return Response(
                    {'error': f'Estado clínico inválido. Estados válidos: {estados_validos}'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            atencion.estado_clinico = nuevo_estado

        consulta_data = request.data.copy()
        consulta_data.pop('estado_clinico', None)

        consulta_existente = None
        try:
            consulta_existente = atencion.consulta_ambulatoria
        except ConsultaAmbulatoria.DoesNotExist:
            pass

        serializer = ConsultaAmbulatoriaSerializer(
            instance=consulta_existente,
            data=consulta_data,
            context={'request': request, 'atencion': atencion},
        )
        if not serializer.is_valid():
            logger.warning(
                "Validación falló en registrar_consulta. Atención ID: %s, errors: %s",
                atencion.id, serializer.errors,
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        consulta = serializer.save(atencion=atencion)

        if atencion.turno_id and consulta_ambulatoria_tiene_contenido(consulta):
            turno = atencion.turno
            if turno and turno.estado != Turno.Estado.REALIZADO:
                turno.estado = Turno.Estado.REALIZADO
                turno.save(update_fields=['estado', 'updated_at'])
                logger.info(
                    "Turno %s pasó a REALIZADO tras guardar consulta con contenido (Atención %s)",
                    turno.id, atencion.id,
                )

        if nuevo_estado:
            atencion.save(update_fields=['estado_clinico', 'updated_at'])

        _safe_audit(
            log_update,
            actor=user,
            entity=atencion,
            before=before_atencion,
            module="turnos",
            metadata={"action": "registrar_consulta", "view": "AtencionViewSet.registrar_consulta"},
        )
        if atencion.turno_id:
            _safe_audit(
                log_update,
                actor=user,
                entity=atencion.turno,
                before=before_turno,
                module="turnos",
                metadata={
                    "action": "auto_realizado_por_consulta",
                    "view": "AtencionViewSet.registrar_consulta",
                },
            )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK if consulta_existente else status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'], url_path='crear_registro_ambulatorio')
    @transaction.atomic
    def crear_registro_ambulatorio(self, request, pk=None):
        """Crea (sin actualizar) una ``ConsultaAmbulatoria`` para una atención.

        Compatibilidad con el endpoint esperado por el frontend. La operación
        está envuelta en ``@transaction.atomic`` para que la creación de la
        consulta y la auditoría asociada aborten en bloque ante cualquier
        error en el medio.
        """
        atencion = self.get_object()

        if atencion.tipo_intervencion != Atencion.TipoIntervencion.CONSULTA:
            return Response(
                {'error': 'Este tipo de atención no corresponde a consulta ambulatoria'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if atencion.fecha_cierre:
            return Response(
                {'error': 'No se puede crear consulta sobre una atención cerrada.'},
                status=status.HTTP_409_CONFLICT,
            )

        try:
            atencion.consulta_ambulatoria  # noqa: WPS428 - solo verificamos existencia
            return Response(
                {'error': 'Ya existe un registro de consulta ambulatoria para esta atención'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ConsultaAmbulatoria.DoesNotExist:
            pass

        serializer = ConsultaAmbulatoriaSerializer(
            data=request.data,
            context={'request': request, 'atencion': atencion},
        )
        serializer.is_valid(raise_exception=True)
        consulta = serializer.save(atencion=atencion)

        _safe_audit(
            log_create,
            actor=request.user,
            entity=consulta,
            module="turnos",
            metadata={
                "action": "crear_registro_ambulatorio",
                "view": "AtencionViewSet.crear_registro_ambulatorio",
            },
        )

        logger.info(
            "ConsultaAmbulatoria creada para Atención ID: %s, Usuario: %s",
            atencion.id, request.user.username,
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)
