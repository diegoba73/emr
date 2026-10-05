"""API de analítica poblacional LIMS (agregados, sin PHI)."""
from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.permissions import get_normalized_role
from laboratorio.analytics_resultados import analytics_analitos, parse_analytics_query
from usuarios.roles import ROLES_LIMS_WRITE


class AnalitosAnalyticsView(APIView):
    """
    GET /api/lab/analytics/analitos/?desde=&hasta=&codigo=

    Default ``hasta=2026-09-29``. Solo roles LIMS write / admin.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not user.is_superuser and get_normalized_role(user) not in ROLES_LIMS_WRITE:
            return Response(
                {"detail": "Solo laboratorio/bioquímico/admin."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            opts = parse_analytics_query(request.query_params)
        except ValueError:
            return Response(
                {"error": "Fechas inválidas. Usá YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = analytics_analitos(**opts)
        return Response(data, status=status.HTTP_200_OK)
