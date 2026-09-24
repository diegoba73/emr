"""
ViewSets para la app laboratorio (LIMS).
"""
import logging
from django.http import HttpResponse
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
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
from .muestra_estado import MuestraAccionError, tomar_muestras_en_solicitud
from .serializers import (
    TomarMuestraOrdenSerializer,
    EnviarInformeOrdenSerializer,
    TipoMuestraSerializer,
    TipoExamenSerializer,
    PanelExamenSerializer,
    SolicitudExamenSerializer,
    SolicitudExamenListSerializer,
    SolicitudExamenCreateSerializer,
    ResultadoExamenSerializer,
)
from auditoria.audit_service import log_create, log_event, log_update
from auditoria.snapshot import safe_model_snapshot
from api.permissions import (
    get_normalized_role,
    LimsCatalogReadPermission,
    LimsSolicitudExamenPermission,
    LimsTipoMuestraCatalogPermission,
    LimsTipoExamenCatalogPermission,
)
from .solicitud_estado import SolicitudEstadoTransitionError
from .analisis_longitudinal import (
    analizar_solicitud_optimizado,
    historial_analitos_solicitud,
)
from .orden_grupos_informe import claves_grupos_validas, validar_orden_grupos
from .solicitud_cierre import (
    SolicitudCierreError,
    finalizar_solicitud_manual,
    sincronizar_estado_tras_carga,
    solicitud_resultados_completos,
    solicitud_tiene_algun_resultado,
)
from .qc_service import QcGateError
from .resultado_carga import CargaResultadosError, cargar_resultados_solicitud, payload_item_tiene_valor
from .informe_entrega_token import InformeEntregaTokenError, verificar_token_entrega_informe
from .etiquetas_muestra import (
    generar_etiquetas_muestras_pdf_bytes,
    nombre_archivo_etiquetas_orden,
)
from .services_envio_informe import EnvioInformeError, enviar_informe_solicitud
from .services_informes_pdf import (
    auditar_descarga_informe_pdf,
    generar_informe_lims_pdf_bytes,
    nombre_archivo_pdf_seguro,
)
from .talon_pedido_pdf import (
    auditar_descarga_talon_solicitud,
    generar_talon_solicitud_pdf_bytes,
    nombre_archivo_talon_solicitud,
)

logger = logging.getLogger(__name__)


def _payload_item_tiene_valor(item: dict) -> bool:
    """True si el ítem trae un valor clínico para persistir (carga parcial)."""
    return payload_item_tiene_valor(item)


# ============================================================================
# VIEWSETS DE INFRAESTRUCTURA (READONLY)
# ============================================================================

class TipoMuestraViewSet(viewsets.ModelViewSet):
    """Catálogo de tipos de muestra (sangre, orina, etc.). Escritura: admin y laboratorio."""

    queryset = TipoMuestra.objects.all().order_by('nombre')
    serializer_class = TipoMuestraSerializer
    permission_classes = [LimsTipoMuestraCatalogPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['activo']
    search_fields = ['nombre', 'codigo']
    ordering_fields = ['nombre', 'codigo']
    ordering = ['nombre']
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def perform_create(self, serializer):
        instance = serializer.save()
        log_create(
            actor=getattr(self.request, 'user', None),
            entity=instance,
            module='laboratorio',
            metadata={
                'accion': 'crear_tipo_muestra',
                'tipo_muestra_id': instance.pk,
                'codigo': instance.codigo,
                'view': 'TipoMuestraViewSet.create',
            },
        )

    def perform_update(self, serializer):
        before = safe_model_snapshot(serializer.instance)
        instance = serializer.save()
        log_update(
            actor=getattr(self.request, 'user', None),
            entity=instance,
            before=before,
            module='laboratorio',
            metadata={
                'accion': 'actualizar_tipo_muestra',
                'tipo_muestra_id': instance.pk,
                'codigo': instance.codigo,
                'activo_nuevo': instance.activo,
                'view': 'TipoMuestraViewSet.partial_update',
            },
        )

    def destroy(self, request, *args, **kwargs):
        return Response(
            {'detail': 'No se permite eliminar tipos de muestra; desactive con activo=false.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )


class TipoExamenViewSet(viewsets.ModelViewSet):
    """Catálogo de tipos de examen. Escritura: admin y laboratorio."""

    queryset = TipoExamen.objects.all().select_related(
        'tipo_muestra_requerida', 'tipo_contenedor', 'seccion', 'laboratorio_derivacion'
    )
    serializer_class = TipoExamenSerializer
    permission_classes = [LimsTipoExamenCatalogPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['activo', 'tipo_muestra_requerida', 'modo_entrada']
    search_fields = ['nombre', 'codigo', 'codigo_nbu', 'abreviatura', 'metodo']
    ordering_fields = ['nombre', 'codigo', 'precio']
    ordering = ['nombre']
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def perform_create(self, serializer):
        instance = serializer.save()
        log_create(
            actor=getattr(self.request, 'user', None),
            entity=instance,
            module='laboratorio',
            metadata={
                'accion': 'crear_tipo_examen',
                'tipo_examen_id': instance.pk,
                'codigo': instance.codigo,
                'view': 'TipoExamenViewSet.create',
            },
        )

    def perform_update(self, serializer):
        before = safe_model_snapshot(serializer.instance)
        instance = serializer.save()
        log_update(
            actor=getattr(self.request, 'user', None),
            entity=instance,
            before=before,
            module='laboratorio',
            metadata={
                'accion': 'actualizar_tipo_examen',
                'tipo_examen_id': instance.pk,
                'codigo': instance.codigo,
                'activo_nuevo': instance.activo,
                'view': 'TipoExamenViewSet.partial_update',
            },
        )

    def destroy(self, request, *args, **kwargs):
        return Response(
            {'detail': 'No se permite eliminar tipos de examen; desactive con activo=false.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )


class PanelExamenViewSet(viewsets.ModelViewSet):
    """Catálogo de paneles LIMS. Escritura: admin y laboratorio."""

    queryset = PanelExamen.objects.all().prefetch_related('tipos_examen').order_by('nombre')
    serializer_class = PanelExamenSerializer
    permission_classes = [LimsTipoExamenCatalogPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['activo']
    search_fields = ['nombre', 'codigo', 'codigo_nbu']
    ordering_fields = ['nombre', 'codigo']
    ordering = ['nombre']
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def perform_create(self, serializer):
        instance = serializer.save()
        log_create(
            actor=getattr(self.request, 'user', None),
            entity=instance,
            module='laboratorio',
            metadata={
                'accion': 'crear_panel_examen',
                'panel_id': instance.pk,
                'codigo': instance.codigo,
                'view': 'PanelExamenViewSet.create',
            },
        )

    def perform_update(self, serializer):
        before = safe_model_snapshot(serializer.instance)
        instance = serializer.save()
        log_update(
            actor=getattr(self.request, 'user', None),
            entity=instance,
            before=before,
            module='laboratorio',
            metadata={
                'accion': 'actualizar_panel_examen',
                'panel_id': instance.pk,
                'codigo': instance.codigo,
                'activo_nuevo': instance.activo,
                'view': 'PanelExamenViewSet.partial_update',
            },
        )

    def destroy(self, request, *args, **kwargs):
        return Response(
            {'detail': 'No se permite eliminar paneles; desactive con activo=false.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )


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
        'medico_interno',
        'consulta_hc__turno__recurso',
    ).prefetch_related(
        'tipos_examen',
        'paneles',
        'resultados__tipo_examen',
        'resultados__muestra',
        'resultados__laboratorio_derivacion',
        'muestras__tipo_contenedor',
    ).all()
    permission_classes = [LimsSolicitudExamenPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['paciente', 'estado', 'origen_solicitud', 'consulta_hc']
    search_fields = [
        'numero',
        'paciente__nombre',
        'paciente__apellido',
        'paciente__dni',
        'medico_interno__nombre',
        'medico_interno__apellido',
    ]
    ordering_fields = ['fecha_solicitud', 'id', 'numero', 'estado']
    ordering = ['-fecha_solicitud', '-id']
    
    def get_serializer_class(self):
        """Create vs listado liviano vs detalle."""
        if self.action == 'create':
            return SolicitudExamenCreateSerializer
        if self.action == 'list':
            return SolicitudExamenListSerializer
        return SolicitudExamenSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        instance = serializer.instance
        merged = bool(getattr(instance, "_orden_merged", False))
        out = SolicitudExamenSerializer(instance, context=self.get_serializer_context()).data
        out["merged"] = merged
        headers = self.get_success_headers(out)
        return Response(
            out,
            status=status.HTTP_200_OK if merged else status.HTTP_201_CREATED,
            headers=headers,
        )

    def perform_create(self, serializer):
        instance = serializer.save()
        log_create(actor=getattr(self.request, "user", None), entity=instance, module="laboratorio", metadata={"view": "SolicitudExamenViewSet.perform_create", "merged": bool(getattr(instance, "_orden_merged", False))})

    @action(detail=True, methods=['post'], url_path='agregar-examenes')
    def agregar_examenes(self, request, pk=None):
        """Agrega exámenes/paneles a orden abierta, post-etiquetas o en curso si caben en tubos."""
        from laboratorio.solicitud_orden_abierta import (
            OrdenNoAbiertaError,
            TuboNuevoRequeridoError,
            agregar_examenes_a_solicitud,
        )

        solicitud = self.get_object()
        examenes_ids = request.data.get('examenes_ids') or []
        paneles_ids = request.data.get('paneles_ids') or []
        if not isinstance(examenes_ids, list) or not isinstance(paneles_ids, list):
            return Response(
                {'detail': 'examenes_ids y paneles_ids deben ser listas.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not examenes_ids and not paneles_ids:
            return Response(
                {'detail': 'Indique al menos un examen o panel.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            actualizada = agregar_examenes_a_solicitud(
                solicitud,
                examenes_ids=examenes_ids,
                paneles_ids=paneles_ids,
            )
        except (OrdenNoAbiertaError, TuboNuevoRequeridoError) as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        log_update(
            actor=getattr(request, "user", None),
            entity=actualizada,
            before=None,
            module="laboratorio",
            metadata={
                "view": "SolicitudExamenViewSet.agregar_examenes",
                "examenes_ids": examenes_ids,
                "paneles_ids": paneles_ids,
            },
        )
        data = SolicitudExamenSerializer(actualizada, context=self.get_serializer_context()).data
        data['merged'] = True
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='quitar-examenes')
    def quitar_examenes(self, request, pk=None):
        """Quita exámenes/paneles de orden PENDIENTE o en curso (sin resultado/validado)."""
        from laboratorio.solicitud_orden_abierta import (
            QuitarExamenError,
            quitar_examenes_de_solicitud,
        )

        solicitud = self.get_object()
        examenes_ids = request.data.get('examenes_ids') or []
        paneles_ids = request.data.get('paneles_ids') or []
        if not isinstance(examenes_ids, list) or not isinstance(paneles_ids, list):
            return Response(
                {'detail': 'examenes_ids y paneles_ids deben ser listas.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not examenes_ids and not paneles_ids:
            return Response(
                {'detail': 'Indique al menos un examen o panel.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            actualizada = quitar_examenes_de_solicitud(
                solicitud,
                examenes_ids=examenes_ids,
                paneles_ids=paneles_ids,
            )
        except QuitarExamenError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        log_update(
            actor=getattr(request, "user", None),
            entity=actualizada,
            before=None,
            module="laboratorio",
            metadata={
                "view": "SolicitudExamenViewSet.quitar_examenes",
                "examenes_ids": examenes_ids,
                "paneles_ids": paneles_ids,
            },
        )
        data = SolicitudExamenSerializer(actualizada, context=self.get_serializer_context()).data
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='orden-abierta')
    def orden_abierta(self, request):
        """Devuelve la orden abierta del paciente (si existe) para alerta de merge."""
        from laboratorio.solicitud_orden_abierta import buscar_orden_abierta

        raw = request.query_params.get('paciente_id')
        if not raw:
            return Response(
                {'detail': 'paciente_id es obligatorio.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            paciente_id = int(raw)
        except (TypeError, ValueError):
            return Response(
                {'detail': 'paciente_id inválido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        sol = buscar_orden_abierta(paciente_id)
        if not sol:
            return Response(None)
        return Response(
            {
                'id': sol.id,
                'numero': sol.numero,
                'fecha_solicitud': sol.fecha_solicitud,
                'estado': sol.estado,
            }
        )

    @action(detail=True, methods=['post'], url_path='marcar-derivacion')
    def marcar_derivacion(self, request, pk=None):
        """Marca envío / override de lab externo en un ResultadoExamen de la orden."""
        from laboratorio.models_derivacion import EstadoDerivacion, LaboratorioDerivacion

        solicitud = self.get_object()
        resultado_id = request.data.get('resultado_id')
        if not resultado_id:
            return Response(
                {'detail': 'resultado_id es obligatorio.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            resultado = solicitud.resultados.select_related(
                'laboratorio_derivacion', 'tipo_examen'
            ).get(pk=resultado_id)
        except ResultadoExamen.DoesNotExist:
            return Response(
                {'detail': 'Resultado no pertenece a esta orden.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        lab_id = request.data.get('laboratorio_derivacion_id', None)
        if lab_id is not None:
            if lab_id in ('', None):
                resultado.laboratorio_derivacion = None
                resultado.estado_derivacion = EstadoDerivacion.LOCAL
                resultado.fecha_envio_derivacion = None
            else:
                try:
                    lab = LaboratorioDerivacion.objects.get(pk=lab_id, activo=True)
                except LaboratorioDerivacion.DoesNotExist:
                    return Response(
                        {'detail': 'Laboratorio de derivación no encontrado.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                resultado.laboratorio_derivacion = lab
                if resultado.estado_derivacion == EstadoDerivacion.LOCAL:
                    resultado.estado_derivacion = EstadoDerivacion.PENDIENTE_ENVIO

        nuevo_estado = request.data.get('estado_derivacion')
        if nuevo_estado:
            validos = {c.value for c in EstadoDerivacion}
            if nuevo_estado not in validos:
                return Response(
                    {'detail': f'estado_derivacion inválido: {nuevo_estado}'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            resultado.estado_derivacion = nuevo_estado
            if nuevo_estado == EstadoDerivacion.ENVIADO and not resultado.fecha_envio_derivacion:
                resultado.fecha_envio_derivacion = timezone.now()
            if nuevo_estado == EstadoDerivacion.LOCAL:
                resultado.laboratorio_derivacion = None
                resultado.fecha_envio_derivacion = None

        obs = request.data.get('observaciones_derivacion')
        if obs is not None:
            resultado.observaciones_derivacion = str(obs)

        resultado.save()
        data = ResultadoExamenSerializer(resultado, context=self.get_serializer_context()).data
        return Response(data)

    def retrieve(self, request, *args, **kwargs):
        from laboratorio.hemograma_resultados import asegurar_resultados_paneles_derivados

        instance = self.get_object()
        if asegurar_resultados_paneles_derivados(instance):
            instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

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
        Lectura por rol.
        Admin / laboratorio / bioquímico / médico / secretaría / enfermería:
        todas las órdenes, todos los estados.
        Paciente: solo las propias.
        Filtros adicionales por query params:
        - numero: Búsqueda exacta para código de barras
        - fecha: Filtro por fecha de solicitud (creación)
        - fecha_muestra: Órdenes con muestra tomada ese día (excluye PENDIENTE)
        """
        listado = getattr(self, 'action', None) == 'list'
        if listado:
            # Sin prefetch de resultados: Todos / FINALIZADO cargan historial
            # con cientos de analitos y tumbaban el GET (timeout / 500).
            queryset = (
                SolicitudExamen.objects.select_related(
                    'paciente',
                    'medico_interno',
                    'consulta_hc__turno__recurso',
                )
                .prefetch_related('muestras__tipo_contenedor')
                .defer('orden_grupos_informe')
            )
        else:
            queryset = super().get_queryset()
        queryset = self._restringir_solicitudes_por_rol(queryset)
        return self._aplicar_filtros_listado(queryset)

    def _restringir_solicitudes_por_rol(self, queryset):
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()
        if user.is_superuser:
            return queryset
        role = get_normalized_role(user)
        if role in ('admin', 'laboratorio', 'bioquimico', 'secretaria', 'enfermeria', 'medico'):
            return queryset
        if role == 'paciente':
            try:
                return queryset.filter(paciente_id=user.paciente.id)
            except Exception:
                return queryset.none()
        return queryset.none()

    def _aplicar_filtros_listado(self, queryset):
        numero = self.request.query_params.get('numero')
        if numero:
            queryset = queryset.filter(numero=numero)

        fecha_muestra = self.request.query_params.get('fecha_muestra')
        if fecha_muestra:
            queryset = (
                queryset.exclude(estado='PENDIENTE')
                .filter(muestras__fecha_toma__date=fecha_muestra)
                .distinct()
            )
        else:
            fecha = self.request.query_params.get('fecha')
            if fecha:
                queryset = queryset.filter(fecha_solicitud__date=fecha)

        return queryset.order_by('-fecha_solicitud', '-id')

    def list(self, request, *args, **kwargs):
        """Todos / FINALIZADO no deben 500 si una fila o el SQL del listado fallan."""
        try:
            return super().list(request, *args, **kwargs)
        except Exception:
            logger.exception("SolicitudExamenViewSet.list falló; fallback sin joins de muestra")
            from laboratorio.display_names import format_apellido_nombre

            qs = (
                SolicitudExamen.objects.select_related('paciente', 'medico_interno')
                .defer('orden_grupos_informe')
            )
            qs = self.filter_queryset(self._restringir_solicitudes_por_rol(qs))
            qs = self._aplicar_filtros_listado(qs)
            try:
                page = self.paginate_queryset(qs)
            except Exception:
                logger.exception("SolicitudExamenViewSet.list fallback paginate falló")
                return Response({'count': 0, 'next': None, 'previous': None, 'results': []})
            instances = page if page is not None else qs
            rows = []
            for obj in instances:
                try:
                    pac = getattr(obj, 'paciente', None)
                    rows.append(
                        {
                            'id': obj.pk,
                            'numero': obj.numero,
                            'paciente': obj.paciente_id,
                            'paciente_nombre': format_apellido_nombre(pac) if pac else None,
                            'paciente_dni': getattr(pac, 'dni', None) if pac else None,
                            'medico_interno': obj.medico_interno_id,
                            'medico_display': obj.medico_display,
                            'origen_solicitud': obj.origen_solicitud,
                            'estado': obj.estado,
                            'estado_obra_social': obj.estado_obra_social,
                            'fecha_solicitud': obj.fecha_solicitud,
                            'fecha_toma_muestra': None,
                            'resultados': [],
                            'resultados_visibles': False,
                            'orden_abierta': obj.estado == 'PENDIENTE',
                            'esperando_recepcion': False,
                            'tubos_pendientes_extraccion': [],
                        }
                    )
                except Exception:
                    logger.exception("listado fallback fila id=%s", getattr(obj, 'pk', None))
            if page is not None:
                return self.get_paginated_response(rows)
            return Response(rows)
    
    @action(detail=True, methods=['post'], url_path='cargar-resultados')
    def cargar_resultados(self, request, pk=None):
        """
        Action para cargar resultados de exámenes.
        Recibe un JSON con lista de resultados: [{id: 1, valor: "100", es_patologico: false}, ...]
        Itera y actualiza atómicamente.
        Solo permitido en EN_PROCESO, INFORMADO_PARCIAL o LISTO_PARA_VALIDAR (no tras FINALIZADO).
        Completar todos los valores pasa a LISTO_PARA_VALIDAR (no finaliza).
        Con ``informar_parcial: true`` y resultados incompletos, pasa a INFORMADO_PARCIAL.
        """
        resultados_data = request.data.get('resultados', [])
        informar_parcial = bool(request.data.get('informar_parcial'))

        try:
            solicitud = cargar_resultados_solicitud(
                solicitud_id=pk,
                resultados_data=list(resultados_data or []),
                actor=request.user,
                informar_parcial=informar_parcial,
                observaciones=request.data.get('observaciones') or '',
                observaciones_en_payload='observaciones' in request.data,
                orden_grupos_informe=request.data.get('orden_grupos_informe'),
                orden_grupos_en_payload='orden_grupos_informe' in request.data,
                view='SolicitudExamenViewSet.cargar_resultados',
                fuente='MANUAL',
            )
        except SolicitudExamen.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except CargaResultadosError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except SolicitudEstadoTransitionError:
            return Response(
                {'error': 'Transición de estado no permitida al cargar resultados.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except SolicitudCierreError as exc:
            return Response(
                {'error': str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception:
            logger.error("Error cargando resultados", exc_info=True)
            return Response(
                {'error': 'Error al cargar resultados.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        serializer = self.get_serializer(solicitud)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'], url_path='orden-informe')
    def orden_informe(self, request, pk=None):
        """Persiste el orden de paneles/exámenes en el informe PDF."""
        solicitud = self.get_object()
        if solicitud.estado == 'PENDIENTE':
            return Response(
                {'error': 'La orden aún no tiene muestra tomada.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        claves = claves_grupos_validas(
            solicitud, solicitud.resultados.select_related('tipo_examen__tipo_muestra_requerida')
        )
        orden_validado = validar_orden_grupos(request.data.get('orden_grupos_informe'), claves)
        if orden_validado is None:
            return Response(
                {'error': 'orden_grupos_informe debe ser una lista de claves válidas.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        before = safe_model_snapshot(solicitud)
        solicitud.orden_grupos_informe = orden_validado
        solicitud.save(update_fields=['orden_grupos_informe'])
        log_update(
            actor=request.user,
            entity=solicitud,
            before=before,
            module='laboratorio',
            metadata={'action': 'orden_informe', 'view': 'SolicitudExamenViewSet.orden_informe'},
        )
        serializer = self.get_serializer(solicitud)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'], url_path='estado-obra-social')
    def estado_obra_social(self, request, pk=None):
        """Carga o actualiza la situación de obra social de la orden (pendiente o no)."""
        from laboratorio.obra_social import guardar_estado_obra_social

        solicitud = self.get_object()
        if 'estado_obra_social' not in request.data:
            return Response(
                {'detail': 'estado_obra_social es obligatorio.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        error = guardar_estado_obra_social(
            solicitud,
            request.data.get('estado_obra_social', ''),
            actor=request.user,
            view_name='SolicitudExamenViewSet.estado_obra_social',
        )
        if error is not None:
            return error
        serializer = self.get_serializer(solicitud)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='finalizar')
    def finalizar(self, request, pk=None):
        """Alias de validar: liberación clínica (bioquímico / admin)."""
        return self.validar(request, pk=pk)

    @action(detail=True, methods=['post'], url_path='enviar-informe')
    def enviar_informe(self, request, pk=None):
        """Envía el informe PDF al paciente y/o médico solicitante por email y/o WhatsApp."""
        ser = EnviarInformeOrdenSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                solicitud = (
                    SolicitudExamen.objects.select_for_update(of=('self',))
                    .select_related('paciente', 'medico_interno', 'medico_interno__user')
                    .get(pk=pk)
                )
                public_base = request.build_absolute_uri('/').rstrip('/')
                resultado = enviar_informe_solicitud(
                    solicitud,
                    enviar_email=ser.validated_data.get('email', False),
                    enviar_whatsapp=ser.validated_data.get('whatsapp', False),
                    enviar_email_medico=ser.validated_data.get('email_medico', False),
                    enviar_whatsapp_medico=ser.validated_data.get('whatsapp_medico', False),
                    actor=request.user,
                    view='SolicitudExamenViewSet.enviar_informe',
                    public_base_url=public_base,
                )
        except SolicitudExamen.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except EnvioInformeError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.error("Error enviando informe LIMS", exc_info=True)
            return Response(
                {'error': 'Error al enviar el informe.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        solicitud = self.get_object()
        data = self.get_serializer(solicitud).data
        data['envio'] = {
            'email_enviado': resultado.email_enviado,
            'email_destino': resultado.email_destino,
            'email_destinos': resultado.email_destinos,
            'email_adjunto_pdf': resultado.email_adjunto_pdf,
            'whatsapp_enviado': resultado.whatsapp_enviado,
            'whatsapp_telefono': resultado.whatsapp_telefono,
            'whatsapp_enlace': resultado.whatsapp_enlace,
            'whatsapp_enlaces': resultado.whatsapp_enlaces,
            'whatsapp_pdf_adjunto': resultado.whatsapp_pdf_adjunto,
            'informe_enlace_descarga': resultado.informe_enlace_descarga,
            'advertencias': resultado.advertencias or [],
        }
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='validar')
    def validar(self, request, pk=None):
        """
        Liberación clínica: marca la orden FINALIZADO y bloquea resultados.
        Solo bioquímico / admin. Si hay fuera de rango/críticos, exige confirmar_criticos.
        """
        raw_confirm = request.data.get('confirmar_criticos', False) if hasattr(request, 'data') else False
        if isinstance(raw_confirm, str):
            confirmar_criticos = raw_confirm.strip().lower() in ('1', 'true', 'yes', 'si', 'sí')
        else:
            confirmar_criticos = bool(raw_confirm)
        raw_qc_override = request.data.get('confirmar_qc_override', False) if hasattr(request, 'data') else False
        if isinstance(raw_qc_override, str):
            confirmar_qc_override = raw_qc_override.strip().lower() in ('1', 'true', 'yes', 'si', 'sí')
        else:
            confirmar_qc_override = bool(raw_qc_override)
        motivo_qc_override = str(request.data.get('motivo_qc_override', '') or '').strip()
        try:
            with transaction.atomic():
                solicitud = SolicitudExamen.objects.select_for_update().get(pk=pk)
                finalizar_solicitud_manual(
                    solicitud,
                    actor=request.user,
                    view='SolicitudExamenViewSet.validar',
                    confirmar_criticos=confirmar_criticos,
                    confirmar_qc_override=confirmar_qc_override,
                    motivo_qc_override=motivo_qc_override,
                )
                serializer = self.get_serializer(solicitud)
                return Response(serializer.data, status=status.HTTP_200_OK)
        except SolicitudEstadoTransitionError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except SolicitudCierreError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except QcGateError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except SolicitudExamen.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except Exception:
            logger.error("Error validando solicitud", exc_info=True)
            return Response(
                {'error': 'Error al validar la solicitud.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=['get'], url_path='analisis-longitudinal')
    def analisis_longitudinal(self, request, pk=None):
        """
        Análisis paramétrico: referencia + historial del paciente por resultado cargado.

        No usa IA; devuelve alertas estructuradas para revisión del laboratorio o médico.
        """
        solicitud = self.get_object()
        from api.permissions import usuario_puede_ver_resultados_lims

        if not usuario_puede_ver_resultados_lims(request.user, solicitud):
            return Response(
                {'detail': 'No tenés permiso para ver el análisis de esta orden.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if solicitud.estado == 'PENDIENTE':
            return Response(
                {'error': 'La orden aún no tiene muestra tomada.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = analizar_solicitud_optimizado(solicitud)
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='historial-analitos')
    def historial_analitos(self, request, pk=None):
        """
        Últimos N valores previos por analito de la orden (antes de guardar).

        Pensado para la grilla de carga: mismo paciente + mismo tipo_examen.
        Query param ``n`` (default 10, máx. 20).
        """
        solicitud = self.get_object()
        from api.permissions import usuario_puede_ver_resultados_lims

        if not usuario_puede_ver_resultados_lims(request.user, solicitud):
            return Response(
                {'detail': 'No tenés permiso para ver el historial de esta orden.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        raw_n = request.query_params.get('n', '10')
        try:
            n = int(raw_n)
        except (TypeError, ValueError):
            n = 10
        data = historial_analitos_solicitud(solicitud, limit=n)
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='sugerir-conclusion-hemograma')
    def sugerir_conclusion_hemograma(self, request, pk=None):
        """
        Borrador de conclusión de hemograma (reglas y/o MedGemma local).

        No persiste: el operador debe guardar en observaciones vía cargar-resultados.
        Acepta ``valores_borrador`` (dict codigo→valor) para sugerir con lo tipeado
        en pantalla aunque aún no se haya guardado.
        """
        from laboratorio.conclusion_hemograma import (
            parse_valores_borrador,
            solicitud_tiene_hemograma,
            sugerir_conclusion_hemograma as generar_sugerencia,
        )

        solicitud = self.get_object()
        if not solicitud_tiene_hemograma(solicitud):
            return Response(
                {'error': 'La orden no incluye hemograma (PAN_HEMO) ni analitos hematológicos.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        valores_borrador = parse_valores_borrador(request.data.get('valores_borrador'))
        if not solicitud_tiene_algun_resultado(solicitud) and not valores_borrador:
            return Response(
                {
                    'error': (
                        'No hay resultados cargados para sugerir una conclusión. '
                        'Ingresá valores en la grilla o guardá los resultados primero.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        prefer_ia = str(request.data.get('prefer_medgemma', 'true')).lower() in (
            '1', 'true', 'yes',
        )
        data = generar_sugerencia(
            solicitud,
            prefer_medgemma=prefer_ia,
            valores_borrador=valores_borrador or None,
        )
        log_event(
            action='IA_SUGGESTION_CREATED',
            actor=request.user,
            entity=solicitud,
            module='laboratorio',
            metadata={
                'view': 'SolicitudExamenViewSet.sugerir_conclusion_hemograma',
                'fuente': data.get('fuente'),
                'marcado_sugerencia': True,
                'modelo': data.get('modelo'),
                'texto_len': len(data.get('texto') or ''),
                'con_borrador': bool(valores_borrador),
            },
        )
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='tubos-preview')
    def tubos_preview(self, request, pk=None):
        """Lista de tubos físicos a generar según los exámenes de la orden."""
        from laboratorio.tubos_orden import TubosOrdenError, preview_tubos_solicitud

        solicitud = self.get_object()
        try:
            data = preview_tubos_solicitud(solicitud)
        except TubosOrdenError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'tubos': data}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='tomar-muestra')
    def tomar_muestra(self, request, pk=None):
        """
        Imprime / genera tubos de la orden (PENDIENTE): crea muestras en
        PENDIENTE_TOMA con código de barras. No marca RECIBIDA ni EN_PROCESO;
        eso ocurre al escanear en recepción (recibir-por-codigo).
        Sin ``muestras``: resuelve tubos según catálogo (tipo_contenedor + tope 10/tubo;
        hemograma y orina completa = 1 unidad c/u).
        Con ``muestras``: crea los ítems indicados (uno por tubo físico).
        """
        ser = TomarMuestraOrdenSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        items = ser.validated_data.get('muestras') or []
        try:
            tomar_muestras_en_solicitud(
                int(pk),
                items=items,
                actor=request.user,
                view='SolicitudExamenViewSet.tomar_muestra',
            )
        except SolicitudExamen.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except SolicitudEstadoTransitionError:
            return Response(
                {'error': 'Solo se pueden imprimir etiquetas cuando la solicitud está pendiente.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except MuestraAccionError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

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

    def _responder_informe_entrega(self, token: str):
        token = (token or '').strip()
        if not token:
            return Response(
                {'error': 'Token de entrega requerido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            solicitud_id = verificar_token_entrega_informe(token)
            solicitud = SolicitudExamen.objects.select_related('paciente').get(pk=solicitud_id)
        except InformeEntregaTokenError:
            return Response(
                {'error': 'Enlace de informe inválido o expirado.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        except SolicitudExamen.DoesNotExist:
            return Response(
                {'error': 'Orden no encontrada.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        if solicitud.estado != 'FINALIZADO':
            return Response(
                {'error': 'El informe no está disponible.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            pdf_bytes = generar_informe_lims_pdf_bytes(solicitud, role='admin')
        except Exception:
            logger.error("Error generando informe entrega pública")
            return Response(
                {'error': 'No se pudo generar el informe.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        nombre = nombre_archivo_pdf_seguro(solicitud.pk)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{nombre}"'
        return response

    @action(
        detail=False,
        methods=['get'],
        url_path='informe-entrega/(?P<token>[^/]+)',
        permission_classes=[AllowAny],
        authentication_classes=[],
    )
    def informe_entrega_por_token(self, request, token=None):
        """Descarga pública del PDF (path). WhatsApp autolinkea mejor sin `?t=`."""
        return self._responder_informe_entrega(token or '')

    @action(
        detail=False,
        methods=['get'],
        url_path='informe-entrega',
        permission_classes=[AllowAny],
        authentication_classes=[],
    )
    def informe_entrega(self, request):
        """Compat: descarga pública con `?t=` (enlaces viejos)."""
        return self._responder_informe_entrega((request.query_params.get('t') or '').strip())

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

    @action(detail=True, methods=['get'], url_path='etiquetas-muestras')
    def etiquetas_muestras(self, request, pk=None):
        """PDF con etiquetas Code128 de todas las muestras de la orden."""
        solicitud = self.get_object()
        muestras = list(
            Muestra.objects.filter(solicitud=solicitud)
            .select_related('solicitud', 'paciente', 'tipo_muestra', 'tipo_contenedor')
            .exclude(codigo_barra__isnull=True)
            .exclude(codigo_barra='')
            .order_by('id')
        )
        if not muestras:
            return Response(
                {'error': 'La orden no tiene muestras con código de barras para imprimir.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            pdf_bytes = generar_etiquetas_muestras_pdf_bytes(muestras)
        except Exception:
            logger.exception('generar etiquetas muestras orden pk=%s', pk)
            return Response(
                {'error': 'No se pudieron generar las etiquetas PDF.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        nombre = nombre_archivo_etiquetas_orden(solicitud.pk, solicitud.numero)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{nombre}"'
        return response

    @action(detail=True, methods=['get'], url_path='talon-pdf')
    def talon_pdf(self, request, pk=None):
        """
        Talón PDF A4 de respaldo (impresora común). No muta estado ni muestras.
        """
        solicitud = self.get_object()
        try:
            pdf_bytes = generar_talon_solicitud_pdf_bytes(solicitud)
        except Exception:
            logger.exception('generar talon PDF solicitud pk=%s', pk)
            return Response(
                {'error': 'No se pudo generar el talón PDF.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        auditar_descarga_talon_solicitud(
            actor=request.user,
            solicitud=solicitud,
            view='SolicitudExamenViewSet.talon_pdf',
        )
        nombre = nombre_archivo_talon_solicitud(solicitud)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{nombre}"'
        return response

