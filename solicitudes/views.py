from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from .models import Solicitud
from integracion_lims import lims_service
from auditoria.audit_service import log_create, log_update
from auditoria.snapshot import safe_model_snapshot
from .serializers import (
    SolicitudSerializer,
    SolicitudCreateSerializer,
    SolicitudUpdateSerializer,
    SolicitudListSerializer,
    SolicitudEstadoSerializer,
    SolicitudLimsSerializer,
    SolicitudEstadisticasSerializer,
)

class SolicitudViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar solicitudes con autenticación JWT y permisos basados en roles.
    
    Permisos:
    - ADMIN: Acceso completo a todas las solicitudes
    - MEDICO: Solo solicitudes donde es solicitante o asignado
    - SECRETARIA: Solo solicitudes de pacientes asignados
    - PACIENTE: Solo sus propias solicitudes
    """
    
    queryset = Solicitud.objects.all()
    serializer_class = SolicitudSerializer
    permission_classes = [permissions.IsAuthenticated]
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
        """
        Filtra el queryset basado en el rol del usuario autenticado.
        """
        queryset = super().get_queryset().select_related(
            'paciente', 
            'medico_solicitante', 
            'creado_por', 
            'modificado_por'
        ).prefetch_related('medicos_asignados')
        
        user = self.request.user
        
        rol = getattr(user, 'rol', '') or ''
        rol_upper = rol.upper()

        # ADMIN puede ver todas las solicitudes
        if user.is_superuser or rol_upper == 'ADMIN':
            return queryset
        
        # SECRETARIA puede ver solicitudes de pacientes asignados
        elif rol_upper == 'SECRETARIA':
            # Por ahora, las secretarias ven todas las solicitudes
            # En el futuro se puede implementar lógica de asignación
            return queryset
        
        # MEDICO puede ver solicitudes donde es solicitante o asignado
        elif rol_upper == 'MEDICO':
            try:
                medico = user.medico
                return queryset.filter(
                    Q(medico_solicitante=medico) |
                    Q(medicos_asignados=medico) |
                    Q(creado_por=user)
                ).distinct()
            except:
                return queryset.none()
        
        # PACIENTE solo puede ver sus propias solicitudes
        elif rol_upper == 'PACIENTE':
            try:
                paciente = user.paciente
                return queryset.filter(paciente=paciente)
            except:
                return queryset.none()
        
        # Usuario sin rol específico no ve nada
        return queryset.none()

    def get_serializer_class(self):
        """
        Retorna el serializer apropiado según la acción.
        """
        if self.action == 'create':
            return SolicitudCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return SolicitudUpdateSerializer
        elif self.action == 'list':
            return SolicitudListSerializer
        elif self.action == 'cambiar_estado':
            return SolicitudEstadoSerializer
        elif self.action == 'sincronizar_lims':
            return SolicitudLimsSerializer
        elif self.action == 'estadisticas':
            return SolicitudEstadisticasSerializer
        
        return SolicitudSerializer

    def perform_create(self, serializer):
        """
        Crea la solicitud y asigna el usuario que la crea.
        """
        user = self.request.user
        extra_kwargs = {
            'creado_por': user,
            'modificado_por': user,
        }
        # Si el usuario es médico y no se envió medico_solicitante, asignarlo automáticamente
        try:
            if not serializer.validated_data.get('medico_solicitante') and hasattr(user, 'medico') and user.medico:
                extra_kwargs['medico_solicitante'] = user.medico
        except Exception:
            pass

        solicitud = serializer.save(**extra_kwargs)
        log_create(actor=user, entity=solicitud, module="solicitudes", metadata={"view": "SolicitudViewSet.perform_create"})
        # Si hay selección de LIMS en el payload, enviar inmediatamente por el endpoint dedicado
        try:
            paneles = self.request.data.get('lims_paneles') or []
            tipos = self.request.data.get('lims_tipos_examen') or []
            if (paneles or tipos) and solicitud.tipo_solicitud == 'EXAMEN_LABORATORIO':
                payload = {
                    'external_id': str(solicitud.id),
                    'paciente_id': solicitud.paciente.id if solicitud.paciente else None,
                    'paciente_nombre': getattr(solicitud.paciente, 'nombre_completo', None) if solicitud.paciente else None,
                    'medico_id': solicitud.medico_solicitante.id if solicitud.medico_solicitante else None,
                    'medico_nombre': f"{getattr(solicitud.medico_solicitante, 'nombre', '')} {getattr(solicitud.medico_solicitante, 'apellido', '')}".strip() if solicitud.medico_solicitante else None,
                    'prioridad': solicitud.prioridad,
                    'observaciones': solicitud.observaciones or solicitud.descripcion or '',
                    'paneles': paneles,
                    'tipos_examen': tipos,
                }
                result = lims_service.enviar_solicitud_a_lims(payload)
                if result and 'id' in result:
                    solicitud.lims_id = result.get('id')
                    solicitud.sincronizado_lims = True
                    solicitud.ultima_sincronizacion = timezone.now()
                    solicitud.save(update_fields=['lims_id', 'sincronizado_lims', 'ultima_sincronizacion'])
        except Exception:
            # No bloquear la creación por errores de LIMS
            pass

    def perform_update(self, serializer):
        """
        Actualiza la solicitud y asigna el usuario que la modifica.
        """
        before = safe_model_snapshot(self.get_object())
        instance = serializer.save(modificado_por=self.request.user)
        log_update(actor=self.request.user, entity=instance, before=before, module="solicitudes", metadata={"view": "SolicitudViewSet.perform_update"})

    @action(detail=True, methods=['patch'])
    def cambiar_estado(self, request, pk=None):
        """
        Cambia el estado de una solicitud específica.
        """
        solicitud = self.get_object()
        before = safe_model_snapshot(solicitud)
        serializer = self.get_serializer(solicitud, data=request.data, partial=True)
        
        if serializer.is_valid():
            instance = serializer.save(modificado_por=request.user)
            log_update(
                actor=request.user,
                entity=instance,
                before=before,
                module="solicitudes",
                metadata={"action": "cambiar_estado", "view": "SolicitudViewSet.cambiar_estado"},
            )
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def marcar_como_completada(self, request, pk=None):
        """
        Marca una solicitud como completada.
        """
        solicitud = self.get_object()
        before = safe_model_snapshot(solicitud)
        solicitud.marcar_como_completada()
        solicitud.modificado_por = request.user
        solicitud.save()
        log_update(
            actor=request.user,
            entity=solicitud,
            before=before,
            module="solicitudes",
            metadata={"action": "marcar_como_completada", "view": "SolicitudViewSet.marcar_como_completada"},
        )
        
        serializer = self.get_serializer(solicitud)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        """
        Cancela una solicitud.
        """
        solicitud = self.get_object()
        before = safe_model_snapshot(solicitud)
        solicitud.cancelar()
        solicitud.modificado_por = request.user
        solicitud.save()
        log_update(
            actor=request.user,
            entity=solicitud,
            before=before,
            module="solicitudes",
            metadata={"action": "cancelar", "view": "SolicitudViewSet.cancelar"},
        )
        
        serializer = self.get_serializer(solicitud)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def reabrir(self, request, pk=None):
        """
        Reabre una solicitud cancelada o completada.
        """
        solicitud = self.get_object()
        before = safe_model_snapshot(solicitud)
        solicitud.reabrir()
        solicitud.modificado_por = request.user
        solicitud.save()
        log_update(
            actor=request.user,
            entity=solicitud,
            before=before,
            module="solicitudes",
            metadata={"action": "reabrir", "view": "SolicitudViewSet.reabrir"},
        )
        
        serializer = self.get_serializer(solicitud)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def sincronizar_lims(self, request, pk=None):
        """
        Fuerza la sincronización con LIMS.
        """
        solicitud = self.get_object()
        
        # Solo para solicitudes de laboratorio
        if solicitud.tipo_solicitud == 'EXAMEN_LABORATORIO':
            solicitud._enviar_a_lims()
            solicitud.modificado_por = request.user
            solicitud.save()
        
        serializer = SolicitudLimsSerializer(solicitud)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def enviar_lims(self, request, pk=None):
        """
        Envía la solicitud al LIMS incluyendo selección de paneles y tipos de examen.
        Acepta en body: paneles: [ids|codigos], tipos_examen: [ids|codigos]
        """
        solicitud = self.get_object()

        if solicitud.tipo_solicitud != 'EXAMEN_LABORATORIO':
            return Response({'detail': 'Solo válido para EXAMEN_LABORATORIO'}, status=status.HTTP_400_BAD_REQUEST)

        paneles = request.data.get('paneles') or []
        tipos = request.data.get('tipos_examen') or []

        # Construir nombres legibles
        paciente_nombre = None
        if solicitud.paciente:
            paciente_nombre = getattr(solicitud.paciente, 'nombre_completo', None) or f"{getattr(solicitud.paciente, 'nombre', '')} {getattr(solicitud.paciente, 'apellido', '')}".strip()
        medico_nombre = None
        if solicitud.medico_solicitante:
            medico_nombre = f"{getattr(solicitud.medico_solicitante, 'nombre', '')} {getattr(solicitud.medico_solicitante, 'apellido', '')}".strip()

        payload = {
            'external_id': str(solicitud.id),
            'paciente_id': solicitud.paciente.id if solicitud.paciente else None,
            'paciente_nombre': paciente_nombre,
            'medico_id': solicitud.medico_solicitante.id if solicitud.medico_solicitante else None,
            'medico_nombre': medico_nombre,
            'prioridad': solicitud.prioridad,
            'observaciones': solicitud.observaciones or solicitud.descripcion or '',
            'paneles': paneles,
            'tipos_examen': tipos,
        }

        result = lims_service.enviar_solicitud_a_lims(payload)
        if result and 'id' in result:
            solicitud.lims_id = result.get('id')
            solicitud.sincronizado_lims = True
            solicitud.ultima_sincronizacion = timezone.now()
            solicitud.save(update_fields=['lims_id', 'sincronizado_lims', 'ultima_sincronizacion'])
            return Response({'lims_id': solicitud.lims_id, 'status': 'ok'})

        return Response({'detail': 'No se pudo enviar al LIMS'}, status=status.HTTP_502_BAD_GATEWAY)

    @action(detail=False, methods=['get'])
    def estadisticas(self, request):
        """
        Retorna estadísticas de solicitudes.
        """
        queryset = self.get_queryset()
        
        # Estadísticas básicas
        total_solicitudes = queryset.count()
        solicitudes_pendientes = queryset.filter(estado='PENDIENTE').count()
        solicitudes_en_proceso = queryset.filter(estado='EN_PROCESO').count()
        solicitudes_completadas = queryset.filter(estado='COMPLETADA').count()
        solicitudes_canceladas = queryset.filter(estado='CANCELADA').count()
        solicitudes_vencidas = queryset.filter(
            Q(fecha_limite__lt=timezone.now()) & 
            ~Q(estado__in=['COMPLETADA', 'CANCELADA'])
        ).count()
        solicitudes_sincronizadas_lims = queryset.filter(sincronizado_lims=True).count()
        
        # Estadísticas por tipo
        por_tipo = dict(queryset.values('tipo_solicitud').annotate(
            count=Count('id')
        ).values_list('tipo_solicitud', 'count'))
        
        # Estadísticas por prioridad
        por_prioridad = dict(queryset.values('prioridad').annotate(
            count=Count('id')
        ).values_list('prioridad', 'count'))
        
        # Solicitudes recientes (últimas 10)
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
        """
        Retorna solo las solicitudes pendientes.
        """
        queryset = self.get_queryset().filter(estado='PENDIENTE')
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = SolicitudListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = SolicitudListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def vencidas(self, request):
        """
        Retorna las solicitudes vencidas.
        """
        queryset = self.get_queryset().filter(
            Q(fecha_limite__lt=timezone.now()) & 
            ~Q(estado__in=['COMPLETADA', 'CANCELADA'])
        )
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = SolicitudListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = SolicitudListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def mias(self, request):
        """
        Retorna las solicitudes del usuario autenticado.
        """
        user = request.user
        queryset = self.get_queryset()
        
        if user.rol == 'MEDICO':
            try:
                medico = user.medico
                queryset = queryset.filter(
                    Q(medico_solicitante=medico) | 
                    Q(medicos_asignados=medico)
                ).distinct()
            except:
                queryset = queryset.none()
        elif user.rol == 'PACIENTE':
            try:
                paciente = user.paciente
                queryset = queryset.filter(paciente=paciente)
            except:
                queryset = queryset.none()
        
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = SolicitudListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = SolicitudListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def proximas_vencer(self, request):
        """
        Retorna las solicitudes que vencen en los próximos 7 días.
        """
        fecha_limite = timezone.now() + timedelta(days=7)
        queryset = self.get_queryset().filter(
            Q(fecha_limite__lte=fecha_limite) & 
            Q(fecha_limite__gt=timezone.now()) &
            ~Q(estado__in=['COMPLETADA', 'CANCELADA'])
        ).order_by('fecha_limite')
        
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = SolicitudListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = SolicitudListSerializer(queryset, many=True)
        return Response(serializer.data)
