from __future__ import annotations

import logging
import os

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import FileResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from pacientes.services import ensure_paciente_linked_to_user
from usuarios.roles import es_secretaria_institucional

from .models import MedicoTipoEstudio, PedidoEstudioPaciente, TipoEstudioSala
from .pedido_paciente import (
    agendar_pedido_estudio,
    crear_pedido_estudio_paciente,
    usuario_puede_gestionar_pedidos_estudio,
)
from .serializers_pedido import (
    AgendarPedidoEstudioSerializer,
    MedicoTipoEstudioSerializer,
    PedidoEstudioCreateSerializer,
    PedidoEstudioPacienteSerializer,
    TipoEstudioSalaSerializer,
)

logger = logging.getLogger(__name__)


def _rol(user) -> str:
    return str(getattr(user, 'rol', '') or '').lower()


def _puede_ver_pedido(user, pedido: PedidoEstudioPaciente) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser or _rol(user) == 'admin':
        return True
    if es_secretaria_institucional(user):
        return True
    if _rol(user) == 'paciente':
        pac = ensure_paciente_linked_to_user(user)
        return bool(pac and pac.pk == pedido.paciente_id)
    return False


class MedicoTipoEstudioViewSet(viewsets.ModelViewSet):
    queryset = MedicoTipoEstudio.objects.select_related('medico', 'tipo_estudio').all()
    serializer_class = MedicoTipoEstudioSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['medico', 'tipo_estudio']
    ordering = ['medico_id', 'tipo_estudio_id']
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def get_permissions(self):
        return super().get_permissions()

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.method in ('POST', 'DELETE') and not usuario_puede_gestionar_pedidos_estudio(
            request.user
        ):
            raise PermissionDenied('Solo secretaría o administración puede editar el catálogo.')


class TipoEstudioSalaViewSet(viewsets.ModelViewSet):
    queryset = TipoEstudioSala.objects.select_related('tipo_estudio', 'recurso').all()
    serializer_class = TipoEstudioSalaSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['tipo_estudio', 'recurso']
    ordering = ['tipo_estudio_id', 'recurso_id']
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.method in ('POST', 'DELETE') and not usuario_puede_gestionar_pedidos_estudio(
            request.user
        ):
            raise PermissionDenied('Solo secretaría o administración puede editar el catálogo.')


class PedidoEstudioPacienteViewSet(viewsets.ModelViewSet):
    serializer_class = PedidoEstudioPacienteSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['estado', 'origen_canal', 'paciente']
    ordering = ['-created_at', '-id']
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        user = self.request.user
        qs = PedidoEstudioPaciente.objects.select_related(
            'paciente', 'turno', 'estudio', 'estudio__tipo_estudio'
        )
        if user.is_superuser or _rol(user) == 'admin' or es_secretaria_institucional(user):
            return qs
        if _rol(user) == 'paciente':
            pac = ensure_paciente_linked_to_user(user)
            if not pac:
                return qs.none()
            return qs.filter(paciente=pac)
        return qs.none()

    def create(self, request, *args, **kwargs):
        if _rol(request.user) != 'paciente':
            raise PermissionDenied('Solo el paciente puede crear un pedido de estudio.')
        pac = ensure_paciente_linked_to_user(request.user)
        if not pac:
            raise ValidationError('Su usuario no tiene ficha de paciente vinculada.')
        ser = PedidoEstudioCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            pedido = crear_pedido_estudio_paciente(
                user=request.user,
                paciente=pac,
                foto=ser.validated_data['foto'],
                origen_canal=ser.validated_data.get(
                    'origen_canal', PedidoEstudioPaciente.OrigenCanal.PORTAL
                ),
                notas=ser.validated_data.get('notas', ''),
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict if hasattr(exc, 'message_dict') else exc.messages) from exc
        out = PedidoEstudioPacienteSerializer(pedido, context={'request': request})
        return Response(out.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        pedido = self.get_object()
        if not _puede_ver_pedido(request.user, pedido):
            raise NotFound()
        return super().retrieve(request, *args, **kwargs)

    @action(detail=True, methods=['get'], url_path='download-foto')
    def download_foto(self, request, pk=None):
        pedido = self.get_object()
        if not _puede_ver_pedido(request.user, pedido):
            raise NotFound()
        if not pedido.foto:
            raise NotFound('Sin foto.')
        nombre = os.path.basename(pedido.foto.name) or f'pedido-estudio-{pedido.pk}.jpg'
        response = FileResponse(pedido.foto.open('rb'), as_attachment=True)
        response['Content-Disposition'] = f'attachment; filename="{nombre}"'
        return response

    @action(detail=True, methods=['post'], url_path='agendar')
    def agendar(self, request, pk=None):
        if not usuario_puede_gestionar_pedidos_estudio(request.user):
            raise PermissionDenied('Solo secretaría puede agendar pedidos de estudio.')
        pedido = self.get_object()
        ser = AgendarPedidoEstudioSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            pedido = agendar_pedido_estudio(
                pedido,
                user=request.user,
                tipo_estudio=ser.validated_data['tipo_estudio'],
                medico=ser.validated_data['medico'],
                inicio=ser.validated_data['inicio'],
                horario_id=ser.validated_data.get('horario_id'),
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict if hasattr(exc, 'message_dict') else exc.messages) from exc
        out = PedidoEstudioPacienteSerializer(pedido, context={'request': request})
        return Response(out.data)
