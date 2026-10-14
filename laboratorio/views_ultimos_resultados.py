"""Últimos resultados de laboratorio por paciente (vista de pedido médico)."""

from __future__ import annotations

from datetime import date

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.permissions import get_normalized_role
from laboratorio.analisis_longitudinal import (
    DIAS_ULTIMOS_RESULTADOS_DEFAULT,
    LIMIT_ULTIMOS_RESULTADOS_DEFAULT,
    ultimos_resultados_paciente,
)
from pacientes.models import Paciente
from usuarios.roles import ROLES_LIMS_OPERATIVA_LIMITADA, ROLES_LIMS_WRITE


def usuario_puede_ver_ultimos_resultados_paciente(user, paciente_id: int) -> bool:
    """Misma audiencia de lectura clínica LIMS (médico, lab, secretaría, enfermería)."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True
    role = get_normalized_role(user)
    if role in ROLES_LIMS_WRITE or role in ROLES_LIMS_OPERATIVA_LIMITADA or role == "medico":
        return True
    if role == "paciente":
        try:
            return int(user.paciente.id) == int(paciente_id)
        except Exception:
            return False
    return False


class UltimosResultadosPacienteView(APIView):
    """
    GET /api/lab/pacientes/{paciente_id}/ultimos-resultados/?dias=7&fecha_hasta=YYYY-MM-DD

    Analitos informados en la ventana (FINALIZADO / INFORMADO_PARCIAL),
    orden tipo informe PDF (paneles juntos).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, paciente_id: int):
        if not usuario_puede_ver_ultimos_resultados_paciente(request.user, paciente_id):
            return Response(
                {"detail": "No tenés permiso para ver los resultados de este paciente."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not Paciente.objects.filter(pk=paciente_id).exists():
            return Response(
                {"detail": "Paciente no encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        raw_dias = request.query_params.get("dias", str(DIAS_ULTIMOS_RESULTADOS_DEFAULT))
        try:
            dias = int(raw_dias)
        except (TypeError, ValueError):
            dias = DIAS_ULTIMOS_RESULTADOS_DEFAULT

        raw_limit = request.query_params.get(
            "limit", str(LIMIT_ULTIMOS_RESULTADOS_DEFAULT)
        )
        try:
            limit = int(raw_limit)
        except (TypeError, ValueError):
            limit = LIMIT_ULTIMOS_RESULTADOS_DEFAULT

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

        data = ultimos_resultados_paciente(
            paciente_id, dias=dias, fecha_hasta=fecha_hasta, limit=limit
        )
        return Response(data, status=status.HTTP_200_OK)
