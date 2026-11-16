"""Pedidos de estudio desde la app móvil (paciente + foto)."""

from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import PermissionDenied, ValidationError

from movil.authentication import AutenticacionMovil, RolMovil
from pacientes.services import ensure_paciente_linked_to_user
from estudios.models import PedidoEstudioPaciente
from estudios.pedido_paciente import crear_pedido_estudio_paciente
from estudios.serializers_pedido import PedidoEstudioCreateSerializer, PedidoEstudioPacienteSerializer


class PedidosEstudioMovil(APIView):
    authentication_classes = [AutenticacionMovil]
    permission_classes = [IsAuthenticated, RolMovil]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        if str(getattr(request.user, 'rol', '') or '').lower() != 'paciente':
            raise PermissionDenied('Solo el paciente consulta sus pedidos de estudio.')
        pac = ensure_paciente_linked_to_user(request.user)
        if not pac:
            return Response([])
        qs = PedidoEstudioPaciente.objects.filter(paciente=pac).order_by('-created_at')
        return Response(
            PedidoEstudioPacienteSerializer(qs, many=True, context={'request': request}).data
        )

    def post(self, request):
        if str(getattr(request.user, 'rol', '') or '').lower() != 'paciente':
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
                origen_canal=PedidoEstudioPaciente.OrigenCanal.MOVIL,
                notas=ser.validated_data.get('notas', ''),
            )
        except DjangoValidationError as exc:
            raise ValidationError(
                exc.message_dict if hasattr(exc, 'message_dict') else exc.messages
            ) from exc
        return Response(
            PedidoEstudioPacienteSerializer(pedido, context={'request': request}).data,
            status=201,
        )
