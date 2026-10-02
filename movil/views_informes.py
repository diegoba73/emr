"""Informes LIMS expuestos por la API móvil."""

from __future__ import annotations

import base64
import logging

from django.db import transaction
from django.http import HttpResponse
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from api.permissions import usuario_puede_descargar_informe_lims, usuario_puede_ver_solicitud_lims
from laboratorio.analisis_longitudinal import analizar_solicitud_optimizado, historial_analitos_solicitud
from laboratorio.models import SolicitudExamen
from laboratorio.qc_service import QcGateError
from laboratorio.serializers import SolicitudExamenSerializer
from laboratorio.services_informes_pdf import (
    auditar_descarga_informe_pdf,
    generar_informe_lims_pdf_bytes,
    nombre_archivo_pdf_seguro,
)
from laboratorio.solicitud_cierre import (
    SolicitudCierreError,
    desvalidar_solicitud_manual,
    finalizar_solicitud_manual,
    informar_parcial_si_corresponde,
)
from laboratorio.solicitud_estado import SolicitudEstadoTransitionError
from pacientes.services import ensure_paciente_linked_to_user
from usuarios.roles import normalize_rol

from .authentication import AutenticacionMovil, RolMovil
from .roles import (
    ESTADOS_BIOQUIMICO_TRABAJO,
    ESTADOS_INFORME_LISTADO,
    ROLES_MOVIL_INFORMES,
    ROLES_MOVIL_VALIDAR,
)

logger = logging.getLogger(__name__)


def _rol(user) -> str:
    return normalize_rol(user)


def _assert_rol_informes(user):
    if _rol(user) not in ROLES_MOVIL_INFORMES:
        raise PermissionDenied('Tu rol no puede consultar informes desde la app.')


def _queryset_informes(user):
    qs = SolicitudExamen.objects.select_related('paciente', 'medico_interno').prefetch_related(
        'resultados__tipo_examen',
        'tipos_examen',
        'paneles',
    )
    rol = _rol(user)
    if rol == 'paciente':
        paciente = ensure_paciente_linked_to_user(user)
        if not paciente:
            return qs.none()
        qs = qs.filter(paciente=paciente, estado__in=ESTADOS_INFORME_LISTADO)
    elif rol in ROLES_MOVIL_VALIDAR:
        qs = qs.filter(estado__in=ESTADOS_BIOQUIMICO_TRABAJO)
    else:
        qs = qs.filter(estado__in=ESTADOS_INFORME_LISTADO)
    return qs.order_by('-numero')


class InformeMovilSerializer(serializers.ModelSerializer):
    paciente_nombre = serializers.SerializerMethodField()
    es_parcial = serializers.SerializerMethodField()
    estado_display = serializers.SerializerMethodField()
    puede_descargar_pdf = serializers.SerializerMethodField()
    puede_validar = serializers.SerializerMethodField()
    puede_desvalidar = serializers.SerializerMethodField()
    puede_informar_parcial = serializers.SerializerMethodField()

    class Meta:
        model = SolicitudExamen
        fields = [
            'id',
            'numero',
            'paciente_nombre',
            'estado',
            'estado_display',
            'es_parcial',
            'fecha_solicitud',
            'puede_descargar_pdf',
            'puede_validar',
            'puede_desvalidar',
            'puede_informar_parcial',
        ]

    def get_paciente_nombre(self, obj):
        p = obj.paciente
        if not p:
            return ''
        return f'{p.apellido}, {p.nombre}'.strip(', ')

    def get_es_parcial(self, obj):
        return obj.estado == 'INFORMADO_PARCIAL'

    def get_estado_display(self, obj):
        if obj.estado == 'INFORMADO_PARCIAL':
            return 'Informe parcial'
        if obj.estado == 'FINALIZADO':
            return 'Validado'
        if obj.estado == 'LISTO_PARA_VALIDAR':
            return 'Listo para validar'
        if obj.estado == 'EN_PROCESO':
            return 'En proceso'
        return obj.estado

    def get_puede_descargar_pdf(self, obj):
        user = self.context['request'].user
        return usuario_puede_descargar_informe_lims(user, obj)

    def get_puede_validar(self, obj):
        user = self.context['request'].user
        return _rol(user) in ROLES_MOVIL_VALIDAR and obj.estado == 'LISTO_PARA_VALIDAR'

    def get_puede_desvalidar(self, obj):
        user = self.context['request'].user
        return _rol(user) in ROLES_MOVIL_VALIDAR and obj.estado == 'FINALIZADO'

    def get_puede_informar_parcial(self, obj):
        user = self.context['request'].user
        return _rol(user) in ROLES_MOVIL_VALIDAR and obj.estado in (
            'EN_PROCESO',
            'INFORMADO_PARCIAL',
            'LISTO_PARA_VALIDAR',
        )


class InformesMovil(APIView):
    authentication_classes = [AutenticacionMovil]
    permission_classes = [RolMovil]

    def get(self, request):
        _assert_rol_informes(request.user)
        qs = _queryset_informes(request.user)
        search = (request.query_params.get('q') or '').strip()
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(numero__icontains=search)
                | Q(paciente__apellido__icontains=search)
                | Q(paciente__nombre__icontains=search)
                | Q(paciente__dni__icontains=search)
            )
        page_size = min(int(request.query_params.get('page_size') or 50), 100)
        rows = list(qs[:page_size])
        data = InformeMovilSerializer(rows, many=True, context={'request': request}).data
        return Response({'results': data, 'next': None})


class InformeMovilDetalle(APIView):
    authentication_classes = [AutenticacionMovil]
    permission_classes = [RolMovil]

    def _get(self, request, pk):
        _assert_rol_informes(request.user)
        try:
            sol = _queryset_informes(request.user).get(pk=pk)
        except SolicitudExamen.DoesNotExist as exc:
            raise NotFound('Informe no encontrado.') from exc
        if not usuario_puede_ver_solicitud_lims(request.user, sol):
            raise NotFound('Informe no encontrado.')
        return sol

    def get(self, request, pk):
        sol = self._get(request, pk)
        resumen = InformeMovilSerializer(sol, context={'request': request}).data
        out = {'informe': resumen}
        rol = _rol(request.user)
        if rol in ROLES_MOVIL_VALIDAR or rol in ('laboratorio',):
            out['orden'] = SolicitudExamenSerializer(sol, context={'request': request}).data
            try:
                out['analisis'] = analizar_solicitud_optimizado(sol)
            except Exception:
                logger.exception('analisis longitudinal movil pk=%s', pk)
                out['analisis'] = None
            try:
                out['historial'] = historial_analitos_solicitud(sol, limit=10)
            except Exception:
                logger.exception('historial analitos movil pk=%s', pk)
                out['historial'] = None
        return Response(out)


class InformeMovilPdf(APIView):
    authentication_classes = [AutenticacionMovil]
    permission_classes = [RolMovil]

    def get(self, request, pk):
        _assert_rol_informes(request.user)
        # Paciente puede auto-vincularse en listado; hay que hacerlo también aquí
        # antes de evaluar user.paciente en la regla de descarga.
        if _rol(request.user) == 'paciente':
            ensure_paciente_linked_to_user(request.user)
        try:
            sol = SolicitudExamen.objects.select_related('paciente').get(pk=pk)
        except SolicitudExamen.DoesNotExist as exc:
            raise NotFound('Informe no encontrado.') from exc
        if not usuario_puede_descargar_informe_lims(request.user, sol):
            raise PermissionDenied('El informe no está disponible para descarga.')
        role = normalize_rol(request.user)
        if request.user.is_superuser:
            role = 'admin'
        try:
            pdf_bytes = generar_informe_lims_pdf_bytes(sol, role=role)
        except Exception:
            logger.exception('PDF movil pk=%s', pk)
            return Response(
                {'error': 'No se pudo generar el informe PDF.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        auditar_descarga_informe_pdf(actor=request.user, solicitud=sol)
        nombre = nombre_archivo_pdf_seguro(sol.pk)
        if (request.query_params.get('format') or '').lower() == 'base64':
            return Response({
                'filename': nombre,
                'content_type': 'application/pdf',
                'es_parcial': sol.estado == 'INFORMADO_PARCIAL',
                'base64': base64.b64encode(pdf_bytes).decode('ascii'),
            })
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{nombre}"'
        return response


class InformeMovilValidar(APIView):
    authentication_classes = [AutenticacionMovil]
    permission_classes = [RolMovil]

    def post(self, request, pk):
        if _rol(request.user) not in ROLES_MOVIL_VALIDAR:
            raise PermissionDenied('Solo el bioquímico puede validar informes.')
        raw_confirm = request.data.get('confirmar_criticos', False)
        if isinstance(raw_confirm, str):
            confirmar_criticos = raw_confirm.strip().lower() in ('1', 'true', 'yes', 'si', 'sí')
        else:
            confirmar_criticos = bool(raw_confirm)
        try:
            with transaction.atomic():
                sol = SolicitudExamen.objects.select_for_update().get(pk=pk)
                if not usuario_puede_ver_solicitud_lims(request.user, sol):
                    raise NotFound('Informe no encontrado.')
                finalizar_solicitud_manual(
                    sol,
                    actor=request.user,
                    view='InformeMovilValidar.post',
                    confirmar_criticos=confirmar_criticos,
                    confirmar_qc_override=False,
                    motivo_qc_override='',
                )
                return Response(
                    InformeMovilSerializer(sol, context={'request': request}).data,
                    status=status.HTTP_200_OK,
                )
        except SolicitudExamen.DoesNotExist as exc:
            raise NotFound('Informe no encontrado.') from exc
        except (SolicitudEstadoTransitionError, SolicitudCierreError, QcGateError) as exc:
            raise ValidationError(str(exc)) from exc


class InformeMovilDesvalidar(APIView):
    authentication_classes = [AutenticacionMovil]
    permission_classes = [RolMovil]

    def post(self, request, pk):
        if _rol(request.user) not in ROLES_MOVIL_VALIDAR:
            raise PermissionDenied('Solo el bioquímico puede reabrir informes validados.')
        motivo = str(request.data.get('motivo', '') or '')
        try:
            with transaction.atomic():
                sol = SolicitudExamen.objects.select_for_update().get(pk=pk)
                if not usuario_puede_ver_solicitud_lims(request.user, sol):
                    raise NotFound('Informe no encontrado.')
                desvalidar_solicitud_manual(
                    sol,
                    actor=request.user,
                    view='InformeMovilDesvalidar.post',
                    motivo=motivo,
                )
                return Response(
                    InformeMovilSerializer(sol, context={'request': request}).data,
                    status=status.HTTP_200_OK,
                )
        except SolicitudExamen.DoesNotExist as exc:
            raise NotFound('Informe no encontrado.') from exc
        except (SolicitudEstadoTransitionError, SolicitudCierreError) as exc:
            raise ValidationError(str(exc)) from exc


class InformeMovilInformarParcial(APIView):
    authentication_classes = [AutenticacionMovil]
    permission_classes = [RolMovil]

    def post(self, request, pk):
        if _rol(request.user) not in ROLES_MOVIL_VALIDAR:
            raise PermissionDenied('Solo el bioquímico puede informar parcialmente.')
        try:
            with transaction.atomic():
                sol = SolicitudExamen.objects.select_for_update().get(pk=pk)
                if not usuario_puede_ver_solicitud_lims(request.user, sol):
                    raise NotFound('Informe no encontrado.')
                if sol.estado == 'INFORMADO_PARCIAL':
                    return Response(
                        InformeMovilSerializer(sol, context={'request': request}).data,
                        status=status.HTTP_200_OK,
                    )
                ok = informar_parcial_si_corresponde(
                    sol,
                    actor=request.user,
                    view='InformeMovilInformarParcial.post',
                )
                if not ok:
                    raise ValidationError(
                        'No se puede informar parcialmente: hace falta al menos un '
                        'resultado cargado y que aún falten otros.'
                    )
                sol.refresh_from_db()
                return Response(
                    InformeMovilSerializer(sol, context={'request': request}).data,
                    status=status.HTTP_200_OK,
                )
        except SolicitudExamen.DoesNotExist as exc:
            raise NotFound('Informe no encontrado.') from exc
        except SolicitudEstadoTransitionError as exc:
            raise ValidationError(str(exc)) from exc
