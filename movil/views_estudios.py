"""Estudios complementarios (imagen/informes) en la API móvil."""

from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.renderers import BaseRenderer, JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from estudios import services as estudios_services
from estudios.access import (
    usuario_puede_descargar_pdf_informe,
    usuario_puede_ver_estudio_clinico,
)
from estudios.models import EstudioComplementario, InformeEstudioComplementario
from pacientes.services import ensure_paciente_linked_to_user
from usuarios.roles import normalize_rol

from .authentication import AutenticacionMovil, RolMovil


class _PdfBinaryRenderer(BaseRenderer):
    media_type = 'application/pdf'
    format = 'pdf'
    charset = None
    render_style = 'binary'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if isinstance(data, (bytes, bytearray, memoryview)):
            return bytes(data)
        return b''


def _rol(user) -> str:
    return normalize_rol(user)


def _assert_rol_estudios(user):
    if _rol(user) not in ('paciente', 'medico'):
        raise PermissionDenied('Tu rol no consulta estudios desde la app.')


def _queryset_estudios(user):
    qs = EstudioComplementario.objects.select_related(
        'paciente', 'tipo_estudio', 'medico_solicitante'
    ).prefetch_related('informes')
    rol = _rol(user)
    if rol == 'paciente':
        paciente = ensure_paciente_linked_to_user(user)
        if not paciente:
            return qs.none()
        return qs.filter(
            paciente=paciente,
            estado=EstudioComplementario.Estado.ENTREGADO,
        ).order_by('-fecha_solicitud', '-id')
    if rol == 'medico':
        return qs.filter(
            estado__in=[
                EstudioComplementario.Estado.VALIDADO,
                EstudioComplementario.Estado.ENTREGADO,
            ]
        ).order_by('-fecha_solicitud', '-id')
    return qs.none()


def _titulo_informe(informe: InformeEstudioComplementario) -> str:
    tipo = informe.get_tipo_display() if hasattr(informe, 'get_tipo_display') else 'Informe'
    return f'{tipo} v{informe.version}'


def _serialize_estudio(estudio, user) -> dict:
    tipo_nombre = ''
    if estudio.tipo_estudio_id:
        tipo_nombre = estudio.tipo_estudio.nombre
    elif estudio.practica:
        tipo_nombre = estudio.get_practica_display() if hasattr(estudio, 'get_practica_display') else estudio.practica
    informes = []
    for inf in estudio.informes.all():
        informes.append(
            {
                'id': inf.pk,
                'titulo': _titulo_informe(inf),
                'estado': inf.estado,
                'estado_display': inf.get_estado_display(),
                'version': inf.version,
                'es_vigente': inf.es_vigente,
                'puede_descargar_pdf': usuario_puede_descargar_pdf_informe(user, estudio, inf),
            }
        )
    pac = estudio.paciente
    return {
        'id': estudio.pk,
        'paciente_nombre': getattr(pac, 'nombre_completo', '') if pac else '',
        'paciente_dni': getattr(pac, 'dni', '') or '',
        'tipo_nombre': tipo_nombre or 'Estudio',
        'tipo_actividad': estudio.tipo_actividad,
        'estado': estudio.estado,
        'estado_display': estudio.get_estado_display(),
        'fecha_solicitud': estudio.fecha_solicitud.isoformat()
        if getattr(estudio, 'fecha_solicitud', None)
        else None,
        'informes': informes,
    }


def _get_estudio_visible(user, pk: int) -> EstudioComplementario:
    estudio = (
        EstudioComplementario.objects.select_related('paciente', 'tipo_estudio')
        .prefetch_related('informes')
        .filter(pk=pk)
        .first()
    )
    if not estudio:
        raise NotFound('No se encontró el estudio.')
    rol = _rol(user)
    if rol == 'paciente':
        paciente = ensure_paciente_linked_to_user(user)
        if (
            not paciente
            or estudio.paciente_id != paciente.pk
            or estudio.estado != EstudioComplementario.Estado.ENTREGADO
        ):
            raise NotFound('No se encontró el estudio.')
        return estudio
    if rol == 'medico':
        if estudio.estado not in (
            EstudioComplementario.Estado.VALIDADO,
            EstudioComplementario.Estado.ENTREGADO,
        ):
            raise NotFound('No se encontró el estudio.')
        if not usuario_puede_ver_estudio_clinico(user, estudio):
            raise NotFound('No se encontró el estudio.')
        return estudio
    raise PermissionDenied('Tu rol no consulta estudios desde la app.')


class EstudiosMovil(APIView):
    authentication_classes = [AutenticacionMovil]
    permission_classes = [RolMovil]

    def get(self, request):
        _assert_rol_estudios(request.user)
        qs = _queryset_estudios(request.user)
        q = (request.query_params.get('q') or '').strip()
        if q and _rol(request.user) == 'medico':
            qs = qs.filter(
                Q(paciente__nombre__icontains=q)
                | Q(paciente__apellido__icontains=q)
                | Q(paciente__dni__icontains=q)
                | Q(tipo_estudio__nombre__icontains=q)
                | Q(practica__icontains=q)
            )
        results = [_serialize_estudio(e, request.user) for e in qs[:100]]
        return Response({'results': results})


class EstudioMovilDetalle(APIView):
    authentication_classes = [AutenticacionMovil]
    permission_classes = [RolMovil]

    def get(self, request, pk: int):
        _assert_rol_estudios(request.user)
        estudio = _get_estudio_visible(request.user, pk)
        return Response(_serialize_estudio(estudio, request.user))


class EstudioInformePdfMovil(APIView):
    authentication_classes = [AutenticacionMovil]
    permission_classes = [RolMovil]
    renderer_classes = [JSONRenderer, _PdfBinaryRenderer]

    def get(self, request, pk: int, informe_id: int):
        _assert_rol_estudios(request.user)
        estudio = _get_estudio_visible(request.user, pk)
        try:
            informe = estudio.informes.get(pk=informe_id)
        except InformeEstudioComplementario.DoesNotExist as exc:
            raise NotFound('No se encontró el informe.') from exc
        if not usuario_puede_descargar_pdf_informe(request.user, estudio, informe):
            raise PermissionDenied(
                'El PDF del estudio solo está disponible cuando el informe está validado '
                'y el estudio entregado (paciente) o validado (médico).'
            )
        try:
            return estudios_services.servir_descarga_informe_pdf(informe, user=request.user)
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages if hasattr(exc, 'messages') else str(exc)) from exc
