"""BI / indicadores de calidad operativos."""
from __future__ import annotations

from datetime import datetime, time, timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.permissions import get_normalized_role


def _parse_date(value: str | None, default):
    if not value:
        return default
    return datetime.strptime(value, "%Y-%m-%d").date()


def _percentile(sorted_vals: list[float], p: float) -> float | None:
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return round(sorted_vals[0], 2)
    k = (len(sorted_vals) - 1) * p
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return round(sorted_vals[f], 2)
    return round(sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f), 2)


class BiKpisView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        role = get_normalized_role(request.user)
        allowed = {"admin", "bioquimico", "secretaria", "laboratorio"}
        if not request.user.is_superuser and role not in allowed:
            return Response({"detail": "Sin permiso."}, status=403)

        hoy = timezone.localdate()
        desde = _parse_date(request.query_params.get("desde"), hoy - timedelta(days=30))
        hasta = _parse_date(request.query_params.get("hasta"), hoy)
        start = timezone.make_aware(datetime.combine(desde, time.min))
        end = timezone.make_aware(datetime.combine(hasta, time.max))

        payload: dict = {"desde": desde.isoformat(), "hasta": hasta.isoformat()}

        include_lims = role in {"admin", "bioquimico", "laboratorio"} or request.user.is_superuser
        include_ops = role in {"admin", "bioquimico", "secretaria"} or request.user.is_superuser

        if include_lims:
            payload["lims"] = self._lims_kpis(start, end)
        if include_ops:
            payload["turnos"] = self._turnos_kpis(start, end)
            payload["internacion"] = self._internacion_kpis()

        return Response(payload)

    def _lims_kpis(self, start, end):
        from laboratorio.models import ResultadoExamen, SolicitudExamen
        from laboratorio.models_catalog import Muestra

        solicitudes = SolicitudExamen.objects.filter(fecha_solicitud__gte=start, fecha_solicitud__lte=end)
        tats = []
        for s in solicitudes.prefetch_related("resultados"):
            fechas = [
                r.fecha_validacion
                for r in s.resultados.all()
                if r.fecha_validacion
            ]
            if not fechas or not s.fecha_solicitud:
                continue
            delta = (max(fechas) - s.fecha_solicitud).total_seconds() / 3600.0
            if delta >= 0:
                tats.append(delta)
        tats.sort()

        muestras = Muestra.objects.filter(created_at__gte=start, created_at__lte=end)
        total_m = muestras.count()
        rechazadas = muestras.filter(estado="RECHAZADA")
        n_rech = rechazadas.count()
        top_motivos = list(
            rechazadas.exclude(motivo_rechazo__isnull=True)
            .exclude(motivo_rechazo="")
            .values("motivo_rechazo")
            .annotate(total=Count("id"))
            .order_by("-total")[:10]
        )

        validados = ResultadoExamen.objects.filter(
            fecha_validacion__gte=start,
            fecha_validacion__lte=end,
            fecha_validacion__isnull=False,
        )
        por_dia = list(
            validados.annotate(dia=TruncDate("fecha_validacion"))
            .values("dia")
            .annotate(total=Count("id"))
            .order_by("dia")
        )
        por_usuario = list(
            validados.values("validado_por__username")
            .annotate(total=Count("id"))
            .order_by("-total")[:20]
        )

        return {
            "tat_horas": {
                "p50": _percentile(tats, 0.5),
                "p90": _percentile(tats, 0.9),
                "n": len(tats),
            },
            "rechazo_muestras": {
                "total": total_m,
                "rechazadas": n_rech,
                "tasa": round(n_rech / total_m, 4) if total_m else 0,
                "top_motivos": top_motivos,
            },
            "productividad": {
                "por_dia": [
                    {"dia": (x["dia"].isoformat() if x["dia"] else None), "total": x["total"]}
                    for x in por_dia
                ],
                "por_usuario": [
                    {
                        "usuario": x["validado_por__username"] or "—",
                        "total": x["total"],
                    }
                    for x in por_usuario
                ],
            },
            "ordenes_en_rango": solicitudes.count(),
        }

    def _turnos_kpis(self, start, end):
        from turnos.models import Turno

        turnos = Turno.objects.filter(fecha_hora_inicio__gte=start, fecha_hora_inicio__lte=end)
        total = turnos.count()
        cancelados = turnos.filter(estado="CANCELADO")
        no_show_ids = set()
        try:
            from auditoria.models import AuditEvent

            events = AuditEvent.objects.filter(
                module="turnos",
                created_at__gte=start,
                created_at__lte=end,
            )
            for ev in events.iterator():
                meta = ev.metadata or {}
                if meta.get("accion") == "marcar_no_asistio":
                    eid = meta.get("turno_id") or getattr(ev, "object_id", None)
                    if eid:
                        no_show_ids.add(int(eid))
        except Exception:
            pass

        # Nota: Turno.notas_administrativas se eliminó en turnos.0005;
        # el no-show se detecta solo vía AuditEvent (marcar_no_asistio).

        n_ns = len(no_show_ids)
        return {
            "total_programados": total,
            "cancelados": cancelados.count(),
            "no_shows": n_ns,
            "tasa_no_show": round(n_ns / total, 4) if total else 0,
        }

    def _internacion_kpis(self):
        try:
            from internacion.models import Cama, Internacion
        except Exception:
            return {"error": "módulo internacion no disponible"}

        por_estado = list(Cama.objects.values("estado").annotate(total=Count("id")))
        total = sum(x["total"] for x in por_estado) or 0
        ocupadas = next((x["total"] for x in por_estado if x["estado"] == "OCUPADA"), 0)
        return {
            "camas_por_estado": {x["estado"]: x["total"] for x in por_estado},
            "ocupacion_pct": round(100.0 * ocupadas / total, 1) if total else 0,
            "internaciones_activas": Internacion.objects.filter(activo=True).count(),
        }
