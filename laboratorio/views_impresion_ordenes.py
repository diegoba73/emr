"""Impresión desde la bandeja de órdenes: listado del día y pedidos en formato papel."""
from __future__ import annotations

import logging

from django.http import HttpResponse
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.permissions import get_normalized_role
from laboratorio.impresion_ordenes_pdf import (
    ImpresionOrdenesError,
    auditar_impresion_ordenes,
    generar_listado_ordenes_dia_pdf_bytes,
    generar_pedidos_papel_pdf_bytes,
    parsear_items,
    parsear_resenas,
    resenas_sugeridas,
)
from usuarios.roles import ROLES_LIMS_WRITE

logger = logging.getLogger(__name__)


class LimsImpresionOrdenesPermission(permissions.BasePermission):
    """Operadores LIMS (listado del día, pedidos papel)."""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return get_normalized_role(user) in ROLES_LIMS_WRITE


class PedidosPapelImpresionPermission(permissions.BasePermission):
    """
    Pedidos institucionales (firma médico/paciente): operadores LIMS + médico.
    El listado del día sigue restringido a LIMS.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        rol = get_normalized_role(user)
        return rol in ROLES_LIMS_WRITE or rol == "medico"


def _pdf_response(pdf_bytes: bytes, filename: str) -> HttpResponse:
    resp = HttpResponse(pdf_bytes, content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp


def _fecha_label(raw) -> str:
    s = str(raw or "").strip()
    parts = s.split("-")
    if len(parts) == 3 and all(p.isdigit() for p in parts):
        return f"{parts[2]}/{parts[1]}/{parts[0]}"
    return ""


class ListadoOrdenesDiaPdfView(APIView):
    """POST {items: [{tipo, id}], fecha: 'YYYY-MM-DD'} → PDF del listado."""

    permission_classes = [LimsImpresionOrdenesPermission]

    def post(self, request):
        try:
            items = parsear_items(request.data.get("items"))
            pdf, _ = generar_listado_ordenes_dia_pdf_bytes(
                items, _fecha_label(request.data.get("fecha"))
            )
        except ImpresionOrdenesError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("generar listado ordenes dia PDF")
            return Response(
                {"error": "No se pudo generar el listado PDF."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        auditar_impresion_ordenes(
            actor=request.user,
            accion="lims_listado_ordenes_dia_pdf",
            items=items,
            view="ListadoOrdenesDiaPdfView",
        )
        return _pdf_response(pdf, "listado-ordenes-dia.pdf")


class ResenasSugeridasView(APIView):
    """
    POST {items: [{tipo, id}]} → {resenas: [...]} sugerencias editables para las
    órdenes clínicas con exámenes fuera del listado básico. No persiste.
    """

    permission_classes = [PedidosPapelImpresionPermission]

    def post(self, request):
        try:
            items = parsear_items(request.data.get("items"))
            resenas = resenas_sugeridas(items)
        except ImpresionOrdenesError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("sugerir reseñas de pedidos")
            return Response(
                {"error": "No se pudieron generar las reseñas."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        if resenas:
            auditar_impresion_ordenes(
                actor=request.user,
                accion="lims_resenas_sugeridas",
                items=items,
                view="ResenasSugeridasView",
                extra={
                    "resenas": [
                        {"solicitud_id": r["solicitud_id"], "fuente": r["fuente"]} for r in resenas
                    ],
                },
            )
        return Response({"resenas": resenas})


class PedidosPapelPdfView(APIView):
    """
    POST {items: [{tipo, id}], resenas?: [{solicitud_id, texto}]} → PDF A4 apaisado,
    2 formularios por hoja (pedido, reseña y proBNP cuando corresponde).
    """

    permission_classes = [PedidosPapelImpresionPermission]

    def post(self, request):
        try:
            items = parsear_items(request.data.get("items"))
            resenas = parsear_resenas(request.data.get("resenas"))
            pdf, _ = generar_pedidos_papel_pdf_bytes(items, resenas)
        except ImpresionOrdenesError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("generar pedidos papel PDF")
            return Response(
                {"error": "No se pudieron generar los pedidos PDF."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        auditar_impresion_ordenes(
            actor=request.user,
            accion="lims_pedidos_papel_pdf",
            items=items,
            view="PedidosPapelPdfView",
            extra={"resenas_revisadas_ids": sorted(resenas)} if resenas else None,
        )
        return _pdf_response(pdf, "pedidos-laboratorio.pdf")
