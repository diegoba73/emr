"""API Filtros avanzados (cohortes por exámenes)."""
from __future__ import annotations

from datetime import date

from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.permissions import get_normalized_role
from laboratorio.cohortes_filtros import (
    escribir_xlsx_bytes,
    filas_ancho,
    paciente_ids_por_filtro,
    resumen_filtro,
)
from usuarios.roles import ROLES_LIMS_WRITE

_ROLES_FILTROS = frozenset({*ROLES_LIMS_WRITE, "medico"})


def _puede_filtros(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return get_normalized_role(user) in _ROLES_FILTROS


def _parse_body(data) -> tuple[list[str], str, list[str], date | None, date | None]:
    raw_codigos = data.get("codigos") or []
    raw_examenes = data.get("examenes")
    obligatorios: list[str] = []

    if isinstance(raw_examenes, list) and raw_examenes and isinstance(raw_examenes[0], dict):
        codigos = []
        for item in raw_examenes:
            c = str(item.get("codigo") or "").strip()
            if not c:
                continue
            codigos.append(c)
            if item.get("obligatorio"):
                obligatorios.append(c)
    else:
        if isinstance(raw_codigos, str):
            raw_codigos = [c.strip() for c in raw_codigos.split(",") if c.strip()]
        if not isinstance(raw_codigos, list):
            raise ValueError("codigos debe ser una lista")
        codigos = [str(c).strip() for c in raw_codigos if str(c).strip()]
        raw_obl = data.get("obligatorios") or []
        if isinstance(raw_obl, str):
            raw_obl = [c.strip() for c in raw_obl.split(",") if c.strip()]
        if not isinstance(raw_obl, list):
            raise ValueError("obligatorios debe ser una lista")
        obligatorios = [str(c).strip() for c in raw_obl if str(c).strip()]

    modo = str(data.get("modo") or "all").strip().lower()
    if modo in ("todos", "and", "all"):
        modo = "all"
    elif modo in ("algunos", "or", "any"):
        modo = "any"
    else:
        raise ValueError("modo debe ser 'all' (Todos) o 'any' (Algunos)")

    desde = date.fromisoformat(str(data["desde"])) if data.get("desde") else None
    hasta = date.fromisoformat(str(data["hasta"])) if data.get("hasta") else None
    return codigos, modo, obligatorios, desde, hasta


class FiltrosAvanzadosPreviewView(APIView):
    """
    POST /api/lab/filtros-avanzados/preview/
    Body: {
      codigos: [...],
      obligatorios?: [...],  # solo aplica en modo any
      modo: "all"|"any",
      desde?, hasta?
    }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not _puede_filtros(request.user):
            return Response(
                {"detail": "No tenés permiso para filtros avanzados."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            codigos, modo, obligatorios, desde, hasta = _parse_body(request.data)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if not codigos:
            return Response(
                {"error": "Seleccioná al menos un examen."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = resumen_filtro(
            codigos,
            modo=modo,
            obligatorios=obligatorios if modo == "any" else None,
            desde=desde,
            hasta=hasta,
        )
        return Response(data, status=status.HTTP_200_OK)


class FiltrosAvanzadosExcelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not _puede_filtros(request.user):
            return Response(
                {"detail": "No tenés permiso para filtros avanzados."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            codigos, modo, obligatorios, desde, hasta = _parse_body(request.data)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if not codigos:
            return Response(
                {"error": "Seleccioná al menos un examen."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        obl = obligatorios if modo == "any" else []
        ids = paciente_ids_por_filtro(
            codigos, modo=modo, obligatorios=obl, desde=desde, hasta=hasta
        )
        # Filas: en Todos exige todos los códigos en la orden; en Algunos con
        # obligatorios exige solo esos (el resto rellena columna si está).
        if modo == "all":
            req_fila = codigos
        elif obl:
            req_fila = obl
        else:
            req_fila = []
        rows = filas_ancho(
            codigos, ids, requeridos=req_fila, desde=desde, hasta=hasta
        )
        if modo == "all":
            modo_txt = "Todos"
            obl_txt = ", ".join(codigos)
        else:
            modo_txt = "Algunos"
            obl_txt = (
                ", ".join(obl)
                if obl
                else "(ninguno — OR puro; opcionales no filtraron)"
            )
        meta = {
            "generado": timezone.localtime().strftime("%Y-%m-%d %H:%M"),
            "modo": modo_txt,
            "codigos": ", ".join(codigos),
            "obligatorios": obl_txt,
            "desde": desde.isoformat() if desde else "(sin piso)",
            "hasta": hasta.isoformat() if hasta else "(sin techo)",
            "pacientes": len(ids),
            "filas": len(rows),
            "nota": (
                "Contiene DNI — uso local/estudio. No publicar. "
                "Columnas opcionales vacías si esa orden no tenía el examen."
            ),
        }
        content = escribir_xlsx_bytes(codigos, rows, meta=meta)
        stamp = timezone.localtime().strftime("%Y%m%d_%H%M")
        filename = f"filtros_avanzados_{stamp}.xlsx"
        resp = HttpResponse(
            content,
            content_type=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        )
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp
