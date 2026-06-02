"""
ViewSets de microbiología base — LIMS Fase B3.1.

Endpoints expuestos bajo ``/api/lab/microbiologia/...`` y alias
``/api/laboratorio/microbiologia/...`` (mismas clases ViewSet).
"""
from __future__ import annotations

import logging

from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from api.permissions import (
    LimsMicrobiologiaCatalogPermission,
    LimsMicrobiologiaInformePermission,
    LimsMicrobiologiaPermission,
    get_normalized_role,
)
from auditoria.audit_service import log_create, log_update
from auditoria.snapshot import safe_model_snapshot
from laboratorio.microbiologia_estado import (
    MicrobiologiaAccionError,
    assert_estudio_micro_operable,
    actualizar_informe_borrador,
    actualizar_resultado_antibiotico,
    aplicar_anular_informe,
    aplicar_cancelar_antibiograma,
    aplicar_cancelar_estudio,
    aplicar_completar_antibiograma,
    aplicar_descartar_aislado,
    aplicar_emitir_informe,
    aplicar_iniciar_estudio,
    aplicar_marcar_estudio_informado,
    aplicar_validar_informe_final,
    crear_aislado,
    crear_antibiograma,
    crear_estudio,
    crear_identificacion,
    crear_informe_borrador,
    crear_lectura,
    crear_resultado_antibiotico,
    crear_siembra,
)
from laboratorio.models_microbiologia import (
    AisladoMicrobiologico,
    Antibiograma,
    Antibiotico,
    EstudioMicrobiologia,
    IdentificacionMicroorganismo,
    InformeMicrobiologia,
    LecturaCultivo,
    MedioCultivo,
    Microorganismo,
    ResultadoAntibiotico,
    SiembraMicrobiologia,
)
from laboratorio.serializers_microbiologia import (
    AisladoDescartarSerializer,
    AisladoMicrobiologicoCreateSerializer,
    AisladoMicrobiologicoPartialUpdateSerializer,
    AisladoMicrobiologicoSerializer,
    AntibiogramaCancelarSerializer,
    AntibiogramaCompletarSerializer,
    AntibiogramaCreateSerializer,
    AntibiogramaPartialUpdateSerializer,
    AntibiogramaSerializer,
    AntibioticoSerializer,
    EstudioCancelarSerializer,
    EstudioIniciarSerializer,
    EstudioMarcarInformadoSerializer,
    EstudioMicrobiologiaCreateSerializer,
    EstudioMicrobiologiaPartialUpdateSerializer,
    EstudioMicrobiologiaSerializer,
    IdentificacionMicroorganismoCreateSerializer,
    IdentificacionMicroorganismoSerializer,
    InformeAnularSerializer,
    InformeMicrobiologiaCreateSerializer,
    InformeMicrobiologiaPartialUpdateSerializer,
    InformeMicrobiologiaSerializer,
    InformeValidarSerializer,
    LecturaCultivoCreateSerializer,
    LecturaCultivoPartialUpdateSerializer,
    LecturaCultivoSerializer,
    MedioCultivoSerializer,
    MicroorganismoSerializer,
    ResultadoAntibioticoCreateSerializer,
    ResultadoAntibioticoPartialUpdateSerializer,
    ResultadoAntibioticoSerializer,
    SiembraMicrobiologiaCreateSerializer,
    SiembraMicrobiologiaPartialUpdateSerializer,
    SiembraMicrobiologiaSerializer,
)

logger = logging.getLogger(__name__)


def _guard_estudio_micro_operable_entity(entity) -> None:
    """Bloquea PATCH técnicos si el estudio asociado está cerrado."""
    if isinstance(entity, EstudioMicrobiologia):
        estudio = entity
    elif hasattr(entity, "estudio"):
        estudio = entity.estudio
    elif hasattr(entity, "antibiograma"):
        estudio = entity.antibiograma.aislado.estudio
    elif hasattr(entity, "aislado"):
        estudio = entity.aislado.estudio
    else:
        return
    try:
        assert_estudio_micro_operable(estudio)
    except MicrobiologiaAccionError as exc:
        raise ValidationError(str(exc)) from exc


class MedioCultivoViewSet(viewsets.ModelViewSet):
    """Catálogo de medios. Lectura amplia, escritura solo admin (patrón B0)."""

    queryset = MedioCultivo.objects.all().order_by("nombre")
    serializer_class = MedioCultivoSerializer
    permission_classes = [LimsMicrobiologiaCatalogPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["codigo", "nombre", "tipo"]
    ordering_fields = ["codigo", "nombre", "created_at"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def perform_create(self, serializer):
        instance = serializer.save()
        log_create(
            actor=getattr(self.request, "user", None),
            entity=instance,
            module="laboratorio",
            metadata={
                "accion": "crear_medio",
                "medio_id": instance.pk,
                "medio_codigo": instance.codigo,
                "view": "MedioCultivoViewSet.create",
            },
        )

    def perform_update(self, serializer):
        before = safe_model_snapshot(serializer.instance)
        instance = serializer.save()
        log_update(
            actor=getattr(self.request, "user", None),
            entity=instance,
            before=before,
            module="laboratorio",
            metadata={
                "accion": "actualizar_medio",
                "medio_id": instance.pk,
                "medio_codigo": instance.codigo,
                "activo_nuevo": instance.activo,
                "view": "MedioCultivoViewSet.partial_update",
            },
        )

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "No se permite eliminar medios; desactive con activo=false."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )


class EstudioMicrobiologiaViewSet(viewsets.ModelViewSet):
    """Estudios microbiológicos. El estado solo cambia por acciones explícitas."""

    queryset = EstudioMicrobiologia.objects.select_related(
        "solicitud",
        "solicitud__medico_interno",
        "muestra",
        "paciente",
        "responsable",
    ).prefetch_related("siembras", "lecturas")
    permission_classes = [LimsMicrobiologiaPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["numero", "solicitud__numero", "muestra__codigo_barra"]
    ordering_fields = ["created_at", "fecha_inicio", "estado"]
    ordering = ["-created_at"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_serializer_class(self):
        if self.action == "create":
            return EstudioMicrobiologiaCreateSerializer
        if self.action in ("partial_update", "update"):
            return EstudioMicrobiologiaPartialUpdateSerializer
        return EstudioMicrobiologiaSerializer

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
        try:
            estudio = crear_estudio(
                solicitud=vd["_solicitud"],
                muestra=vd["_muestra"],
                tipo_estudio=vd.get("tipo_estudio") or "CULTIVO_RUTINA",
                observaciones=vd.get("observaciones") or "",
                actor=request.user,
                view="EstudioMicrobiologiaViewSet.create",
            )
        except MicrobiologiaAccionError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        out = EstudioMicrobiologiaSerializer(estudio, context=self.get_serializer_context())
        return Response(out.data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        _guard_estudio_micro_operable_entity(serializer.instance)
        before = safe_model_snapshot(serializer.instance)
        instance = serializer.save()
        log_update(
            actor=getattr(self.request, "user", None),
            entity=instance,
            before=before,
            module="laboratorio",
            metadata={
                "accion": "actualizar_estudio",
                "estudio_id": instance.pk,
                "numero_estudio": instance.numero,
                "solicitud_id": instance.solicitud_id,
                "view": "EstudioMicrobiologiaViewSet.partial_update",
            },
        )

    @action(detail=True, methods=["post"], url_path="iniciar")
    def iniciar(self, request, pk=None):
        EstudioIniciarSerializer(data=request.data).is_valid(raise_exception=True)
        try:
            estudio = aplicar_iniciar_estudio(
                int(pk),
                actor=request.user,
                view="EstudioMicrobiologiaViewSet.iniciar",
            )
        except EstudioMicrobiologia.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except MicrobiologiaAccionError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            EstudioMicrobiologiaSerializer(estudio, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="cancelar")
    def cancelar(self, request, pk=None):
        ser = EstudioCancelarSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            estudio = aplicar_cancelar_estudio(
                int(pk),
                actor=request.user,
                view="EstudioMicrobiologiaViewSet.cancelar",
                motivo=ser.validated_data["motivo"],
            )
        except EstudioMicrobiologia.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except MicrobiologiaAccionError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            EstudioMicrobiologiaSerializer(estudio, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="marcar-informado")
    def marcar_informado(self, request, pk=None):
        EstudioMarcarInformadoSerializer(data=request.data).is_valid(raise_exception=True)
        try:
            estudio = aplicar_marcar_estudio_informado(
                int(pk),
                actor=request.user,
                view="EstudioMicrobiologiaViewSet.marcar_informado",
            )
        except EstudioMicrobiologia.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except MicrobiologiaAccionError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            EstudioMicrobiologiaSerializer(estudio, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )


class SiembraMicrobiologiaViewSet(viewsets.ModelViewSet):
    queryset = SiembraMicrobiologia.objects.select_related(
        "estudio",
        "estudio__solicitud",
        "estudio__muestra",
        "medio",
    )
    permission_classes = [LimsMicrobiologiaPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["estudio__numero", "medio__codigo"]
    ordering_fields = ["created_at", "fecha_siembra", "estado"]
    ordering = ["-created_at"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_serializer_class(self):
        if self.action == "create":
            return SiembraMicrobiologiaCreateSerializer
        if self.action in ("partial_update", "update"):
            return SiembraMicrobiologiaPartialUpdateSerializer
        return SiembraMicrobiologiaSerializer

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
            return qs.filter(estudio__solicitud__medico_interno__user=user)
        return qs.none()

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        vd = ser.validated_data
        try:
            siembra = crear_siembra(
                estudio_id=vd["estudio_id"],
                medio_id=vd["medio_id"],
                fecha_siembra=vd.get("fecha_siembra"),
                condicion_incubacion=vd.get("condicion_incubacion") or "",
                temperatura_c=vd.get("temperatura_c"),
                atmosfera=vd.get("atmosfera") or "",
                observaciones=vd.get("observaciones") or "",
                actor=request.user,
                view="SiembraMicrobiologiaViewSet.create",
            )
        except EstudioMicrobiologia.DoesNotExist:
            return Response({"error": "Estudio inexistente."}, status=status.HTTP_400_BAD_REQUEST)
        except MicrobiologiaAccionError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        out = SiembraMicrobiologiaSerializer(siembra, context=self.get_serializer_context())
        return Response(out.data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        _guard_estudio_micro_operable_entity(serializer.instance)
        before = safe_model_snapshot(serializer.instance)
        instance = serializer.save()
        log_update(
            actor=getattr(self.request, "user", None),
            entity=instance,
            before=before,
            module="laboratorio",
            metadata={
                "accion": "actualizar_siembra",
                "siembra_id": instance.pk,
                "estudio_id": instance.estudio_id,
                "view": "SiembraMicrobiologiaViewSet.partial_update",
            },
        )


class LecturaCultivoViewSet(viewsets.ModelViewSet):
    queryset = LecturaCultivo.objects.select_related(
        "siembra",
        "estudio",
        "estudio__solicitud",
        "estudio__muestra",
    )
    permission_classes = [LimsMicrobiologiaPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["estudio__numero", "siembra__medio__codigo"]
    ordering_fields = ["created_at", "fecha_lectura"]
    ordering = ["-fecha_lectura"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_serializer_class(self):
        if self.action == "create":
            return LecturaCultivoCreateSerializer
        if self.action in ("partial_update", "update"):
            return LecturaCultivoPartialUpdateSerializer
        return LecturaCultivoSerializer

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
            return qs.filter(estudio__solicitud__medico_interno__user=user)
        return qs.none()

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        vd = ser.validated_data
        try:
            lectura = crear_lectura(
                siembra_id=vd["siembra_id"],
                fecha_lectura=vd.get("fecha_lectura"),
                horas_incubacion=vd.get("horas_incubacion"),
                crecimiento=vd.get("crecimiento") or "PENDIENTE",
                descripcion_colonias=vd.get("descripcion_colonias") or "",
                tincion_gram=vd.get("tincion_gram") or "",
                observaciones=vd.get("observaciones") or "",
                es_preliminar=vd.get("es_preliminar") or False,
                actor=request.user,
                view="LecturaCultivoViewSet.create",
            )
        except SiembraMicrobiologia.DoesNotExist:
            return Response({"error": "Siembra inexistente."}, status=status.HTTP_400_BAD_REQUEST)
        except MicrobiologiaAccionError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        out = LecturaCultivoSerializer(lectura, context=self.get_serializer_context())
        return Response(out.data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        _guard_estudio_micro_operable_entity(serializer.instance)
        before = safe_model_snapshot(serializer.instance)
        instance = serializer.save()
        log_update(
            actor=getattr(self.request, "user", None),
            entity=instance,
            before=before,
            module="laboratorio",
            metadata={
                "accion": "actualizar_lectura",
                "lectura_id": instance.pk,
                "siembra_id": instance.siembra_id,
                "estudio_id": instance.estudio_id,
                "view": "LecturaCultivoViewSet.partial_update",
            },
        )


# ---------------------------------------------------------------------------
# B3.2 — Microorganismos, aislados, identificaciones
# ---------------------------------------------------------------------------


class MicroorganismoViewSet(viewsets.ModelViewSet):
    """Catálogo de microorganismos (B3.2). Lectura amplia, escritura solo admin."""

    queryset = Microorganismo.objects.all().order_by("nombre")
    serializer_class = MicroorganismoSerializer
    permission_classes = [LimsMicrobiologiaCatalogPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["codigo", "nombre", "genero", "especie", "grupo"]
    ordering_fields = ["codigo", "nombre", "created_at"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def perform_create(self, serializer):
        instance = serializer.save()
        log_create(
            actor=getattr(self.request, "user", None),
            entity=instance,
            module="laboratorio",
            metadata={
                "accion": "crear_microorganismo",
                "microorganismo_id": instance.pk,
                "microorganismo_codigo": instance.codigo,
                "view": "MicroorganismoViewSet.create",
            },
        )

    def perform_update(self, serializer):
        before = safe_model_snapshot(serializer.instance)
        instance = serializer.save()
        log_update(
            actor=getattr(self.request, "user", None),
            entity=instance,
            before=before,
            module="laboratorio",
            metadata={
                "accion": "actualizar_microorganismo",
                "microorganismo_id": instance.pk,
                "microorganismo_codigo": instance.codigo,
                "activo_nuevo": instance.activo,
                "view": "MicroorganismoViewSet.partial_update",
            },
        )

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "No se permite eliminar microorganismos; desactive con activo=false."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )


class AisladoMicrobiologicoViewSet(viewsets.ModelViewSet):
    """Aislados microbiológicos (B3.2). PATCH limitado; estado solo por servicio."""

    queryset = AisladoMicrobiologico.objects.select_related(
        "estudio",
        "estudio__solicitud",
        "estudio__muestra",
        "lectura_origen",
        "microorganismo",
    ).prefetch_related("identificaciones")
    permission_classes = [LimsMicrobiologiaPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["estudio__numero", "microorganismo__codigo"]
    ordering_fields = ["created_at", "estado"]
    ordering = ["-created_at"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_serializer_class(self):
        if self.action == "create":
            return AisladoMicrobiologicoCreateSerializer
        if self.action in ("partial_update", "update"):
            return AisladoMicrobiologicoPartialUpdateSerializer
        return AisladoMicrobiologicoSerializer

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
            return qs.filter(estudio__solicitud__medico_interno__user=user)
        return qs.none()

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        vd = ser.validated_data
        try:
            aislado = crear_aislado(
                estudio_id=vd["estudio_id"],
                lectura_id=vd["lectura_id"],
                microorganismo_id=vd.get("microorganismo_id"),
                descripcion=vd.get("descripcion") or "",
                cantidad=vd.get("cantidad") or "",
                significancia=vd.get("significancia") or "NO_DEFINIDA",
                requiere_antibiograma=vd.get("requiere_antibiograma") or False,
                observaciones=vd.get("observaciones") or "",
                actor=request.user,
                view="AisladoMicrobiologicoViewSet.create",
            )
        except EstudioMicrobiologia.DoesNotExist:
            return Response({"error": "Estudio inexistente."}, status=status.HTTP_400_BAD_REQUEST)
        except MicrobiologiaAccionError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        out = AisladoMicrobiologicoSerializer(aislado, context=self.get_serializer_context())
        return Response(out.data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        _guard_estudio_micro_operable_entity(serializer.instance)
        before = safe_model_snapshot(serializer.instance)
        instance = serializer.save()
        log_update(
            actor=getattr(self.request, "user", None),
            entity=instance,
            before=before,
            module="laboratorio",
            metadata={
                "accion": "actualizar_aislado",
                "aislado_id": instance.pk,
                "estudio_id": instance.estudio_id,
                "view": "AisladoMicrobiologicoViewSet.partial_update",
            },
        )

    @action(detail=True, methods=["post"], url_path="descartar")
    def descartar(self, request, pk=None):
        ser = AisladoDescartarSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            aislado = aplicar_descartar_aislado(
                int(pk),
                actor=request.user,
                view="AisladoMicrobiologicoViewSet.descartar",
                motivo=ser.validated_data["motivo"],
            )
        except AisladoMicrobiologico.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except MicrobiologiaAccionError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            AisladoMicrobiologicoSerializer(aislado, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )


class IdentificacionMicroorganismoViewSet(viewsets.ModelViewSet):
    """Identificaciones (B3.2). Append-only: sin PATCH/DELETE para preservar trazabilidad."""

    queryset = IdentificacionMicroorganismo.objects.select_related(
        "aislado",
        "aislado__estudio",
        "aislado__estudio__solicitud",
        "aislado__estudio__muestra",
        "microorganismo",
    )
    permission_classes = [LimsMicrobiologiaPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["aislado__estudio__numero", "microorganismo__codigo"]
    ordering_fields = ["fecha", "created_at"]
    ordering = ["-fecha"]
    http_method_names = ["get", "post", "head", "options"]

    def get_serializer_class(self):
        if self.action == "create":
            return IdentificacionMicroorganismoCreateSerializer
        return IdentificacionMicroorganismoSerializer

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
            return qs.filter(aislado__estudio__solicitud__medico_interno__user=user)
        return qs.none()

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        vd = ser.validated_data
        try:
            identificacion = crear_identificacion(
                aislado_id=vd["aislado_id"],
                microorganismo_id=vd["microorganismo_id"],
                metodo=vd.get("metodo") or "",
                resultado=vd.get("resultado") or "",
                confianza=vd.get("confianza"),
                fecha=vd.get("fecha"),
                observaciones=vd.get("observaciones") or "",
                actor=request.user,
                view="IdentificacionMicroorganismoViewSet.create",
            )
        except AisladoMicrobiologico.DoesNotExist:
            return Response({"error": "Aislado inexistente."}, status=status.HTTP_400_BAD_REQUEST)
        except MicrobiologiaAccionError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        out = IdentificacionMicroorganismoSerializer(identificacion, context=self.get_serializer_context())
        return Response(out.data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# B3.3 — Antibióticos / Antibiogramas / Resultados de antibiótico
# ---------------------------------------------------------------------------


class AntibioticoViewSet(viewsets.ModelViewSet):
    """Catálogo de antibióticos (B3.3). Lectura amplia, escritura solo admin."""

    queryset = Antibiotico.objects.all().order_by("nombre")
    serializer_class = AntibioticoSerializer
    permission_classes = [LimsMicrobiologiaCatalogPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["codigo", "nombre", "familia"]
    ordering_fields = ["codigo", "nombre", "created_at"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def perform_create(self, serializer):
        instance = serializer.save()
        log_create(
            actor=getattr(self.request, "user", None),
            entity=instance,
            module="laboratorio",
            metadata={
                "accion": "crear_antibiotico",
                "antibiotico_id": instance.pk,
                "antibiotico_codigo": instance.codigo,
                "view": "AntibioticoViewSet.create",
            },
        )

    def perform_update(self, serializer):
        before = safe_model_snapshot(serializer.instance)
        instance = serializer.save()
        log_update(
            actor=getattr(self.request, "user", None),
            entity=instance,
            before=before,
            module="laboratorio",
            metadata={
                "accion": "actualizar_antibiotico",
                "antibiotico_id": instance.pk,
                "antibiotico_codigo": instance.codigo,
                "activo_nuevo": instance.activo,
                "view": "AntibioticoViewSet.partial_update",
            },
        )

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "No se permite eliminar antibióticos; desactive con activo=false."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )


class AntibiogramaViewSet(viewsets.ModelViewSet):
    """Antibiogramas (B3.3). Estado solo cambia por servicios y acciones."""

    queryset = Antibiograma.objects.select_related(
        "aislado",
        "aislado__estudio",
        "aislado__estudio__solicitud",
        "aislado__estudio__muestra",
        "aislado__microorganismo",
    ).prefetch_related("resultados")
    permission_classes = [LimsMicrobiologiaPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["aislado__estudio__numero"]
    ordering_fields = ["created_at", "fecha_inicio", "estado"]
    ordering = ["-created_at"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_serializer_class(self):
        if self.action == "create":
            return AntibiogramaCreateSerializer
        if self.action in ("partial_update", "update"):
            return AntibiogramaPartialUpdateSerializer
        return AntibiogramaSerializer

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
            return qs.filter(aislado__estudio__solicitud__medico_interno__user=user)
        return qs.none()

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        vd = ser.validated_data
        try:
            antibiograma = crear_antibiograma(
                aislado_id=vd["aislado_id"],
                metodo=vd.get("metodo") or "",
                fecha_inicio=vd.get("fecha_inicio"),
                observaciones=vd.get("observaciones") or "",
                actor=request.user,
                view="AntibiogramaViewSet.create",
            )
        except MicrobiologiaAccionError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        out = AntibiogramaSerializer(antibiograma, context=self.get_serializer_context())
        return Response(out.data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        _guard_estudio_micro_operable_entity(serializer.instance)
        before = safe_model_snapshot(serializer.instance)
        instance = serializer.save()
        log_update(
            actor=getattr(self.request, "user", None),
            entity=instance,
            before=before,
            module="laboratorio",
            metadata={
                "accion": "actualizar_antibiograma",
                "antibiograma_id": instance.pk,
                "aislado_id": instance.aislado_id,
                "view": "AntibiogramaViewSet.partial_update",
            },
        )

    @action(detail=True, methods=["post"], url_path="completar")
    def completar(self, request, pk=None):
        AntibiogramaCompletarSerializer(data=request.data).is_valid(raise_exception=True)
        try:
            antibiograma = aplicar_completar_antibiograma(
                int(pk),
                actor=request.user,
                view="AntibiogramaViewSet.completar",
            )
        except Antibiograma.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except MicrobiologiaAccionError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            AntibiogramaSerializer(antibiograma, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="cancelar")
    def cancelar(self, request, pk=None):
        ser = AntibiogramaCancelarSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            antibiograma = aplicar_cancelar_antibiograma(
                int(pk),
                actor=request.user,
                view="AntibiogramaViewSet.cancelar",
                motivo=ser.validated_data["motivo"],
            )
        except Antibiograma.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except MicrobiologiaAccionError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            AntibiogramaSerializer(antibiograma, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )


class ResultadoAntibioticoViewSet(viewsets.ModelViewSet):
    """Resultados de antibiótico (B3.3). Carga/edición bloqueada si antibiograma COMPLETO/CANCELADO."""

    queryset = ResultadoAntibiotico.objects.select_related(
        "antibiograma",
        "antibiograma__aislado",
        "antibiograma__aislado__estudio",
        "antibiograma__aislado__estudio__solicitud",
        "antibiograma__aislado__estudio__muestra",
        "antibiotico",
    )
    permission_classes = [LimsMicrobiologiaPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["antibiograma__id", "antibiotico__codigo"]
    ordering_fields = ["created_at", "interpretacion"]
    ordering = ["-created_at"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_serializer_class(self):
        if self.action == "create":
            return ResultadoAntibioticoCreateSerializer
        if self.action in ("partial_update", "update"):
            return ResultadoAntibioticoPartialUpdateSerializer
        return ResultadoAntibioticoSerializer

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
            return qs.filter(
                antibiograma__aislado__estudio__solicitud__medico_interno__user=user
            )
        return qs.none()

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        vd = ser.validated_data
        try:
            resultado = crear_resultado_antibiotico(
                antibiograma_id=vd["antibiograma_id"],
                antibiotico_id=vd["antibiotico_id"],
                halo_mm=vd.get("halo_mm"),
                mic=vd.get("mic") or "",
                interpretacion=vd["interpretacion"],
                observaciones=vd.get("observaciones") or "",
                actor=request.user,
                view="ResultadoAntibioticoViewSet.create",
            )
        except MicrobiologiaAccionError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        out = ResultadoAntibioticoSerializer(resultado, context=self.get_serializer_context())
        return Response(out.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        ser = self.get_serializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        vd = ser.validated_data
        try:
            resultado = actualizar_resultado_antibiotico(
                instance.pk,
                actor=request.user,
                view="ResultadoAntibioticoViewSet.partial_update",
                halo_mm=vd.get("halo_mm") if "halo_mm" in vd else None,
                mic=vd.get("mic") if "mic" in vd else None,
                interpretacion=vd.get("interpretacion") if "interpretacion" in vd else None,
                observaciones=vd.get("observaciones") if "observaciones" in vd else None,
            )
        except MicrobiologiaAccionError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        out = ResultadoAntibioticoSerializer(resultado, context=self.get_serializer_context())
        return Response(out.data, status=status.HTTP_200_OK)


class InformeMicrobiologiaViewSet(viewsets.ModelViewSet):
    """Informes preliminares y finales (B3.4). Validación profesional solo admin."""

    queryset = InformeMicrobiologia.objects.select_related(
        "estudio",
        "estudio__solicitud",
        "estudio__solicitud__medico_interno",
        "estudio__muestra",
        "emitido_por",
        "validado_por",
        "anulado_por",
        "reemplaza_a",
    )
    permission_classes = [LimsMicrobiologiaInformePermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["estudio__numero", "texto"]
    ordering_fields = ["created_at", "tipo", "estado"]
    ordering = ["-created_at"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_serializer_class(self):
        if self.action == "create":
            return InformeMicrobiologiaCreateSerializer
        if self.action in ("partial_update", "update"):
            return InformeMicrobiologiaPartialUpdateSerializer
        return InformeMicrobiologiaSerializer

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
            return qs.filter(estudio__solicitud__medico_interno__user=user)
        return qs.none()

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        vd = ser.validated_data
        try:
            informe = crear_informe_borrador(
                estudio_id=vd["estudio_id"],
                tipo=vd["tipo"],
                texto=vd.get("texto") or "",
                observaciones=vd.get("observaciones") or "",
                reemplaza_a_id=vd.get("reemplaza_a_id"),
                actor=request.user,
                view="InformeMicrobiologiaViewSet.create",
            )
        except EstudioMicrobiologia.DoesNotExist:
            return Response({"error": "Estudio inexistente."}, status=status.HTTP_400_BAD_REQUEST)
        except MicrobiologiaAccionError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        out = InformeMicrobiologiaSerializer(informe, context=self.get_serializer_context())
        return Response(out.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        ser = self.get_serializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        vd = ser.validated_data
        try:
            informe = actualizar_informe_borrador(
                instance.pk,
                actor=request.user,
                view="InformeMicrobiologiaViewSet.partial_update",
                texto=vd.get("texto") if "texto" in vd else None,
                observaciones=vd.get("observaciones") if "observaciones" in vd else None,
                version=vd.get("version") if "version" in vd else None,
            )
        except MicrobiologiaAccionError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        out = InformeMicrobiologiaSerializer(informe, context=self.get_serializer_context())
        return Response(out.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "No se permite eliminar informes; use anular con motivo."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=True, methods=["post"], url_path="emitir")
    def emitir(self, request, pk=None):
        texto_kw = None
        if isinstance(request.data, dict) and "texto" in request.data:
            texto_kw = request.data.get("texto")
        try:
            informe = aplicar_emitir_informe(
                int(pk),
                actor=request.user,
                view="InformeMicrobiologiaViewSet.emitir",
                texto=texto_kw,
            )
        except InformeMicrobiologia.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except MicrobiologiaAccionError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            InformeMicrobiologiaSerializer(informe, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="validar")
    def validar(self, request, pk=None):
        InformeValidarSerializer(data=request.data).is_valid(raise_exception=True)
        try:
            informe = aplicar_validar_informe_final(
                int(pk),
                actor=request.user,
                view="InformeMicrobiologiaViewSet.validar",
            )
        except InformeMicrobiologia.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except MicrobiologiaAccionError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            InformeMicrobiologiaSerializer(informe, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="anular")
    def anular(self, request, pk=None):
        ser = InformeAnularSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            informe = aplicar_anular_informe(
                int(pk),
                actor=request.user,
                view="InformeMicrobiologiaViewSet.anular",
                motivo=ser.validated_data["motivo"],
            )
        except InformeMicrobiologia.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except MicrobiologiaAccionError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            InformeMicrobiologiaSerializer(informe, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )
