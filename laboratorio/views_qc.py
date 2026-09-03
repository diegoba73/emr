"""ViewSets QC Westgard."""
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DrfValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from api.permissions import LimsQcPermission
from laboratorio.models import SolicitudExamen, TipoExamen
from laboratorio.models_qc import (
    Calibracion,
    CorridaQC,
    EquipoAnalizador,
    LoteControl,
    LoteProductoControl,
    MaterialControl,
    ProductoControl,
    TargetLoteControl,
)
from laboratorio.qc_service import (
    aceptar_nivel_rapido,
    estado_iqc_solicitud,
    evaluar_y_guardar_punto,
    evaluar_y_guardar_punto_multiparam,
    finalizar_corrida,
    get_equipo_iqc_default,
    levey_jennings_por_examen,
    levey_jennings_series,
)
from laboratorio.serializers_qc import (
    CalibracionSerializer,
    CorridaQCSerializer,
    EquipoAnalizadorSerializer,
    LoteControlSerializer,
    LoteProductoControlSerializer,
    MaterialControlSerializer,
    ProductoControlSerializer,
    PuntoQCSerializer,
    TargetLoteControlSerializer,
)


class EquipoAnalizadorViewSet(viewsets.ModelViewSet):
    queryset = EquipoAnalizador.objects.all()
    serializer_class = EquipoAnalizadorSerializer
    permission_classes = [LimsQcPermission]
    filterset_fields = ["activo", "area", "seccion"]
    ordering = ["codigo"]


class ProductoControlViewSet(viewsets.ModelViewSet):
    queryset = ProductoControl.objects.select_related("equipo").all()
    serializer_class = ProductoControlSerializer
    permission_classes = [LimsQcPermission]
    filterset_fields = ["activo", "equipo", "modo"]
    ordering = ["equipo__codigo", "nombre"]


class LoteProductoControlViewSet(viewsets.ModelViewSet):
    queryset = (
        LoteProductoControl.objects.select_related("producto", "producto__equipo")
        .prefetch_related("targets__tipo_examen")
        .all()
    )
    serializer_class = LoteProductoControlSerializer
    permission_classes = [LimsQcPermission]
    filterset_fields = ["producto", "activo"]
    ordering = ["-vencimiento"]

    def get_queryset(self):
        qs = super().get_queryset()
        pid = self.request.query_params.get("producto_id")
        if pid:
            qs = qs.filter(producto_id=pid)
        return qs

    @action(detail=True, methods=["get", "put"], url_path="targets")
    def targets(self, request, pk=None):
        lote = self.get_object()
        if request.method == "GET":
            ser = TargetLoteControlSerializer(lote.targets.select_related("tipo_examen"), many=True)
            return Response(ser.data)
        rows = request.data if isinstance(request.data, list) else request.data.get("targets") or []
        if not isinstance(rows, list):
            return Response({"detail": "Se espera una lista de targets."}, status=400)
        saved = []
        for row in rows:
            te_id = row.get("tipo_examen")
            nivel = row.get("nivel")
            if not te_id or not nivel:
                continue
            obj, _ = TargetLoteControl.objects.update_or_create(
                lote=lote,
                tipo_examen_id=te_id,
                nivel=nivel,
                defaults={
                    "media_target": row.get("media_target"),
                    "de_target": row.get("de_target"),
                },
            )
            saved.append(obj)
        return Response(TargetLoteControlSerializer(saved, many=True).data)


class TargetLoteControlViewSet(viewsets.ModelViewSet):
    queryset = TargetLoteControl.objects.select_related("lote", "tipo_examen").all()
    serializer_class = TargetLoteControlSerializer
    permission_classes = [LimsQcPermission]
    filterset_fields = ["lote", "tipo_examen", "nivel"]
    ordering = ["tipo_examen__codigo", "nivel"]


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
        "lote_control",
        "lote_control__material",
        "lote_producto",
        "lote_producto__producto",
        "equipo",
    ).prefetch_related("puntos", "puntos__tipo_examen")
    serializer_class = CorridaQCSerializer
    permission_classes = [LimsQcPermission]
    ordering = ["-fecha"]

    def perform_create(self, serializer):
        valor = serializer.validated_data.pop("valor", None)
        modo = serializer.validated_data.pop("modo", None)
        valores = serializer.validated_data.pop("valores", None) or []
        fecha = serializer.validated_data.get("fecha") or timezone.now()
        if serializer.validated_data.get("equipo") is None:
            lote_prod = serializer.validated_data.get("lote_producto")
            lote_mat = serializer.validated_data.get("lote_control")
            eq = None
            if lote_prod is not None:
                if not hasattr(lote_prod, "producto"):
                    lote_prod = LoteProductoControl.objects.select_related("producto__equipo").get(
                        pk=lote_prod.pk if hasattr(lote_prod, "pk") else lote_prod
                    )
                eq = lote_prod.producto.equipo
            elif lote_mat is not None:
                if not hasattr(lote_mat, "material"):
                    lote_mat = LoteControl.objects.select_related("material__equipo").get(pk=lote_mat)
                eq = lote_mat.material.equipo
            serializer.validated_data["equipo"] = eq or get_equipo_iqc_default()
        corrida = serializer.save(
            operador=self.request.user if self.request.user.is_authenticated else None,
            fecha=fecha,
        )
        lote_producto = corrida.lote_producto
        try:
            if lote_producto is not None:
                if modo == "VALORES":
                    for item in valores:
                        te = TipoExamen.objects.get(pk=item["tipo_examen"])
                        evaluar_y_guardar_punto_multiparam(corrida, te, item["valor"])
                    finalizar_corrida(corrida)
                else:
                    aceptar_nivel_rapido(corrida)
                return
            if valor is not None:
                evaluar_y_guardar_punto(corrida, valor)
                finalizar_corrida(corrida)
        except TipoExamen.DoesNotExist as e:
            raise DrfValidationError({"tipo_examen": "Examen inexistente."}) from e
        except ValueError as e:
            raise DrfValidationError({"detail": str(e)}) from e

    @action(detail=True, methods=["post"])
    def puntos(self, request, pk=None):
        corrida = self.get_object()
        valor = request.data.get("valor")
        if valor is None:
            return Response({"detail": "valor requerido"}, status=400)
        if corrida.lote_producto_id:
            te_id = request.data.get("tipo_examen")
            if not te_id:
                return Response(
                    {"detail": "tipo_examen requerido en corrida multiparámetro."}, status=400
                )
            te = get_object_or_404(TipoExamen, pk=te_id)
            punto = evaluar_y_guardar_punto_multiparam(corrida, te, valor)
        else:
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


class IqcPrecheckView(APIView):
    """GET ?solicitud=<id> | POST {solicitud_ids: [...]} batch para bandeja."""

    permission_classes = [LimsQcPermission]

    def get(self, request):
        sid = request.query_params.get("solicitud")
        if not sid:
            return Response({"detail": "Parámetro solicitud requerido."}, status=400)
        solicitud = get_object_or_404(SolicitudExamen, pk=sid)
        data = estado_iqc_solicitud(solicitud)
        data["solicitud_id"] = solicitud.id
        return Response(data)

    def post(self, request):
        raw_ids = request.data.get("solicitud_ids") or []
        if not isinstance(raw_ids, list) or not raw_ids:
            return Response({"detail": "solicitud_ids debe ser una lista no vacía."}, status=400)
        ids: list[int] = []
        for x in raw_ids[:100]:
            try:
                ids.append(int(x))
            except (TypeError, ValueError):
                continue
        if not ids:
            return Response({"detail": "solicitud_ids inválidos."}, status=400)
        qs = SolicitudExamen.objects.filter(pk__in=ids).prefetch_related(
            "tipos_examen", "paneles__tipos_examen", "resultados"
        )
        by_id = {s.id: s for s in qs}
        results = []
        for sid in ids:
            sol = by_id.get(sid)
            if not sol:
                results.append(
                    {
                        "solicitud_id": sid,
                        "ok": True,
                        "aplicable": False,
                        "problemas": [],
                        "equipo": None,
                    }
                )
                continue
            data = estado_iqc_solicitud(sol)
            data["solicitud_id"] = sid
            results.append(data)
        return Response({"results": results})


class LeveyJenningsExamenView(APIView):
    """GET ?tipo_examen=<id> — serie LJ unificada (multiparámetro + por ensayo)."""

    permission_classes = [LimsQcPermission]

    def get(self, request):
        tid = request.query_params.get("tipo_examen")
        if not tid:
            return Response({"detail": "Parámetro tipo_examen requerido."}, status=400)
        examen = get_object_or_404(TipoExamen, pk=tid)
        return Response(levey_jennings_por_examen(examen))
