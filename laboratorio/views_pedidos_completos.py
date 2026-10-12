"""POST /api/lab/pedidos-completos/ — confirmación atómica de pedido médico/lab."""
from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.permissions import get_normalized_role
from laboratorio.pedidos_completos import crear_pedido_completo
from usuarios.roles import ROLES_LIMS_WRITE


class PedidoCompletoCreateView(APIView):
    """
    Único camino de confirmación médica multi-material.
    También usable desde UI lab (preferido para pedidos multi-material).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        role = get_normalized_role(request.user)
        if not request.user.is_superuser and role not in (
            *ROLES_LIMS_WRITE,
            "medico",
            "secretaria",
        ):
            return Response(
                {"detail": "No tiene permiso para confirmar pedidos de laboratorio."},
                status=status.HTTP_403_FORBIDDEN,
            )

        data = request.data if isinstance(request.data, dict) else {}
        idem_key = (
            request.headers.get("Idempotency-Key")
            or request.META.get("HTTP_IDEMPOTENCY_KEY")
            or data.get("idempotency_key")
            or ""
        ).strip() or None

        # Payload canónico para hash (sin la clave de idempotencia).
        payload_for_hash = {
            k: v for k, v in data.items() if k not in ("idempotency_key",)
        }

        try:
            result = crear_pedido_completo(
                user=request.user,
                paciente_id=data.get("paciente_id"),
                fecha_programada_toma=data.get("fecha_programada_toma"),
                solicitudes_lab=list(data.get("solicitudes_lab") or []),
                estudios_micro=list(data.get("estudios_micro") or []),
                medico_id=data.get("medico_id"),
                medico_externo_nombre=data.get("medico_externo_nombre") or "",
                consulta_hc_id=data.get("consulta_hc_id"),
                origen_solicitud=data.get("origen_solicitud") or "",
                observaciones=data.get("observaciones") or "",
                observaciones_micro=data.get("observaciones_micro") or "",
                obra_social=data.get("obra_social") or "",
                numero_afiliado=data.get("numero_afiliado") or "",
                afiliacion_id=data.get("afiliacion_id"),
                idempotency_key=idem_key,
                payload_for_hash=payload_for_hash,
            )
        except Exception as exc:
            from rest_framework.exceptions import ValidationError as DRFValidationError

            if isinstance(exc, DRFValidationError):
                detail = exc.detail
                # Conflicto de idempotencia → 409
                if isinstance(detail, dict) and detail.get("code") == "idempotency_conflict":
                    return Response(detail, status=status.HTTP_409_CONFLICT)
                return Response(detail, status=status.HTTP_400_BAD_REQUEST)
            raise

        return Response(result, status=status.HTTP_201_CREATED)
