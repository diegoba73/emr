import logging
import os
from datetime import timedelta

from django.db import transaction
from django.http import FileResponse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from auditoria.audit_service import log_event
from auditoria.snapshot import safe_model_snapshot

from api.permissions import CanWriteArchivoMedico

from .access import medico_puede_acceder_paciente, paciente_ids_vinculados_a_medico
from pacientes.models import Paciente
from .models import ArchivoMedico
from .serializers import ArchivoMedicoListSerializer, ArchivoMedicoSerializer

logger = logging.getLogger(__name__)

_DELETE_BLOCKED_DETAIL = (
    'La eliminación física de archivos clínicos no está permitida.'
)


def _safe_audit(callable_, *args, **kwargs):
    try:
        callable_(*args, **kwargs)
    except Exception:  # pragma: no cover
        logger.exception(
            'Fallo silencioso en auditoría: %s',
            getattr(callable_, '__name__', 'audit'),
        )


class ArchivoMedicoViewSet(viewsets.ModelViewSet):
    """Archivos médicos: descarga autenticada, sin URL /media/ en API, DELETE bloqueado."""

    queryset = ArchivoMedico.objects.select_related(
        'paciente', 'consulta', 'atencion', 'subido_por'
    ).all()
    serializer_class = ArchivoMedicoSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['paciente', 'consulta', 'atencion', 'tipo_archivo', 'es_urgente', 'fecha_estudio']
    search_fields = ['titulo', 'descripcion', 'paciente__nombre', 'paciente__apellido']
    ordering_fields = ['fecha_subida', 'fecha_estudio', 'titulo']
    ordering = ['-fecha_subida']

    def get_queryset(self):
        queryset = super().get_queryset()
        paciente_id = self.request.query_params.get('paciente_id')
        atencion_id = self.request.query_params.get('atencion_id')
        if paciente_id:
            try:
                queryset = queryset.filter(paciente_id=int(paciente_id))
            except (ValueError, TypeError):
                pass
        if atencion_id:
            try:
                queryset = queryset.filter(atencion_id=int(atencion_id))
            except (ValueError, TypeError):
                pass

        user = self.request.user
        rol = str(getattr(user, 'rol', '') or '').lower()

        if user.is_superuser or rol == 'admin':
            return queryset

        if rol in ('secretaria', 'enfermeria', 'laboratorio'):
            return queryset.none()

        if rol == 'medico':
            try:
                medico = user.medico
            except Exception:
                return queryset.none()
            ids = paciente_ids_vinculados_a_medico(medico)
            return queryset.filter(paciente_id__in=ids)

        if rol == 'paciente':
            try:
                return queryset.filter(paciente=user.paciente)
            except Exception:
                return queryset.none()

        return queryset.none()

    def get_serializer_class(self):
        if self.action == 'list':
            return ArchivoMedicoListSerializer
        return ArchivoMedicoSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update'):
            return [IsAuthenticated(), CanWriteArchivoMedico()]
        return [IsAuthenticated()]

    def _validar_paciente_escritura(self, user, paciente_id: int) -> None:
        rol = str(getattr(user, 'rol', '') or '').lower()
        if user.is_superuser or rol == 'admin':
            return
        if rol == 'paciente':
            try:
                if user.paciente.id != paciente_id:
                    raise PermissionDenied('No puede subir archivos para otro paciente.')
            except PermissionDenied:
                raise
            except Exception as exc:
                raise PermissionDenied('Paciente no vinculado.') from exc
            return
        if rol == 'medico':
            try:
                paciente = Paciente.objects.get(pk=paciente_id)
            except Paciente.DoesNotExist as exc:
                raise PermissionDenied('Paciente no encontrado.') from exc
            if not medico_puede_acceder_paciente(user.medico, paciente):
                raise PermissionDenied(
                    'No puede subir archivos para pacientes sin vínculo clínico.'
                )
            return
        raise PermissionDenied('No tiene permiso para subir archivos clínicos.')

    def perform_create(self, serializer):
        user = self.request.user
        self._validar_paciente_escritura(user, serializer.validated_data['paciente_id'])

        with transaction.atomic():
            instance = serializer.save(subido_por=user)
            _safe_audit(
                log_event,
                action='CREATE',
                actor=user,
                entity=instance,
                after=safe_model_snapshot(instance),
                entity_repr=f'{instance._meta.label}:{instance.pk}',
                module='archivos_medicos',
                metadata={
                    'accion': 'archivo_medico_create',
                    'view': 'ArchivoMedicoViewSet',
                    'tipo': instance.tipo_archivo,
                },
            )

    def perform_update(self, serializer):
        paciente_id = serializer.validated_data.get(
            'paciente_id', serializer.instance.paciente_id
        )
        self._validar_paciente_escritura(self.request.user, paciente_id)
        before = safe_model_snapshot(serializer.instance)
        with transaction.atomic():
            instance = serializer.save()
            _safe_audit(
                log_event,
                action='UPDATE',
                actor=self.request.user,
                entity=instance,
                before=before,
                after=safe_model_snapshot(instance),
                entity_repr=f'{instance._meta.label}:{instance.pk}',
                module='archivos_medicos',
                metadata={
                    'accion': 'archivo_medico_update',
                    'view': 'ArchivoMedicoViewSet',
                    'tipo': instance.tipo_archivo,
                },
            )

    def destroy(self, request, *args, **kwargs):
        return Response(
            {'detail': _DELETE_BLOCKED_DETAIL},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def _tiene_permiso_lectura(self, user, archivo):
        rol = str(getattr(user, 'rol', '') or '').lower()
        if user.is_superuser or rol == 'admin':
            return True
        if rol in ('secretaria', 'enfermeria', 'laboratorio'):
            return False
        if rol == 'medico':
            try:
                return medico_puede_acceder_paciente(user.medico, archivo.paciente)
            except Exception:
                return False
        if rol == 'paciente':
            try:
                return archivo.paciente_id == user.paciente.id
            except Exception:
                return False
        return False

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        archivo = self.get_object()
        if not self._tiene_permiso_lectura(request.user, archivo):
            return Response(
                {'detail': 'No tiene permiso para descargar este archivo.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not archivo.archivo:
            return Response(
                {'detail': 'Archivo no encontrado en el servidor.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            storage_path = archivo.archivo.path
        except Exception:
            return Response(
                {'detail': 'Archivo no encontrado en el servidor.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not os.path.exists(storage_path):
            logger.error('Archivo clínico ausente en almacenamiento')
            return Response(
                {'detail': 'Archivo no encontrado en el servidor.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        _safe_audit(
            log_event,
            action='UPDATE',
            actor=request.user,
            entity=archivo,
            after=safe_model_snapshot(archivo),
            entity_repr=f'{archivo._meta.label}:{archivo.pk}',
            module='archivos_medicos',
            metadata={
                'accion': 'archivo_medico_download',
                'view': 'ArchivoMedicoViewSet.download',
                'tipo': archivo.tipo_archivo,
            },
        )

        try:
            response = FileResponse(
                open(storage_path, 'rb'),
                content_type='application/octet-stream',
            )
            nombre_descarga = os.path.basename(archivo.archivo.name) or 'archivo'
            nombre_descarga = nombre_descarga.replace('"', '_')
            response['Content-Disposition'] = f'attachment; filename="{nombre_descarga}"'
            return response
        except Exception:
            logger.exception('Error al servir descarga de archivo clínico')
            return Response(
                {'detail': 'Error al procesar el archivo.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=['get'])
    def tipos_disponibles(self, request):
        tipos = ArchivoMedico.TIPO_CHOICES
        return Response([{'value': c[0], 'label': c[1]} for c in tipos])

    @action(detail=False, methods=['get'])
    def estadisticas(self, request):
        if not (
            request.user.is_superuser
            or str(getattr(request.user, 'rol', '') or '').lower() == 'admin'
        ):
            return Response(
                {'detail': 'No tiene permisos para ver estadísticas.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        queryset = self.get_queryset()
        stats = {
            'total_archivos': queryset.count(),
            'por_tipo': {},
            'urgentes': queryset.filter(es_urgente=True).count(),
            'recientes': queryset.filter(
                fecha_subida__gte=timezone.now() - timedelta(days=7)
            ).count(),
        }
        for choice in ArchivoMedico.TIPO_CHOICES:
            stats['por_tipo'][choice[0]] = queryset.filter(tipo_archivo=choice[0]).count()
        return Response(stats)


@api_view(['GET'])
@permission_classes([AllowAny])
def tipos_archivo_publicos(request):
    """Catálogo estático de tipos (sin PHI)."""
    tipos = ArchivoMedico.TIPO_CHOICES
    return Response([{'value': c[0], 'label': c[1]} for c in tipos])
