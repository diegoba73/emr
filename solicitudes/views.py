from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from .models import Solicitud
from integracion_lims import lims_service
from auditoria.audit_service import log_create, log_update, log_event
from auditoria.snapshot import safe_model_snapshot
from api.permissions import get_normalized_role
from .permissions import SolicitudPermission, is_admin
from .serializers import (
    SolicitudSerializer,
    SolicitudCreateSerializer,
    SolicitudUpdateSerializer,
    SolicitudListSerializer,
    SolicitudEstadoSerializer,
    SolicitudLimsSerializer,
    SolicitudEstadisticasSerializer,
)


def _audit_solicitud_meta(accion: str, view: str, solicitud, **extra) -> dict:
    """Metadata técnica de auditoría sin PHI ni payload externo."""
    meta = {
        'accion': accion,
        'view': view,
        'solicitud_id': solicitud.pk,
        'tipo_solicitud': solicitud.tipo_solicitud,
    }
    meta.update(extra)
    return meta


def _estado_meta(before: dict, solicitud) -> dict:
    return {
        'estado_anterior': before.get('estado'),
        'estado_nuevo': solicitud.estado,
    }


class SolicitudViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar solicitudes genéricas EMR (no LIMS nativo).

    Permisos: ``SolicitudPermission`` (PERM-01). La lectura se acota además por ``get_queryset``.
  """

    queryset = Solicitud.objects.all()
    serializer_class = SolicitudSerializer
    permission_classes = [SolicitudPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'estado',
        'tipo_solicitud',
        'prioridad',
        'sincronizado_lims',
        'medico_solicitante',
        'paciente',
    ]
    search_fields = [
        'paciente__nombre',
        'paciente__apellido',
        'paciente__dni',
        'medico_solicitante__nombre',
        'medico_solicitante__apellido',
        'descripcion',
        'observaciones',
        'lims_id',
    ]
    ordering_fields = [
        'fecha_solicitud',
        'fecha_limite',
        'estado',
        'prioridad',
        'paciente__nombre',
    ]
    ordering = ['-fecha_solicitud']

    def get_queryset(self):
        """Filtra el queryset basado en el rol del usuario autenticado."""
        queryset = super().get_queryset().select_related(
            'paciente',
            'medico_solicitante',
            'creado_por',
            'modificado_por',
        ).prefetch_related('medicos_asignados')

        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()

        if is_admin(user):
            return queryset

        role = get_normalized_role(user)

        if role == 'secretaria':
            return queryset

        if role == 'medico':
            try:
                medico = user.medico
                return queryset.filter(
                    Q(medico_solicitante=medico)
                    | Q(medicos_asignados=medico)
                    | Q(creado_por=user)
                ).distinct()
            except Exception:
                return queryset.none()

        if role == 'paciente':
            try:
                paciente = user.paciente
                return queryset.filter(paciente=paciente)
            except Exception:
                return queryset.none()

        return queryset.none()

    def get_serializer_class(self):
        if self.action == 'create':
            return SolicitudCreateSerializer
        if self.action in ['update', 'partial_update']:
            return SolicitudUpdateSerializer
        if self.action == 'list':
            return SolicitudListSerializer
        if self.action == 'cambiar_estado':
            return SolicitudEstadoSerializer
        if self.action == 'sincronizar_lims':
            return SolicitudLimsSerializer
        if self.action == 'estadisticas':
            return SolicitudEstadisticasSerializer
        return SolicitudSerializer

    def perform_create(self, serializer):
        user = self.request.user
        solicitud = serializer.save(
            creado_por=user,
            modificado_por=user,
        )
        log_create(
            actor=user,
            entity=solicitud,
            module='solicitudes',
            metadata=_audit_solicitud_meta(
                'solicitud_create',
                'SolicitudViewSet.perform_create',
                solicitud,
            ),
        )

    def perform_update(self, serializer):
        before = safe_model_snapshot(self.get_object())
        instance = serializer.save(modificado_por=self.request.user)
        log_update(
            actor=self.request.user,
            entity=instance,
            before=before,
            module='solicitudes',
            metadata=_audit_solicitud_meta(
                'solicitud_update',
                'SolicitudViewSet.perform_update',
                instance,
            ),
        )

    def perform_destroy(self, instance):
        pk = instance.pk
        label = Solicitud._meta.label
        before = safe_model_snapshot(instance)
        super().perform_destroy(instance)
        log_event(
            action='DELETE',
            actor=self.request.user,
            entity=None,
            entity_type=label,
            entity_id=str(pk),
            entity_repr=f'{label}:{pk}'[:255],
            before=before,
            after=None,
            module='solicitudes',
            metadata=_audit_solicitud_meta(
                'solicitud_destroy',
                'SolicitudViewSet.perform_destroy',
                instance,
            ),
        )

    @action(detail=True, methods=['patch'])
    def cambiar_estado(self, request, pk=None):
        solicitud = self.get_object()
        before = safe_model_snapshot(solicitud)
        serializer = self.get_serializer(solicitud, data=request.data, partial=True)

        if serializer.is_valid():
            instance = serializer.save(modificado_por=request.user)
            log_update(
                actor=request.user,
                entity=instance,
                before=before,
                module='solicitudes',
                metadata=_audit_solicitud_meta(
                    'solicitud_estado_cambio',
                    'SolicitudViewSet.cambiar_estado',
                    instance,
                    **_estado_meta(before, instance),
                ),
            )
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def marcar_como_completada(self, request, pk=None):
        solicitud = self.get_object()
        before = safe_model_snapshot(solicitud)
        solicitud.marcar_como_completada()
        solicitud.modificado_por = request.user
        solicitud.save()
        log_update(
            actor=request.user,
            entity=solicitud,
            before=before,
            module='solicitudes',
            metadata=_audit_solicitud_meta(
                'solicitud_estado_cambio',
                'SolicitudViewSet.marcar_como_completada',
                solicitud,
                **_estado_meta(before, solicitud),
            ),
        )

        serializer = self.get_serializer(solicitud)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        solicitud = self.get_object()
        before = safe_model_snapshot(solicitud)
        solicitud.cancelar()
        solicitud.modificado_por = request.user
        solicitud.save()
        log_update(
            actor=request.user,
            entity=solicitud,
            before=before,
            module='solicitudes',
            metadata=_audit_solicitud_meta(
                'solicitud_cancelar',
                'SolicitudViewSet.cancelar',
                solicitud,
                motivo_presente=bool((request.data.get('motivo') or '').strip()),
                **_estado_meta(before, solicitud),
            ),
        )

        serializer = self.get_serializer(solicitud)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def reabrir(self, request, pk=None):
        solicitud = self.get_object()
        before = safe_model_snapshot(solicitud)
        solicitud.reabrir()
        solicitud.modificado_por = request.user
        solicitud.save()
        log_update(
            actor=request.user,
            entity=solicitud,
            before=before,
            module='solicitudes',
            metadata=_audit_solicitud_meta(
                'solicitud_reabrir',
                'SolicitudViewSet.reabrir',
                solicitud,
                **_estado_meta(before, solicitud),
            ),
        )

        serializer = self.get_serializer(solicitud)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def sincronizar_lims(self, request, pk=None):
        solicitud = self.get_object()
        before = safe_model_snapshot(solicitud)
        success = False

        if solicitud.tipo_solicitud == 'EXAMEN_LABORATORIO':
            solicitud._enviar_a_lims()
            solicitud.modificado_por = request.user
            solicitud.save()
            success = bool(solicitud.sincronizado_lims)

        log_update(
            actor=request.user,
            entity=solicitud,
            before=before,
            module='solicitudes',
            metadata=_audit_solicitud_meta(
                'solicitud_lims_sincronizar',
                'SolicitudViewSet.sincronizar_lims',
                solicitud,
                destino='lims_externo',
                success=success,
                lims_id_presente=bool(solicitud.lims_id),
            ),
        )

        serializer = SolicitudLimsSerializer(solicitud)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def enviar_lims(self, request, pk=None):
        solicitud = self.get_object()

        if solicitud.tipo_solicitud != 'EXAMEN_LABORATORIO':
            return Response(
                {'detail': 'Solo válido para EXAMEN_LABORATORIO'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        before = safe_model_snapshot(solicitud)
        paneles = request.data.get('paneles') or []
        tipos = request.data.get('tipos_examen') or []

        payload = {
            'external_id': str(solicitud.id),
            'paciente_id': solicitud.paciente.id if solicitud.paciente else None,
            'paciente_nombre': (
                getattr(solicitud.paciente, 'nombre_completo', None) if solicitud.paciente else None
            ),
            'medico_id': (
                solicitud.medico_solicitante.id if solicitud.medico_solicitante else None
            ),
            'medico_nombre': (
                f"{getattr(solicitud.medico_solicitante, 'nombre', '')} "
                f"{getattr(solicitud.medico_solicitante, 'apellido', '')}".strip()
                if solicitud.medico_solicitante else None
            ),
            'prioridad': solicitud.prioridad,
            'observaciones': solicitud.observaciones or solicitud.descripcion or '',
            'paneles': paneles,
            'tipos_examen': tipos,
        }

        result = lims_service.enviar_solicitud_a_lims(payload)
        success = bool(result and 'id' in result)
        if success:
            solicitud.lims_id = result.get('id')
            solicitud.sincronizado_lims = True
            solicitud.ultima_sincronizacion = timezone.now()
            solicitud.save(update_fields=['lims_id', 'sincronizado_lims', 'ultima_sincronizacion'])

        log_update(
            actor=request.user,
            entity=solicitud,
            before=before,
            module='solicitudes',
            metadata=_audit_solicitud_meta(
                'solicitud_lims_enviar',
                'SolicitudViewSet.enviar_lims',
                solicitud,
                destino='lims_externo',
                success=success,
                paneles_count=len(paneles),
                tipos_count=len(tipos),
                lims_id_presente=bool(solicitud.lims_id),
            ),
        )

        if success:
            return Response({'lims_id': solicitud.lims_id, 'status': 'ok'})

        return Response({'detail': 'No se pudo enviar al LIMS'}, status=status.HTTP_502_BAD_GATEWAY)

    @action(detail=False, methods=['get'])
    def estadisticas(self, request):
        queryset = self.get_queryset()

        total_solicitudes = queryset.count()
        solicitudes_pendientes = queryset.filter(estado='PENDIENTE').count()
        solicitudes_en_proceso = queryset.filter(estado='EN_PROCESO').count()
        solicitudes_completadas = queryset.filter(estado='COMPLETADA').count()
        solicitudes_canceladas = queryset.filter(estado='CANCELADA').count()
        solicitudes_vencidas = queryset.filter(
            Q(fecha_limite__lt=timezone.now())
            & ~Q(estado__in=['COMPLETADA', 'CANCELADA'])
        ).count()
        solicitudes_sincronizadas_lims = queryset.filter(sincronizado_lims=True).count()

        por_tipo = dict(
            queryset.values('tipo_solicitud').annotate(count=Count('id')).values_list(
                'tipo_solicitud', 'count'
            )
        )
        por_prioridad = dict(
            queryset.values('prioridad').annotate(count=Count('id')).values_list(
                'prioridad', 'count'
            )
        )
        solicitudes_recientes = queryset.order_by('-fecha_solicitud')[:10]

        data = {
            'total_solicitudes': total_solicitudes,
            'solicitudes_pendientes': solicitudes_pendientes,
            'solicitudes_en_proceso': solicitudes_en_proceso,
            'solicitudes_completadas': solicitudes_completadas,
            'solicitudes_canceladas': solicitudes_canceladas,
            'solicitudes_vencidas': solicitudes_vencidas,
            'solicitudes_sincronizadas_lims': solicitudes_sincronizadas_lims,
            'por_tipo': por_tipo,
            'por_prioridad': por_prioridad,
            'solicitudes_recientes': SolicitudListSerializer(
                solicitudes_recientes, many=True
            ).data,
        }

        serializer = SolicitudEstadisticasSerializer(data)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def pendientes(self, request):
        queryset = self.get_queryset().filter(estado='PENDIENTE')
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = SolicitudListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = SolicitudListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def vencidas(self, request):
        queryset = self.get_queryset().filter(
            Q(fecha_limite__lt=timezone.now())
            & ~Q(estado__in=['COMPLETADA', 'CANCELADA'])
        )
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = SolicitudListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = SolicitudListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def mias(self, request):
        user = request.user
        queryset = self.get_queryset()
        role = get_normalized_role(user)

        if role == 'medico':
            try:
                medico = user.medico
                queryset = queryset.filter(
                    Q(medico_solicitante=medico) | Q(medicos_asignados=medico)
                ).distinct()
            except Exception:
                queryset = queryset.none()
        elif role == 'paciente':
            try:
                paciente = user.paciente
                queryset = queryset.filter(paciente=paciente)
            except Exception:
                queryset = queryset.none()

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = SolicitudListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = SolicitudListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def proximas_vencer(self, request):
        fecha_limite = timezone.now() + timedelta(days=7)
        queryset = self.get_queryset().filter(
            Q(fecha_limite__lte=fecha_limite)
            & Q(fecha_limite__gt=timezone.now())
            & ~Q(estado__in=['COMPLETADA', 'CANCELADA'])
        ).order_by('fecha_limite')

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = SolicitudListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = SolicitudListSerializer(queryset, many=True)
        return Response(serializer.data)
