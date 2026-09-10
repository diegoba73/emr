"""ViewSets de interfaz de analizadores."""
from __future__ import annotations

from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from api.permissions import LimsInstrumentPermission
from laboratorio.destroy_protected import ProtectedDestroyMixin
from laboratorio.instrumentos_auth import (
    CsrfExemptSessionAuthentication,
    InstrumentTokenAuthentication,
    actor_usuario,
)
from laboratorio.instrumentos_service import (
    IngestaItem,
    InstrumentoError,
    consulta_trabajo,
    ingestar_resultados,
    resolver_interfaz,
)
from laboratorio.models_instrumentos import (
    InterfazInstrumento,
    MapeoAnalitoInstrumento,
    MensajeInstrumento,
)
from laboratorio.serializers_instrumentos import (
    ConsultaTrabajoSerializer,
    IngestaSerializer,
    InterfazInstrumentoSerializer,
    MapeoAnalitoInstrumentoSerializer,
    MensajeInstrumentoSerializer,
)


class InterfazInstrumentoViewSet(ProtectedDestroyMixin, viewsets.ModelViewSet):
    queryset = InterfazInstrumento.objects.select_related("equipo").all()
    serializer_class = InterfazInstrumentoSerializer
    permission_classes = [LimsInstrumentPermission]
    filterset_fields = ["activo", "driver", "equipo"]
    ordering = ["driver", "nombre"]


class MapeoAnalitoInstrumentoViewSet(ProtectedDestroyMixin, viewsets.ModelViewSet):
    queryset = MapeoAnalitoInstrumento.objects.select_related("interfaz", "tipo_examen").all()
    serializer_class = MapeoAnalitoInstrumentoSerializer
    permission_classes = [LimsInstrumentPermission]
    filterset_fields = ["interfaz", "activo"]
    ordering = ["interfaz", "codigo_instrumento"]


class MensajeInstrumentoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MensajeInstrumento.objects.select_related(
        "interfaz", "muestra", "solicitud"
    ).all()
    serializer_class = MensajeInstrumentoSerializer
    permission_classes = [LimsInstrumentPermission]
    filterset_fields = ["interfaz", "estado", "direccion"]
    ordering = ["-created_at"]
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset()
        excepciones = self.request.query_params.get("excepciones")
        if excepciones in ("1", "true", "True"):
            qs = qs.exclude(estado=MensajeInstrumento.Estado.OK)
        return qs


class InstrumentoGatewayView(APIView):
    """consulta-trabajo / ingesta: token de gateway o sesión LIMS."""

    authentication_classes = [InstrumentTokenAuthentication, CsrfExemptSessionAuthentication]
    permission_classes = [LimsInstrumentPermission]

    def _resolver(self, data):
        return resolver_interfaz(
            interfaz_id=data.get("interfaz_id"),
            equipo_codigo=data.get("equipo_codigo") or None,
            driver=data.get("driver") or None,
        )


class ConsultaTrabajoView(InstrumentoGatewayView):
    def post(self, request):
        ser = ConsultaTrabajoSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        try:
            interfaz = self._resolver(data)
        except InstrumentoError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        wl = consulta_trabajo(
            sample_id=data["sample_id"],
            interfaz=interfaz,
            actor=actor_usuario(request.user),
            crudo=data.get("crudo") or "",
        )
        return Response(
            {
                "estado": wl.estado,
                "sample_id": wl.sample_id,
                "interfaz_id": wl.interfaz.id,
                "muestra_id": wl.muestra.pk if wl.muestra else None,
                "solicitud_id": wl.solicitud.pk if wl.solicitud else None,
                "numero_solicitud": wl.numero_solicitud,
                "detalle": wl.detalle,
                "analitos": [
                    {
                        "codigo_instrumento": a.codigo_instrumento,
                        "tipo_examen_codigo": a.tipo_examen_codigo,
                        "resultado_id": a.resultado_id,
                    }
                    for a in wl.analitos
                ],
            }
        )


class IngestaInstrumentoView(InstrumentoGatewayView):
    def post(self, request):
        ser = IngestaSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        try:
            interfaz = self._resolver(data)
        except InstrumentoError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        items = [
            IngestaItem(
                codigo_instrumento=it["codigo_instrumento"],
                valor=it["valor"],
                unidad=it.get("unidad") or "",
            )
            for it in data["resultados"]
        ]
        result = ingestar_resultados(
            sample_id=data["sample_id"],
            interfaz=interfaz,
            items=items,
            actor=actor_usuario(request.user),
            crudo=data.get("crudo") or "",
        )
        http_status = (
            status.HTTP_200_OK
            if result.estado == MensajeInstrumento.Estado.OK
            else status.HTTP_400_BAD_REQUEST
        )
        return Response(
            {
                "estado": result.estado,
                "sample_id": result.sample_id,
                "interfaz_id": result.interfaz.id,
                "muestra_id": result.muestra.pk if result.muestra else None,
                "solicitud_id": result.solicitud.pk if result.solicitud else None,
                "cargados": result.cargados,
                "sin_match": result.sin_match,
                "detalle": result.detalle,
            },
            status=http_status,
        )
