"""Ensayos recientes de internación (sugerencia al crear pedido)."""

from __future__ import annotations

from datetime import date

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from laboratorio.sugerencia_seguimiento_internacion import (
    DIAS_DEFAULT,
    ensayos_recientes_internacion,
)
from laboratorio.views_ultimos_resultados import (
    usuario_puede_ver_ultimos_resultados_paciente,
)
from pacientes.models import Paciente


class EnsayosRecientesInternacionView(APIView):
    """
    GET /api/lab/pacientes/{paciente_id}/ensayos-recientes-internacion/?dias=7&fecha_hasta=YYYY-MM-DD

    Ensayos pedidos en órdenes de internación en [fecha_hasta - dias, fecha_hasta]
    (incluye el mismo día del pedido en curso).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, paciente_id: int):
        if not usuario_puede_ver_ultimos_resultados_paciente(request.user, paciente_id):
            return Response(
                {"detail": "No tenés permiso para ver los pedidos de este paciente."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not Paciente.objects.filter(pk=paciente_id).exists():
            return Response(
                {"detail": "Paciente no encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )
        raw_dias = request.query_params.get("dias", str(DIAS_DEFAULT))
        try:
            dias = int(raw_dias)
        except (TypeError, ValueError):
            dias = DIAS_DEFAULT

        fecha_hasta: date | None = None
        raw_hasta = (request.query_params.get("fecha_hasta") or "").strip()
        if raw_hasta:
            try:
                fecha_hasta = date.fromisoformat(raw_hasta)
            except ValueError:
                return Response(
                    {"detail": "fecha_hasta inválida (usar YYYY-MM-DD)."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        data = ensayos_recientes_internacion(
            paciente_id, dias=dias, fecha_hasta=fecha_hasta
        )
        return Response(data, status=status.HTTP_200_OK)
