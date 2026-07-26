"""ViewSets QC Westgard."""
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from api.permissions import LimsQcPermission
from laboratorio.models_qc import (
    Calibracion,
    CorridaQC,
    EquipoAnalizador,
    LoteControl,
    MaterialControl,
)
from laboratorio.qc_service import evaluar_y_guardar_punto, finalizar_corrida, levey_jennings_series
from laboratorio.serializers_qc import (
    CalibracionSerializer,
    CorridaQCSerializer,
    EquipoAnalizadorSerializer,
    LoteControlSerializer,
    MaterialControlSerializer,
    PuntoQCSerializer,
)


class EquipoAnalizadorViewSet(viewsets.ModelViewSet):
    queryset = EquipoAnalizador.objects.all()
    serializer_class = EquipoAnalizadorSerializer
    permission_classes = [LimsQcPermission]
    filterset_fields = ["activo", "area", "seccion"]
    ordering = ["codigo"]


class MaterialControlViewSet(viewsets.ModelViewSet):
    queryset = MaterialControl.objects.select_related("tipo_examen").all()
    serializer_class = MaterialControlSerializer
    permission_classes = [LimsQcPermission]
    filterset_fields = ["activo", "tipo_examen", "nivel"]
    ordering = ["nombre"]

    @action(detail=True, methods=["get"], url_path="levey-jennings")
    def levey_jennings(self, request, pk=None):
        material = self.get_object()
        return Response(levey_jennings_series(material))


class LoteControlViewSet(viewsets.ModelViewSet):
    queryset = LoteControl.objects.select_related("material").all()
    serializer_class = LoteControlSerializer
    permission_classes = [LimsQcPermission]
    filterset_fields = ["material", "activo"]
    ordering = ["-vencimiento"]

    def get_queryset(self):
        qs = super().get_queryset()
        mid = self.request.query_params.get("material_id")
        if mid:
            qs = qs.filter(material_id=mid)
        return qs

    @action(detail=True, methods=["get"], url_path="levey-jennings")
    def levey_jennings(self, request, pk=None):
        lote = self.get_object()
        return Response(levey_jennings_series(lote.material))


class CorridaQCViewSet(viewsets.ModelViewSet):
    queryset = CorridaQC.objects.select_related(
        "lote_control", "lote_control__material", "equipo"
    ).prefetch_related("puntos")
    serializer_class = CorridaQCSerializer
    permission_classes = [LimsQcPermission]
    ordering = ["-fecha"]

    def perform_create(self, serializer):
        valor = serializer.validated_data.pop("valor", None)
        fecha = serializer.validated_data.get("fecha") or timezone.now()
        corrida = serializer.save(
            operador=self.request.user if self.request.user.is_authenticated else None,
            fecha=fecha,
        )
        if valor is not None:
            evaluar_y_guardar_punto(corrida, valor)
            finalizar_corrida(corrida)

    @action(detail=True, methods=["post"])
    def puntos(self, request, pk=None):
        corrida = self.get_object()
        valor = request.data.get("valor")
        if valor is None:
            return Response({"detail": "valor requerido"}, status=400)
        punto = evaluar_y_guardar_punto(corrida, valor)
        finalizar_corrida(corrida)
        return Response(
            {"punto": PuntoQCSerializer(punto).data, "corrida": CorridaQCSerializer(corrida).data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def finalizar(self, request, pk=None):
        corrida = finalizar_corrida(self.get_object())
        return Response(CorridaQCSerializer(corrida).data)


class CalibracionViewSet(viewsets.ModelViewSet):
    queryset = Calibracion.objects.select_related("equipo").all()
    serializer_class = CalibracionSerializer
    permission_classes = [LimsQcPermission]
    filterset_fields = ["equipo"]
    ordering = ["-fecha"]

    def perform_create(self, serializer):
        serializer.save(
            realizada_por=self.request.user if self.request.user.is_authenticated else None
        )
