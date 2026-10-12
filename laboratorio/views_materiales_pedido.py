"""API de materiales de pedido (mapa clínico + micro)."""

from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from laboratorio.materiales_pedido_catalogo import as_api_list


class MaterialesPedidoListView(APIView):
    """GET: lista de materiales de pedido (SoT) para la UI de Nueva orden."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(as_api_list())
