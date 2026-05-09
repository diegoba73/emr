"""
ViewSets para la app turnos.
"""
import logging
from rest_framework import viewsets, filters, status
from rest_framework.exceptions import MethodNotAllowed, ValidationError
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from datetime import datetime
from pacientes.services import ensure_paciente_linked_to_user

from .models import Turno, Recurso, Atencion, ConsultaAmbulatoria
from .services import AtencionService, BusinessLogicError
from .serializers import (
    TurnoSerializer,
    RecursoSerializer,
    ConsultaAmbulatoriaSerializer,
    consulta_ambulatoria_tiene_contenido,
)
# Usar el AtencionSerializer completo de api.serializers que incluye documentos
from api.serializers import AtencionSerializer
from api.permissions import IsMedicoOrEnfermeriaOrAdmin
from auditoria.audit_service import log_create, log_delete, log_update
from auditoria.snapshot import safe_model_snapshot

logger = logging.getLogger(__name__)


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
        - Admin, Secretaría, Enfermería: ven todo
        - Médico: los suyos, o todos con ?all=true; sin ficha vinculada, ver todo
        - Cualquier usuario con ficha de paciente: solo sus turnos
        """
        queryset = super().get_queryset()
        user = self.request.user
        user_rol = (user.rol or '').lower()

        if user.is_superuser or user.is_staff or user_rol in ['admin', 'secretaria', 'enfermeria']:
            return queryset

        if user_rol == 'medico':
            try:
                med = user.medico
            except ObjectDoesNotExist:
                return queryset
            if self.request.query_params.get('all') == 'true':
                return queryset
            return queryset.filter(medico=med)

        pac = ensure_paciente_linked_to_user(user)
        if not pac:
            return queryset.none()
        return queryset.filter(paciente=pac)

    def perform_create(self, serializer):
        """
        Garantizar que un usuario con rol paciente no cree turnos sin ficha o con otro paciente.
        El GET lista solo turnos con paciente = user.paciente; si el front no enviaba
        paciente_id, el turno quedaba con paciente NULL y "desaparecía" de la grilla.
        """
        user = self.request.user
        with transaction.atomic():
            if (getattr(user, "rol", "") or "").lower() == "paciente":
                pac = ensure_paciente_linked_to_user(user)
                if not pac:
                    raise ValidationError(
                        "No hay ficha de paciente vinculada a su usuario. Compruebe que el email "
                        "de la cuenta coincida con el de su ficha, o contacte a administración."
                    )
                instance = serializer.save(paciente=pac)
            else:
                instance = serializer.save()

            _safe_audit(
                log_create,
                actor=user,
                entity=instance,
                module="turnos",
                metadata={"view": "TurnoViewSet.perform_create"},
            )

    def perform_update(self, serializer):
        """Mismo criterio que en create: un paciente no puede reasignar el turno a otro."""
        user = self.request.user
        before = safe_model_snapshot(self.get_object())
        with transaction.atomic():
            if (getattr(user, "rol", "") or "").lower() == "paciente":
                pac = ensure_paciente_linked_to_user(user)
                if not pac:
                    raise ValidationError(
                        "No hay ficha de paciente vinculada a su usuario. Contacte a administración."
                    )
                instance = serializer.save(paciente=pac)
            else:
                instance = serializer.save()

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


class AtencionViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar Atenciones.
    Permisos: IsMedicoOrEnfermeriaOrAdmin
    """
    queryset = Atencion.objects.select_related(
        'paciente', 'medico_principal', 'turno'
    ).prefetch_related(
        'documentos', 'documentos__usuario_cargador',
        'consulta_ambulatoria', 'registro_procedimiento', 'registro_quirurgico'
    ).all()
    serializer_class = AtencionSerializer
    permission_classes = [IsMedicoOrEnfermeriaOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['paciente', 'medico_principal', 'estado_clinico', 'tipo_atencion']
    search_fields = ['paciente__nombre', 'paciente__apellido', 'paciente__dni']
    ordering_fields = ['fecha_admision', 'fecha_cierre', 'estado_clinico']
    ordering = ['-fecha_admision']

    def get_queryset(self):
        """
        Filtrado por rol según reglas de negocio.
        - Admin/Enfermería: Ven todo
        - Médico: Solo ve atenciones donde es el médico principal
        - Paciente: Solo ve sus propias atenciones
        """
        queryset = super().get_queryset()
        user = self.request.user

        # Superusuarios y staff ven todo
        if user.is_superuser or user.is_staff:
            return queryset

        # Médico: solo sus atenciones (acceso seguro: el OneToOne inverso
        # lanza DoesNotExist si no hay ficha vinculada).
        try:
            medico = user.medico
        except ObjectDoesNotExist:
            medico = None
        if medico:
            return queryset.filter(medico_principal=medico)

        # Paciente: solo sus atenciones
        try:
            paciente = user.paciente
        except ObjectDoesNotExist:
            paciente = None
        if paciente:
            return queryset.filter(paciente=paciente)

        return queryset.none()

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
        Crea una Atención desde un Turno.

        - Si ya existe una atención para el turno, retorna la existente (idempotencia).
        - Resuelve automáticamente paciente, medico_principal, tipo_atencion desde el turno.
        - El frontend NO necesita enviar medico_principal.
        """
        turno_raw = request.data.get("turno")
        if not turno_raw:
            return Response(
                {"error": "Se requiere el ID del turno para crear una atención."},
                status=status.HTTP_400_BAD_REQUEST,
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
        if outcome.created_new:
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
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
