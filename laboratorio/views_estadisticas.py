"""API Estadísticas LIMS — volúmenes agregados (sin PHI)."""

from __future__ import annotations

import csv
import io

from django.http import HttpResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.permissions import get_normalized_role
from laboratorio import estadisticas as stats
from usuarios.roles import ROLES_ESTADISTICAS_LIMS


def _allowed(user) -> bool:
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if user.is_superuser:
        return True
    return get_normalized_role(user) in ROLES_ESTADISTICAS_LIMS


class EstadisticasLimsMixin:
    permission_classes = [IsAuthenticated]

    def _deny(self):
        return Response({'detail': 'Sin permiso.'}, status=status.HTTP_403_FORBIDDEN)

    def _parse(self, request):
        try:
            desde, hasta, start, end = stats.parse_rango(request.query_params)
        except ValueError as exc:
            return None, Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return (desde, hasta, start, end, request.query_params), None


class EstadisticasResumenView(EstadisticasLimsMixin, APIView):
    """GET /api/lab/estadisticas/resumen/"""

    def get(self, request):
        if not _allowed(request.user):
            return self._deny()
        parsed, err = self._parse(request)
        if err:
            return err
        desde, hasta, start, end, params = parsed
        payload = stats.resumen(start, end, params)
        payload['desde'] = desde.isoformat()
        payload['hasta'] = hasta.isoformat()
        return Response(payload)


class EstadisticasSeriesView(EstadisticasLimsMixin, APIView):
    """GET /api/lab/estadisticas/series/?granularidad=dia|mes|anio"""

    def get(self, request):
        if not _allowed(request.user):
            return self._deny()
        parsed, err = self._parse(request)
        if err:
            return err
        desde, hasta, start, end, params = parsed
        try:
            granularidad = stats.parse_granularidad(params)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        payload = stats.series(start, end, params, granularidad)
        payload['desde'] = desde.isoformat()
        payload['hasta'] = hasta.isoformat()
        return Response(payload)


class EstadisticasPorExamenView(EstadisticasLimsMixin, APIView):
    """GET /api/lab/estadisticas/por-examen/"""

    def get(self, request):
        if not _allowed(request.user):
            return self._deny()
        parsed, err = self._parse(request)
        if err:
            return err
        desde, hasta, start, end, params = parsed
        payload = stats.por_examen(start, end, params)
        payload['desde'] = desde.isoformat()
        payload['hasta'] = hasta.isoformat()
        return Response(payload)


class EstadisticasPorObraSocialView(EstadisticasLimsMixin, APIView):
    """GET /api/lab/estadisticas/por-obra-social/"""

    def get(self, request):
        if not _allowed(request.user):
            return self._deny()
        parsed, err = self._parse(request)
        if err:
            return err
        desde, hasta, start, end, params = parsed
        payload = stats.por_obra_social(start, end, params)
        payload['desde'] = desde.isoformat()
        payload['hasta'] = hasta.isoformat()
        return Response(payload)


class EstadisticasPorOrigenView(EstadisticasLimsMixin, APIView):
    """GET /api/lab/estadisticas/por-origen/"""

    def get(self, request):
        if not _allowed(request.user):
            return self._deny()
        parsed, err = self._parse(request)
        if err:
            return err
        desde, hasta, start, end, params = parsed
        payload = stats.por_origen(start, end, params)
        payload['desde'] = desde.isoformat()
        payload['hasta'] = hasta.isoformat()
        return Response(payload)


class EstadisticasPorEstadoView(EstadisticasLimsMixin, APIView):
    """GET /api/lab/estadisticas/por-estado/"""

    def get(self, request):
        if not _allowed(request.user):
            return self._deny()
        parsed, err = self._parse(request)
        if err:
            return err
        desde, hasta, start, end, params = parsed
        payload = stats.por_estado(start, end, params)
        payload['desde'] = desde.isoformat()
        payload['hasta'] = hasta.isoformat()
        return Response(payload)


class EstadisticasExportCsvView(EstadisticasLimsMixin, APIView):
    """GET /api/lab/estadisticas/export.csv/?dimension=examen|obra_social|origen|estado|serie"""

    def get(self, request):
        if not _allowed(request.user):
            return self._deny()
        parsed, err = self._parse(request)
        if err:
            return err
        desde, hasta, start, end, params = parsed
        dimension = (params.get('dimension') or 'examen').lower()
        try:
            rows = stats.export_rows(start, end, params, dimension)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        buf = io.StringIO()
        if not rows:
            writer = csv.writer(buf)
            writer.writerow(['sin_datos'])
        else:
            fieldnames = list(rows[0].keys())
            writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

        resp = HttpResponse(buf.getvalue(), content_type='text/csv; charset=utf-8')
        resp['Content-Disposition'] = (
            f'attachment; filename="estadisticas_lims_{dimension}_{desde}_{hasta}.csv"'
        )
        return resp
