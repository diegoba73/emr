"""
API unificada de resolución / recepción por código de barras LIMS.
"""
from __future__ import annotations

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from api.permissions import LimsCodigoPermission
from laboratorio.lab_codigo import (
    LabCodigoError,
    resolver_entidad,
    serialize_resolve_payload,
)
from laboratorio.microbiologia_estado import MicrobiologiaAccionError, aplicar_iniciar_estudio
from laboratorio.muestra_estado import (
    MuestraAccionError,
    aplicar_recibir,
    extraccion_completa,
    tubos_pendientes_extraccion,
)
from laboratorio.serializers_muestras import MuestraRecibirPorCodigoSerializer


class LabCodigoViewSet(viewsets.ViewSet):
    """
    Escaneo unificado: tubos LAB-…-nn / MUE-… y microbiología LAB-… / MICB-… / MIC-….
    """

    permission_classes = [LimsCodigoPermission]

    @action(detail=False, methods=["get"], url_path=r"por-codigo/(?P<codigo>[^/]+)")
    def por_codigo(self, request, codigo=None):
        try:
            result = resolver_entidad(codigo)
        except LabCodigoError as exc:
            http = (
                status.HTTP_400_BAD_REQUEST
                if getattr(exc, "code", "") in ("invalid", "need_tubo_suffix")
                else status.HTTP_404_NOT_FOUND
            )
            return Response({"error": str(exc), "code": getattr(exc, "code", None)}, status=http)

        if result.tipo == "tubo" and result.muestra is not None:
            self.check_object_permissions(request, result.muestra)
        elif result.tipo == "micro" and result.estudio is not None:
            self.check_object_permissions(request, result.estudio)

        return Response(
            serialize_resolve_payload(result, request=request),
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="recibir-por-codigo")
    def recibir_por_codigo(self, request):
        ser = MuestraRecibirPorCodigoSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        codigo = ser.validated_data["codigo_barra"]
        try:
            result = resolver_entidad(codigo)
        except LabCodigoError as exc:
            http = (
                status.HTTP_400_BAD_REQUEST
                if getattr(exc, "code", "") in ("invalid", "need_tubo_suffix")
                else status.HTTP_404_NOT_FOUND
            )
            return Response({"error": str(exc), "code": getattr(exc, "code", None)}, status=http)

        if result.tipo == "tubo":
            muestra = result.muestra
            assert muestra is not None
            self.check_object_permissions(request, muestra)
            try:
                muestra = aplicar_recibir(
                    muestra.pk,
                    actor=request.user,
                    view="LabCodigoViewSet.recibir_por_codigo",
                    observaciones=ser.validated_data.get("observaciones") or "",
                    ubicacion_actual=ser.validated_data.get("ubicacion_actual") or "Laboratorio",
                )
            except MuestraAccionError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            result.muestra = muestra
            sid = muestra.solicitud_id
            pendientes = tubos_pendientes_extraccion(sid)
            extra = {
                "extraccion_completa": extraccion_completa(sid),
                "tubos_pendientes_extraccion": [
                    {
                        "id": p.pk,
                        "codigo_barra": p.codigo_barra,
                        "tipo_contenedor_codigo": (
                            p.tipo_contenedor.codigo if p.tipo_contenedor_id else None
                        ),
                        "tipo_contenedor_nombre": (
                            p.tipo_contenedor.nombre if p.tipo_contenedor_id else None
                        ),
                    }
                    for p in pendientes
                ],
            }
            return Response(
                serialize_resolve_payload(result, request=request, extra=extra),
                status=status.HTTP_200_OK,
            )

        estudio = result.estudio
        assert estudio is not None
        self.check_object_permissions(request, estudio)
        try:
            estudio = aplicar_iniciar_estudio(
                estudio.pk,
                actor=request.user,
                view="LabCodigoViewSet.recibir_por_codigo",
            )
        except MicrobiologiaAccionError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        result.estudio = estudio
        return Response(
            serialize_resolve_payload(result, request=request),
            status=status.HTTP_200_OK,
        )
