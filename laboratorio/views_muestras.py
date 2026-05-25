"""
ViewSets LIMS Fase B0 (catálogos) y B1 (muestras transaccionales).
"""
from __future__ import annotations

import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from api.permissions import (
    LimsB0CatalogPermission,
    LimsMuestraTransaccionalPermission,
    get_normalized_role,
)
from auditoria.audit_service import log_update
from auditoria.snapshot import safe_model_snapshot
from laboratorio.models_catalog import AreaLaboratorio, Muestra, SeccionLaboratorio, TipoContenedor
from laboratorio.muestra_estado import (
    MuestraAccionError,
    aplicar_cancelar,
    aplicar_cambiar_ubicacion,
    aplicar_conservar,
    aplicar_descartar,
    aplicar_rechazar,
    aplicar_recibir,
    aplicar_tomar,
    crear_muestra,
    registrar_evento_actualizacion_admin,
)
from laboratorio.serializers_muestras import (
    AreaLaboratorioSerializer,
    EventoMuestraSerializer,
    MuestraCancelarSerializer,
    MuestraCambiarUbicacionSerializer,
    MuestraConservarSerializer,
    MuestraCreateSerializer,
    MuestraDescartarSerializer,
    MuestraPartialUpdateSerializer,
    MuestraRechazarSerializer,
    MuestraRecibirSerializer,
    MuestraSerializer,
    MuestraTomarSerializer,
    SeccionLaboratorioSerializer,
    TipoContenedorSerializer,
)

logger = logging.getLogger(__name__)


class AreaLaboratorioViewSet(viewsets.ModelViewSet):
    queryset = AreaLaboratorio.objects.all().order_by("nombre")
    serializer_class = AreaLaboratorioSerializer
    permission_classes = [LimsB0CatalogPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["codigo", "nombre"]
    ordering_fields = ["codigo", "nombre", "created_at"]

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "No se permite eliminar áreas; desactive con activo=false."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )


class SeccionLaboratorioViewSet(viewsets.ModelViewSet):
    queryset = SeccionLaboratorio.objects.select_related("area").all().order_by("area", "nombre")
    serializer_class = SeccionLaboratorioSerializer
    permission_classes = [LimsB0CatalogPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["codigo", "nombre", "area__codigo"]
    ordering_fields = ["codigo", "nombre", "created_at"]

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "No se permite eliminar secciones; desactive con activo=false."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )


class TipoContenedorViewSet(viewsets.ModelViewSet):
    queryset = TipoContenedor.objects.all().order_by("nombre")
    serializer_class = TipoContenedorSerializer
    permission_classes = [LimsB0CatalogPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["codigo", "nombre", "aditivo"]
    ordering_fields = ["codigo", "nombre", "created_at"]

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "No se permite eliminar contenedores; desactive con activo=false."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )


class MuestraTransaccionalViewSet(viewsets.ModelViewSet):
    """
    Muestra física vinculada a SolicitudExamen.
    El estado solo cambia por acciones POST explícitas.
    """

    queryset = Muestra.objects.select_related(
        "solicitud",
        "solicitud__medico_interno",
        "paciente",
        "tipo_muestra",
        "tipo_contenedor",
    ).prefetch_related("eventos")
    permission_classes = [LimsMuestraTransaccionalPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["codigo_barra", "solicitud__numero"]
    ordering_fields = ["created_at", "fecha_toma", "fecha_recepcion", "estado"]
    ordering = ["-created_at"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_serializer_class(self):
        if self.action == "create":
            return MuestraCreateSerializer
        if self.action in ("partial_update", "update"):
            return MuestraPartialUpdateSerializer
        return MuestraSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_authenticated:
            return qs.none()
        if user.is_superuser:
            return qs
        role = get_normalized_role(user)
        if role in ("admin", "laboratorio"):
            return qs
        if role == "medico":
            return qs.filter(solicitud__medico_interno__user=user)
        return qs.none()

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        vd = ser.validated_data
        sol = vd["_solicitud"]
        try:
            with transaction.atomic():
                muestra = crear_muestra(
                    solicitud=sol,
                    tipo_muestra_id=vd["tipo_muestra_id"],
                    tipo_contenedor_id=vd.get("tipo_contenedor_id"),
                    observaciones=vd.get("observaciones") or "",
                    codigo_barra=vd.get("codigo_barra"),
                    actor=request.user,
                    view="MuestraTransaccionalViewSet.create",
                )
        except DjangoValidationError as e:
            return Response({"error": e.messages if hasattr(e, "messages") else str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("crear muestra")
            return Response({"error": "No se pudo crear la muestra."}, status=status.HTTP_400_BAD_REQUEST)
        out = MuestraSerializer(muestra, context=self.get_serializer_context())
        return Response(out.data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        instance = serializer.instance
        before = safe_model_snapshot(instance)
        estado_prev = instance.estado
        serializer.save()
        instance.refresh_from_db()
        after = safe_model_snapshot(instance)
        if before != after:
            registrar_evento_actualizacion_admin(
                instance,
                actor=self.request.user,
                view="MuestraTransaccionalViewSet.partial_update",
                estado_anterior=str(estado_prev),
            )
            log_update(
                actor=self.request.user,
                entity=instance,
                before=before,
                module="laboratorio",
                metadata={
                    "accion": "ACTUALIZADA",
                    "muestra_id": instance.pk,
                    "codigo_barra": instance.codigo_barra,
                    "solicitud_id": instance.solicitud_id,
                    "numero_solicitud": instance.solicitud.numero,
                    "view": "MuestraTransaccionalViewSet.partial_update",
                },
            )

    def _run_accion(self, request, pk, fn, view_label: str, **extra):
        try:
            muestra = fn(int(pk), actor=request.user, view=view_label, **extra)
        except Muestra.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except MuestraAccionError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(MuestraSerializer(muestra, context={"request": request}).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="tomar")
    def tomar(self, request, pk=None):
        ser = MuestraTomarSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return self._run_accion(
            request,
            pk,
            aplicar_tomar,
            "MuestraTransaccionalViewSet.tomar",
            observaciones=ser.validated_data.get("observaciones") or "",
        )

    @action(detail=True, methods=["post"], url_path="recibir")
    def recibir(self, request, pk=None):
        ser = MuestraRecibirSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return self._run_accion(
            request,
            pk,
            aplicar_recibir,
            "MuestraTransaccionalViewSet.recibir",
            observaciones=ser.validated_data.get("observaciones") or "",
            ubicacion_actual=ser.validated_data.get("ubicacion_actual") or "",
        )

    @action(detail=True, methods=["post"], url_path="rechazar")
    def rechazar(self, request, pk=None):
        ser = MuestraRechazarSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return self._run_accion(
            request,
            pk,
            aplicar_rechazar,
            "MuestraTransaccionalViewSet.rechazar",
            motivo_rechazo=ser.validated_data.get("motivo_rechazo") or "",
            observaciones=ser.validated_data.get("observaciones") or "",
        )

    @action(detail=True, methods=["post"], url_path="conservar")
    def conservar(self, request, pk=None):
        ser = MuestraConservarSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return self._run_accion(
            request,
            pk,
            aplicar_conservar,
            "MuestraTransaccionalViewSet.conservar",
            ubicacion_actual=ser.validated_data.get("ubicacion_actual") or "",
            observaciones=ser.validated_data.get("observaciones") or "",
        )

    @action(detail=True, methods=["post"], url_path="descartar")
    def descartar(self, request, pk=None):
        ser = MuestraDescartarSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return self._run_accion(
            request,
            pk,
            aplicar_descartar,
            "MuestraTransaccionalViewSet.descartar",
            observaciones=ser.validated_data.get("observaciones") or "",
        )

    @action(detail=True, methods=["post"], url_path="cambiar-ubicacion")
    def cambiar_ubicacion(self, request, pk=None):
        ser = MuestraCambiarUbicacionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return self._run_accion(
            request,
            pk,
            aplicar_cambiar_ubicacion,
            "MuestraTransaccionalViewSet.cambiar_ubicacion",
            ubicacion_actual=ser.validated_data.get("ubicacion") or "",
            observaciones=ser.validated_data.get("observaciones") or "",
        )

    @action(detail=True, methods=["get"], url_path="eventos")
    def eventos(self, request, pk=None):
        muestra = self.get_object()
        qs = muestra.eventos.all().order_by("-fecha", "-id")
        return Response(EventoMuestraSerializer(qs, many=True).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="cancelar")
    def cancelar(self, request, pk=None):
        ser = MuestraCancelarSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return self._run_accion(
            request,
            pk,
            aplicar_cancelar,
            "MuestraTransaccionalViewSet.cancelar",
            motivo=ser.validated_data.get("motivo") or "",
            observaciones=ser.validated_data.get("observaciones") or "",
        )
