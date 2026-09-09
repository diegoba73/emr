"""ViewSets inventario LIMS."""
from django.db import transaction
from django.db.models import F
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from api.permissions import LimsInventarioPermission
from laboratorio.destroy_protected import ProtectedDestroyMixin
from laboratorio.inventario_service import alertas, registrar_ingreso
from laboratorio.models_inventario import (
    ConsumoInsumoExamen,
    InsumoLab,
    LoteInsumo,
    MovimientoStock,
)
from laboratorio.serializers_inventario import (
    ConsumoInsumoExamenSerializer,
    InsumoLabSerializer,
    LoteInsumoSerializer,
    MovimientoStockSerializer,
)


class InsumoLabViewSet(ProtectedDestroyMixin, viewsets.ModelViewSet):
    queryset = InsumoLab.objects.select_related(
        "tipo_contenedor", "medio_cultivo", "equipo"
    ).all()
    serializer_class = InsumoLabSerializer
    permission_classes = [LimsInventarioPermission]
    filterset_fields = [
        "tipo",
        "activo",
        "tipo_contenedor",
        "medio_cultivo",
        "canal_analizador",
        "composicion",
        "equipo",
    ]
    search_fields = ["codigo", "nombre", "proveedor"]
    ordering = ["codigo"]

    def get_queryset(self):
        qs = super().get_queryset()
        canal = self.request.query_params.get("canal")
        if canal:
            qs = qs.filter(canal_analizador=canal)
        return qs

    @action(detail=False, methods=["get"])
    def alertas(self, request):
        return Response(alertas())


class LoteInsumoViewSet(ProtectedDestroyMixin, viewsets.ModelViewSet):
    queryset = LoteInsumo.objects.select_related("insumo").all()
    serializer_class = LoteInsumoSerializer
    permission_classes = [LimsInventarioPermission]
    filterset_fields = ["insumo", "activo"]
    ordering = ["fecha_vencimiento", "id"]

    def get_queryset(self):
        qs = super().get_queryset()
        insumo_id = self.request.query_params.get("insumo_id")
        if insumo_id:
            qs = qs.filter(insumo_id=insumo_id)
        canal = self.request.query_params.get("canal")
        if canal:
            qs = qs.filter(insumo__canal_analizador=canal)
        return qs


class MovimientoStockViewSet(viewsets.ModelViewSet):
    queryset = MovimientoStock.objects.select_related("lote", "lote__insumo").all()
    serializer_class = MovimientoStockSerializer
    permission_classes = [LimsInventarioPermission]
    http_method_names = ["get", "post", "head", "options"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        lote_id = self.request.query_params.get("lote_id")
        insumo_id = self.request.query_params.get("insumo_id")
        canal = self.request.query_params.get("canal")
        if lote_id:
            qs = qs.filter(lote_id=lote_id)
        if insumo_id:
            qs = qs.filter(lote__insumo_id=insumo_id)
        if canal:
            qs = qs.filter(lote__insumo__canal_analizador=canal)
        return qs

    def create(self, request, *args, **kwargs):
        data = request.data
        lote_id = data.get("lote_id") or data.get("lote")
        tipo = data.get("tipo")
        cantidad = int(data.get("cantidad") or 0)
        motivo = data.get("motivo") or ""
        try:
            lote = LoteInsumo.objects.select_for_update().get(pk=lote_id)
        except LoteInsumo.DoesNotExist:
            return Response({"detail": "Lote no encontrado."}, status=status.HTTP_404_NOT_FOUND)

        with transaction.atomic():
            if tipo == MovimientoStock.Tipo.INGRESO:
                mov = registrar_ingreso(lote=lote, cantidad=cantidad, user=request.user, motivo=motivo)
            elif tipo in (MovimientoStock.Tipo.AJUSTE, MovimientoStock.Tipo.DESCARTE):
                if cantidad <= 0:
                    return Response({"detail": "Cantidad inválida."}, status=400)
                if lote.cantidad < cantidad and tipo == MovimientoStock.Tipo.DESCARTE:
                    return Response({"detail": "Stock insuficiente."}, status=400)
                if tipo == MovimientoStock.Tipo.DESCARTE:
                    LoteInsumo.objects.filter(pk=lote.pk).update(cantidad=F("cantidad") - cantidad)
                else:
                    LoteInsumo.objects.filter(pk=lote.pk).update(cantidad=cantidad)
                lote.refresh_from_db()
                mov = MovimientoStock.objects.create(
                    tipo=tipo,
                    lote=lote,
                    cantidad=cantidad,
                    motivo=motivo or tipo,
                    usuario=request.user,
                )
            else:
                return Response(
                    {"detail": "Use INGRESO, AJUSTE o DESCARTE (EGRESO es operativo)."},
                    status=400,
                )
        return Response(MovimientoStockSerializer(mov).data, status=status.HTTP_201_CREATED)


class ConsumoInsumoExamenViewSet(ProtectedDestroyMixin, viewsets.ModelViewSet):
    """Recetas examen → insumos (0..N SKUs físicos)."""

    queryset = ConsumoInsumoExamen.objects.select_related(
        "tipo_examen",
        "tipo_examen__equipo_analizador",
        "insumo",
        "insumo__equipo",
    ).all()
    serializer_class = ConsumoInsumoExamenSerializer
    permission_classes = [LimsInventarioPermission]
    filterset_fields = ["tipo_examen", "insumo", "activo"]
    ordering = ["tipo_examen_id", "id"]

    def get_queryset(self):
        qs = super().get_queryset()
        tipo_examen = self.request.query_params.get("tipo_examen_id") or self.request.query_params.get(
            "tipo_examen"
        )
        insumo = self.request.query_params.get("insumo_id") or self.request.query_params.get("insumo")
        equipo = self.request.query_params.get("equipo") or self.request.query_params.get(
            "equipo_codigo"
        )
        if tipo_examen:
            qs = qs.filter(tipo_examen_id=tipo_examen)
        if insumo:
            qs = qs.filter(insumo_id=insumo)
        if equipo:
            qs = qs.filter(tipo_examen__equipo_analizador__codigo__iexact=equipo)
        return qs
