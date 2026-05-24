from __future__ import annotations

import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from archivos_medicos.access import paciente_ids_vinculados_a_medico

from .access import (
    usuario_puede_crear_estudio,
    usuario_puede_descargar_archivo_estudio,
    usuario_puede_escribir_estudio,
    usuario_puede_ver_estudio,
    usuario_puede_ver_estudio_clinico,
)
from .models import ArchivoEstudioComplementario, EstudioComplementario, InformeEstudioComplementario
from .permissions import EstudioComplementarioPermission
from .serializers import (
    AgregarArchivoSerializer,
    AnularEstudioSerializer,
    ArchivoEstudioComplementarioSerializer,
    CrearInformeSerializer,
    EstudioComplementarioDetailSerializer,
    EstudioComplementarioListSerializer,
    InformeEstudioComplementarioSerializer,
    RectificarInformeSerializer,
)
from . import services

logger = logging.getLogger(__name__)

_DELETE_BLOCKED_DETAIL = 'La eliminación física de estudios complementarios no está permitida.'


class EstudioComplementarioViewSet(viewsets.ModelViewSet):
    queryset = EstudioComplementario.objects.select_related(
        'paciente',
        'tipo_estudio',
        'atencion',
        'consulta_hc',
        'medico_solicitante',
    ).all()
    permission_classes = [IsAuthenticated, EstudioComplementarioPermission]
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['paciente', 'estado', 'modalidad', 'atencion', 'consulta_hc']
    ordering_fields = ['created_at', 'fecha_solicitud', 'fecha_realizacion']
    ordering = ['-created_at']
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        rol = str(getattr(user, 'rol', '') or '').lower()

        paciente_id = self.request.query_params.get('paciente_id')
        if paciente_id:
            try:
                qs = qs.filter(paciente_id=int(paciente_id))
            except (ValueError, TypeError):
                pass

        if user.is_superuser or rol == 'admin':
            return qs

        if rol in ('secretaria', 'enfermeria', 'laboratorio'):
            return qs.none()

        if rol == 'medico':
            try:
                ids = paciente_ids_vinculados_a_medico(user.medico)
                return qs.filter(paciente_id__in=ids)
            except Exception:
                return qs.none()

        if rol == 'paciente':
            try:
                return qs.filter(
                    paciente_id=user.paciente.id,
                    estado=EstudioComplementario.Estado.ENTREGADO,
                )
            except Exception:
                return qs.none()

        return qs.none()

    def get_serializer_class(self):
        if self.action == 'list':
            return EstudioComplementarioListSerializer
        return EstudioComplementarioDetailSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        paciente = serializer.validated_data['paciente']
        if not usuario_puede_crear_estudio(request.user, paciente):
            raise PermissionDenied('No tiene permiso para crear estudios de este paciente.')
        estudio = services.crear_estudio(serializer.validated_data, user=request.user)
        out = EstudioComplementarioDetailSerializer(estudio, context={'request': request})
        return Response(out.data, status=status.HTTP_201_CREATED)

    def _reject_estado_patch(self, request):
        if 'estado' in request.data:
            return Response(
                {'estado': 'El estado no se modifica por PATCH; use las acciones dedicadas.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return None

    def update(self, request, *args, **kwargs):
        blocked = self._reject_estado_patch(request)
        if blocked:
            return blocked
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        estudio = services.actualizar_estudio(
            instance,
            serializer.validated_data,
            user=request.user,
        )
        return Response(self.get_serializer(estudio).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        return Response(
            {'detail': _DELETE_BLOCKED_DETAIL},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def _validation_error_response(self, exc):
        if hasattr(exc, 'message_dict'):
            return Response(exc.message_dict, status=status.HTTP_400_BAD_REQUEST)
        return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='marcar-realizado')
    def marcar_realizado(self, request, pk=None):
        estudio = self.get_object()
        if not usuario_puede_escribir_estudio(request.user):
            raise PermissionDenied()
        try:
            services.marcar_realizado(estudio, user=request.user)
        except DjangoValidationError as exc:
            return self._validation_error_response(exc)
        return Response(EstudioComplementarioDetailSerializer(estudio).data)

    @action(detail=True, methods=['post'], url_path='anular')
    def anular(self, request, pk=None):
        estudio = self.get_object()
        ser = AnularEstudioSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            services.anular_estudio(
                estudio,
                user=request.user,
                motivo=ser.validated_data['motivo_anulacion'],
            )
        except DjangoValidationError as exc:
            return self._validation_error_response(exc)
        return Response(EstudioComplementarioDetailSerializer(estudio).data)

    @action(detail=True, methods=['post'], url_path='entregar')
    def entregar(self, request, pk=None):
        estudio = self.get_object()
        try:
            services.entregar_estudio(estudio, user=request.user)
        except DjangoValidationError as exc:
            return self._validation_error_response(exc)
        return Response(EstudioComplementarioDetailSerializer(estudio).data)

    @action(detail=True, methods=['post'], url_path='agregar-archivo')
    def agregar_archivo(self, request, pk=None):
        estudio = self.get_object()
        ser = AgregarArchivoSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            vinculo = services.asociar_archivo(
                estudio,
                user=request.user,
                **ser.validated_data,
            )
        except DjangoValidationError as exc:
            return self._validation_error_response(exc)
        return Response(
            ArchivoEstudioComplementarioSerializer(vinculo, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['get'], url_path='archivos')
    def archivos(self, request, pk=None):
        estudio = self.get_object()
        qs = estudio.archivos_estudio.select_related('archivo_medico').all()
        data = ArchivoEstudioComplementarioSerializer(
            qs, many=True, context={'request': request}
        ).data
        return Response(data)

    @action(
        detail=True,
        methods=['get'],
        url_path=r'archivos/(?P<archivo_id>[^/.]+)/download',
    )
    def download_archivo(self, request, pk=None, archivo_id=None):
        estudio = EstudioComplementario.objects.filter(pk=pk).select_related('paciente').first()
        if not estudio:
            return Response({'detail': 'No encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        rol = str(getattr(request.user, 'rol', '') or '').lower()
        if rol == 'paciente':
            try:
                if estudio.paciente_id != request.user.paciente.id:
                    return Response({'detail': 'No encontrado.'}, status=status.HTTP_404_NOT_FOUND)
            except Exception:
                return Response({'detail': 'No encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        elif not usuario_puede_ver_estudio_clinico(request.user, estudio):
            return Response({'detail': 'No encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        if not usuario_puede_descargar_archivo_estudio(request.user, estudio):
            return Response(
                {'detail': 'No tiene permiso para descargar este archivo.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            vinculo = estudio.archivos_estudio.select_related('archivo_medico').get(pk=archivo_id)
        except ArchivoEstudioComplementario.DoesNotExist:
            return Response({'detail': 'No encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            return services.servir_descarga_archivo_estudio(vinculo, user=request.user)
        except DjangoValidationError as exc:
            return self._validation_error_response(exc)

    @action(detail=True, methods=['get', 'post'], url_path='informes')
    def informes(self, request, pk=None):
        estudio = self.get_object()
        if request.method == 'GET':
            qs = estudio.informes.all()
            return Response(
                InformeEstudioComplementarioSerializer(qs, many=True).data
            )
        if not usuario_puede_escribir_estudio(request.user):
            raise PermissionDenied()
        ser = CrearInformeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            informe = services.crear_informe(estudio, user=request.user, **ser.validated_data)
        except DjangoValidationError as exc:
            return self._validation_error_response(exc)
        return Response(
            InformeEstudioComplementarioSerializer(informe).data,
            status=status.HTTP_201_CREATED,
        )

    def _get_informe(self, estudio, informe_id):
        try:
            return estudio.informes.get(pk=informe_id)
        except InformeEstudioComplementario.DoesNotExist:
            raise ValidationError({'detail': 'Informe no encontrado.'})

    @action(
        detail=True,
        methods=['post'],
        url_path=r'informes/(?P<informe_id>[^/.]+)/emitir',
    )
    def emitir_informe(self, request, pk=None, informe_id=None):
        estudio = self.get_object()
        informe = self._get_informe(estudio, informe_id)
        medico = getattr(request.user, 'medico', None)
        try:
            services.emitir_informe(informe, user=request.user, medico=medico)
        except DjangoValidationError as exc:
            return self._validation_error_response(exc)
        return Response(InformeEstudioComplementarioSerializer(informe).data)

    @action(
        detail=True,
        methods=['post'],
        url_path=r'informes/(?P<informe_id>[^/.]+)/validar',
    )
    def validar_informe(self, request, pk=None, informe_id=None):
        estudio = self.get_object()
        informe = self._get_informe(estudio, informe_id)
        try:
            services.validar_informe(informe, user=request.user)
        except PermissionDenied:
            raise
        except DjangoValidationError as exc:
            return self._validation_error_response(exc)
        return Response(InformeEstudioComplementarioSerializer(informe).data)

    @action(
        detail=True,
        methods=['post'],
        url_path=r'informes/(?P<informe_id>[^/.]+)/rectificar',
    )
    def rectificar_informe(self, request, pk=None, informe_id=None):
        estudio = self.get_object()
        informe = self._get_informe(estudio, informe_id)
        ser = RectificarInformeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            nuevo = services.rectificar_informe(informe, user=request.user, **ser.validated_data)
        except DjangoValidationError as exc:
            return self._validation_error_response(exc)
        return Response(
            InformeEstudioComplementarioSerializer(nuevo).data,
            status=status.HTTP_201_CREATED,
        )
