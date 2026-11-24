"""Pedidos de estudio desde la app móvil (solo lectura histórica para el paciente)."""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework.exceptions import PermissionDenied

from movil.authentication import AutenticacionMovil, RolMovil
from pacientes.services import ensure_paciente_linked_to_user
from estudios.models import PedidoEstudioPaciente
from estudios.serializers_pedido import PedidoEstudioPacienteSerializer


class PedidosEstudioMovil(APIView):
    authentication_classes = [AutenticacionMovil]
    permission_classes = [IsAuthenticated, RolMovil]

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
        raise PermissionDenied(
            'Los turnos de estudio solo los agenda secretaría '
            '(presencial o por teléfono). No se aceptan pedidos desde la app.'
        )
