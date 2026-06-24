"""
ViewSets para la app laboratorio (LIMS).
"""
import logging
from django.http import HttpResponse
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from .models import (
    TipoMuestra,
    TipoExamen,
    PanelExamen,
    SolicitudExamen,
    ResultadoExamen,
)
from .models_catalog import Muestra
from .resultado_muestra_validacion import (
    MUESTRA_ESTADOS_INVALIDOS_VALIDACION_ORDEN,
    assert_muestra_estado_carga_resultado,
    assert_tipo_examen_muestra_carga,
)
from .muestra_estado import MuestraAccionError, aplicar_iniciar_proceso
from .resultados_clinicos import aplicar_carga_estructurada
from .serializers import (
    TipoMuestraSerializer,
    TipoExamenSerializer,
    PanelExamenSerializer,
    SolicitudExamenSerializer,
    SolicitudExamenCreateSerializer,
    ResultadoExamenSerializer,
)
from auditoria.audit_service import log_create, log_event, log_update
from auditoria.snapshot import safe_model_snapshot
from api.permissions import get_normalized_role, LimsCatalogReadPermission, LimsSolicitudExamenPermission
from .solicitud_estado import SolicitudEstadoTransitionError, apply_solicitud_estado_transition
from .services_informes_pdf import (
    auditar_descarga_informe_pdf,
    generar_informe_lims_pdf_bytes,
    nombre_archivo_pdf_seguro,
)

logger = logging.getLogger(__name__)


# ============================================================================
# VIEWSETS DE INFRAESTRUCTURA (READONLY)
# ============================================================================

class TipoMuestraViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet de solo lectura para TipoMuestra."""
    queryset = TipoMuestra.objects.filter(activo=True)
    serializer_class = TipoMuestraSerializer
    permission_classes = [LimsCatalogReadPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['activo']
    search_fields = ['nombre', 'codigo']
    ordering_fields = ['nombre', 'codigo']
    ordering = ['nombre']


class TipoExamenViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet de solo lectura para TipoExamen."""
    queryset = TipoExamen.objects.filter(activo=True).select_related('tipo_muestra_requerida')
    serializer_class = TipoExamenSerializer
    permission_classes = [LimsCatalogReadPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['activo', 'tipo_muestra_requerida']
    search_fields = ['nombre', 'codigo', 'abreviatura']
    ordering_fields = ['nombre', 'codigo', 'precio']
    ordering = ['nombre']


class PanelExamenViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet de solo lectura para PanelExamen."""
    queryset = PanelExamen.objects.filter(activo=True).prefetch_related('tipos_examen')
    serializer_class = PanelExamenSerializer
    permission_classes = [LimsCatalogReadPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['activo']
    ordering = ['nombre']


# ============================================================================
# VIEWSET DE SOLICITUDES
# ============================================================================

class SolicitudExamenViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar Solicitudes de Examen.
    Permisos provisionales por rol (ver LimsSolicitudExamenPermission).
    """
    queryset = SolicitudExamen.objects.select_related(
        'paciente',
        'medico_interno'
    ).prefetch_related(
        'tipos_examen',
        'paneles',
        'resultados__tipo_examen',
        'resultados__muestra',
    ).all()
    permission_classes = [LimsSolicitudExamenPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['paciente', 'estado', 'origen_solicitud']
    ordering = ['-fecha_solicitud']
    
    def get_serializer_class(self):
        """Usa SolicitudExamenCreateSerializer para crear, SolicitudExamenSerializer para el resto."""
        if self.action == 'create':
            return SolicitudExamenCreateSerializer
        return SolicitudExamenSerializer

    def perform_create(self, serializer):
        instance = serializer.save()
        log_create(actor=getattr(self.request, "user", None), entity=instance, module="laboratorio", metadata={"view": "SolicitudExamenViewSet.perform_create"})

    def perform_update(self, serializer):
        before = safe_model_snapshot(self.get_object())
        instance = serializer.save()
        log_update(actor=getattr(self.request, "user", None), entity=instance, before=before, module="laboratorio", metadata={"view": "SolicitudExamenViewSet.perform_update"})

    def perform_destroy(self, instance):
        pk = instance.pk
        label = SolicitudExamen._meta.label
        repr_str = f"{label}:{pk}"[:255]
        before = safe_model_snapshot(instance)
        super().perform_destroy(instance)
        log_event(
            action="DELETE",
            actor=getattr(self.request, "user", None),
            entity=None,
            entity_type=label,
            entity_id=str(pk),
            entity_repr=repr_str,
            before=before,
            after=None,
            module="laboratorio",
            metadata={"view": "SolicitudExamenViewSet.perform_destroy"},
        )

    def get_queryset(self):
        """
        Restringe solicitudes por rol (médico: solo propias vía medico_interno).
        Filtros adicionales por query params:
        - numero: Búsqueda exacta para código de barras
        - fecha: Filtro por fecha de solicitud
        """
        queryset = super().get_queryset()
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()
        if user.is_superuser:
            pass
        else:
            role = get_normalized_role(user)
            if role in ('admin', 'laboratorio'):
                pass
            elif role == 'medico':
                queryset = queryset.filter(medico_interno__user=user)
            else:
                queryset = queryset.none()

        # Filtro por número (búsqueda exacta para código de barras)
        numero = self.request.query_params.get('numero')
        if numero:
            queryset = queryset.filter(numero=numero)
        
        # Filtro por fecha
        fecha = self.request.query_params.get('fecha')
        if fecha:
            queryset = queryset.filter(fecha_solicitud__date=fecha)
        
        return queryset
    
    @action(detail=True, methods=['post'], url_path='cargar-resultados')
    def cargar_resultados(self, request, pk=None):
        """
        Action para cargar resultados de exámenes.
        Recibe un JSON con lista de resultados: [{id: 1, valor: "100", es_patologico: false}, ...]
        Itera y actualiza atómicamente.
        PENDIENTE o TOMA_MUESTRA pasan a EN_PROCESO; EN_PROCESO solo actualiza resultados.
        """
        resultados_data = request.data.get('resultados', [])

        if not resultados_data:
            return Response(
                {'error': 'Se requiere una lista de resultados.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                solicitud = SolicitudExamen.objects.select_for_update().get(pk=pk)

                if solicitud.estado == 'CANCELADO':
                    return Response(
                        {'error': 'No se pueden cargar resultados en una solicitud cancelada.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                if solicitud.estado == 'VALIDADO':
                    return Response(
                        {'error': 'No se pueden modificar resultados de una solicitud ya validada.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                if solicitud.estado == 'ENTREGADO':
                    return Response(
                        {'error': 'No se pueden modificar resultados de una solicitud ya entregada.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                before_solicitud = safe_model_snapshot(solicitud)

                for resultado_item in resultados_data:
                    resultado_id = resultado_item.get('id')

                    if not resultado_id:
                        continue

                    try:
                        resultado = ResultadoExamen.objects.select_for_update(of=("self",)).get(
                            id=resultado_id,
                            solicitud=solicitud
                        )
                        before_res = safe_model_snapshot(resultado)
                        prev_muestra_id = resultado.muestra_id
                        muestra_meta_aplica = False
                        muestra_iniciar_proceso_id: int | None = None

                        if "muestra_id" in resultado_item:
                            if resultado.validado_por_id or resultado.fecha_validacion:
                                return Response(
                                    {
                                        "error": (
                                            "No se puede cambiar la muestra de un resultado validado."
                                        )
                                    },
                                    status=status.HTTP_400_BAD_REQUEST,
                                )
                            muestra_meta_aplica = True
                            raw_muestra_id = resultado_item.get("muestra_id")
                            if raw_muestra_id is None:
                                resultado.muestra = None
                            else:
                                try:
                                    muestra = Muestra.objects.select_for_update().get(
                                        pk=raw_muestra_id,
                                        solicitud_id=solicitud.pk,
                                    )
                                except Muestra.DoesNotExist:
                                    return Response(
                                        {
                                            "error": (
                                                "La muestra no existe o no pertenece a esta solicitud."
                                            )
                                        },
                                        status=status.HTTP_400_BAD_REQUEST,
                                    )
                                if muestra.paciente_id != solicitud.paciente_id:
                                    return Response(
                                        {
                                            "error": (
                                                "La muestra no corresponde al paciente de la solicitud."
                                            )
                                        },
                                        status=status.HTTP_400_BAD_REQUEST,
                                    )
                                try:
                                    assert_muestra_estado_carga_resultado(muestra)
                                except ValueError as exc:
                                    return Response(
                                        {"error": str(exc)},
                                        status=status.HTTP_400_BAD_REQUEST,
                                    )
                                resultado.muestra = muestra
                                if muestra.estado in ("RECIBIDA", "CONSERVADA"):
                                    muestra_iniciar_proceso_id = muestra.pk

                        try:
                            assert_tipo_examen_muestra_carga(
                                tipo_examen=resultado.tipo_examen,
                                resultado_muestra=resultado.muestra,
                                muestra_id_en_payload="muestra_id" in resultado_item,
                                raw_muestra_id=resultado_item.get("muestra_id"),
                            )
                        except ValueError as exc:
                            return Response(
                                {"error": str(exc)},
                                status=status.HTTP_400_BAD_REQUEST,
                            )

                        try:
                            audit_estructurado = aplicar_carga_estructurada(
                                resultado,
                                resultado.tipo_examen,
                                resultado_item,
                            )
                            audit_estructurado["valor_presente"] = bool(
                                (resultado.valor_obtenido or "").strip()
                            )
                        except ValidationError as exc:
                            msg = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
                            return Response({"error": msg}, status=status.HTTP_400_BAD_REQUEST)
                        resultado.save()
                        muestra_transitioned_en_proceso = False
                        muestra_estado_antes_proceso: str | None = None
                        if muestra_iniciar_proceso_id is not None:
                            muestra_estado_antes_proceso = (
                                Muestra.objects.filter(pk=muestra_iniciar_proceso_id)
                                .values_list("estado", flat=True)
                                .first()
                            )
                            try:
                                aplicar_iniciar_proceso(
                                    muestra_iniciar_proceso_id,
                                    actor=request.user,
                                    view="SolicitudExamenViewSet.cargar_resultados",
                                    resultado_id=resultado.pk,
                                )
                                muestra_transitioned_en_proceso = True
                            except MuestraAccionError:
                                pass
                        meta_carga = {
                            "action": "cargar_resultados",
                            "accion": "cargar_resultados",
                            "view": "SolicitudExamenViewSet.cargar_resultados",
                            "resultado_id": resultado.pk,
                            "solicitud_id": solicitud.pk,
                            "numero_solicitud": solicitud.numero,
                            "actor_id": getattr(request.user, "pk", None),
                            **audit_estructurado,
                        }
                        if muestra_transitioned_en_proceso and muestra_estado_antes_proceso:
                            meta_carga["muestra_estado_anterior"] = muestra_estado_antes_proceso
                            meta_carga["muestra_estado_nuevo"] = "EN_PROCESO"
                        if muestra_meta_aplica:
                            meta_carga["muestra_id"] = resultado.muestra_id
                        if prev_muestra_id != resultado.muestra_id and muestra_meta_aplica:
                            meta_carga["accion"] = "resultado_muestra_asociar"
                            meta_carga["muestra_anterior_id"] = prev_muestra_id
                            meta_carga["muestra_nueva_id"] = resultado.muestra_id
                        log_update(
                            actor=request.user,
                            entity=resultado,
                            before=before_res,
                            module="laboratorio",
                            metadata=meta_carga,
                        )
                    except ResultadoExamen.DoesNotExist:
                        logger.warning("ResultadoExamen inexistente para carga de resultados")

                estado_antes_carga = before_solicitud.get("estado")
                estado_transitioned = False
                if solicitud.estado in ('PENDIENTE', 'TOMA_MUESTRA'):
                    apply_solicitud_estado_transition(
                        solicitud,
                        'EN_PROCESO',
                        actor=request.user,
                        accion='cargar_resultados',
                        view='SolicitudExamenViewSet.cargar_resultados',
                    )
                    estado_transitioned = True
                elif solicitud.estado == 'EN_PROCESO':
                    log_update(
                        actor=request.user,
                        entity=solicitud,
                        before=before_solicitud,
                        module="laboratorio",
                        metadata={
                            "action": "cargar_resultados",
                            "accion": "cargar_resultados",
                            "view": "SolicitudExamenViewSet.cargar_resultados",
                            "estado_anterior": estado_antes_carga,
                            "estado_nuevo": solicitud.estado,
                            "solicitud_id": solicitud.pk,
                            "numero_solicitud": solicitud.numero,
                        },
                    )

                logger.debug(
                    "cargar_resultados completado solicitud_id=%s estado_transitioned=%s",
                    solicitud.pk,
                    estado_transitioned,
                )

                serializer = self.get_serializer(solicitud)
                return Response(serializer.data, status=status.HTTP_200_OK)

        except SolicitudEstadoTransitionError:
            return Response(
                {'error': 'Transición de estado no permitida al cargar resultados.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception:
            logger.error("Error cargando resultados", exc_info=True)
            return Response(
                {'error': 'Error al cargar resultados.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='validar')
    def validar(self, request, pk=None):
        """
        Action para validar una solicitud.
        Cambia estado a VALIDADO.
        Asigna validado_por = request.user.
        Bloquea cambios futuros (lanza error si ya estaba validado).
        """
        try:
            with transaction.atomic():
                solicitud = SolicitudExamen.objects.select_for_update().get(pk=pk)

                if solicitud.estado == 'VALIDADO':
                    return Response(
                        {'error': 'La solicitud ya está validada y no puede modificarse.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                if solicitud.estado == 'CANCELADO':
                    return Response(
                        {'error': 'No se puede validar una solicitud cancelada.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                if solicitud.estado == 'ENTREGADO':
                    return Response(
                        {'error': 'No se puede validar una solicitud ya entregada.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                if solicitud.estado != 'EN_PROCESO':
                    return Response(
                        {'error': 'Solo se pueden validar solicitudes en proceso.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                resultados_vacios = solicitud.resultados.filter(valor_obtenido='')
                if resultados_vacios.exists():
                    return Response(
                        {'error': 'No se puede validar una solicitud con resultados vacíos.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # B2.1: mitigar TOCTOU bloqueando las muestras referenciadas dentro de la
                # transacción ANTES de leer su estado. select_for_update sobre Muestra impide
                # que otro proceso cambie el estado entre lectura y commit de la validación.
                muestra_ids = list(
                    solicitud.resultados.filter(muestra_id__isnull=False)
                    .values_list("muestra_id", flat=True)
                    .distinct()
                )
                if muestra_ids:
                    muestras_bloqueadas = list(
                        Muestra.objects.select_for_update().filter(pk__in=muestra_ids)
                    )
                    for m in muestras_bloqueadas:
                        if m.estado in MUESTRA_ESTADOS_INVALIDOS_VALIDACION_ORDEN:
                            return Response(
                                {
                                    "error": (
                                        "No se puede validar: hay un resultado vinculado a una muestra "
                                        "en estado incompatible con la validación."
                                    )
                                },
                                status=status.HTTP_400_BAD_REQUEST,
                            )

                before_resultados = {
                    r.id: safe_model_snapshot(r)
                    for r in solicitud.resultados.all()
                }

                apply_solicitud_estado_transition(
                    solicitud,
                    'VALIDADO',
                    actor=request.user,
                    accion='validar',
                    view='SolicitudExamenViewSet.validar',
                )

                solicitud.resultados.update(
                    validado_por=request.user,
                    fecha_validacion=timezone.now()
                )
                solicitud.refresh_from_db()

                for res in ResultadoExamen.objects.filter(solicitud_id=solicitud.pk):
                    log_update(
                        actor=request.user,
                        entity=res,
                        before=before_resultados[res.id],
                        module="laboratorio",
                        metadata={
                            "action": "validar",
                            "accion": "validar",
                            "view": "SolicitudExamenViewSet.validar",
                        },
                    )

                logger.debug("validar completado solicitud_id=%s", solicitud.pk)

                serializer = self.get_serializer(solicitud)
                return Response(serializer.data, status=status.HTTP_200_OK)

        except SolicitudEstadoTransitionError:
            return Response(
                {'error': 'Transición de estado no permitida para validar.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception:
            logger.error("Error validando solicitud", exc_info=True)
            return Response(
                {'error': 'Error al validar solicitud.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='tomar-muestra')
    def tomar_muestra(self, request, pk=None):
        """Marca la solicitud en etapa de toma de muestra (PENDIENTE → TOMA_MUESTRA)."""
        try:
            with transaction.atomic():
                solicitud = SolicitudExamen.objects.select_for_update().get(pk=pk)
                apply_solicitud_estado_transition(
                    solicitud,
                    'TOMA_MUESTRA',
                    actor=request.user,
                    accion='tomar_muestra',
                    view='SolicitudExamenViewSet.tomar_muestra',
                )
        except SolicitudEstadoTransitionError:
            return Response(
                {'error': 'Solo se puede tomar muestra cuando la solicitud está pendiente.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except SolicitudExamen.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        solicitud = self.get_object()
        return Response(self.get_serializer(solicitud).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='cancelar')
    def cancelar(self, request, pk=None):
        """Cancela una solicitud no final (PENDIENTE, TOMA_MUESTRA o EN_PROCESO → CANCELADO)."""
        try:
            with transaction.atomic():
                solicitud = SolicitudExamen.objects.select_for_update().get(pk=pk)
                apply_solicitud_estado_transition(
                    solicitud,
                    'CANCELADO',
                    actor=request.user,
                    accion='cancelar',
                    view='SolicitudExamenViewSet.cancelar',
                )
        except SolicitudEstadoTransitionError:
            return Response(
                {'error': 'No se puede cancelar la solicitud en su estado actual.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except SolicitudExamen.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        solicitud = self.get_object()
        return Response(self.get_serializer(solicitud).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='marcar-entregado')
    def marcar_entregado(self, request, pk=None):
        """Marca la solicitud como entregada (VALIDADO → ENTREGADO)."""
        try:
            with transaction.atomic():
                solicitud = SolicitudExamen.objects.select_for_update().get(pk=pk)
                apply_solicitud_estado_transition(
                    solicitud,
                    'ENTREGADO',
                    actor=request.user,
                    accion='marcar_entregado',
                    view='SolicitudExamenViewSet.marcar_entregado',
                )
        except SolicitudEstadoTransitionError:
            return Response(
                {'error': 'Solo se puede marcar como entregada una solicitud validada.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except SolicitudExamen.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        solicitud = self.get_object()
        return Response(self.get_serializer(solicitud).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='informe-pdf')
    def informe_pdf(self, request, pk=None):
        """
        Descarga informe LIMS básico en PDF (generado en memoria).
        No modifica estado ni persiste archivos.
        """
        solicitud = self.get_object()
        role = get_normalized_role(request.user)
        if request.user.is_superuser:
            role = 'admin'
        try:
            pdf_bytes = generar_informe_lims_pdf_bytes(solicitud, role=role)
        except Exception:
            logger.error("Error generando informe PDF LIMS")
            return Response(
                {'error': 'No se pudo generar el informe PDF.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        auditar_descarga_informe_pdf(actor=request.user, solicitud=solicitud)
        nombre = nombre_archivo_pdf_seguro(solicitud.pk)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{nombre}"'
        return response

    @action(detail=True, methods=['get'], url_path='etiqueta')
    def etiqueta(self, request, pk=None):
        """
        Action para generar etiqueta ZPL para imprimir etiquetas de tubos.
        Retorna un JSON simulado con datos ZPL.
        """
        solicitud = self.get_object()
        
        # Generar datos ZPL simulados
        zpl_data = {
            'protocolo': solicitud.numero,
            'paciente': solicitud.paciente.nombre_completo,
            'dni': solicitud.paciente.dni,
            'fecha': solicitud.fecha_solicitud.strftime('%d/%m/%Y'),
            'zpl': f"""
^XA
^FO50,50^A0N,30,30^FD{solicitud.numero}^FS
^FO50,100^A0N,25,25^FD{solicitud.paciente.nombre_completo}^FS
^FO50,130^A0N,20,20^FD{solicitud.paciente.dni}^FS
^FO50,160^A0N,20,20^FD{solicitud.fecha_solicitud.strftime('%d/%m/%Y')}^FS
^XZ
            """.strip()
        }
        
        return Response(zpl_data, status=status.HTTP_200_OK)

