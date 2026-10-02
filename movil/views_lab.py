"""Pedidos de laboratorio desde la app móvil (médicos)."""

from __future__ import annotations

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from auditoria.audit_service import log_create
from laboratorio.models import PanelExamen, SolicitudExamen, TipoExamen
from laboratorio.origen_solicitud import (
    GUARDIA,
    INTERNACION_UCE,
    INTERNACION_UCO,
    _internacion_activa,
    inferir_origen_solicitud,
    label_origen_solicitud,
)
from laboratorio.serializers import SolicitudExamenCreateSerializer
from medicos.models import Medico
from pacientes.models import Paciente

from .authentication import AutenticacionMovil, RolMovil
from .models import FavoritoLabMedico, PaqueteLabContexto
from .roles import CONTEXTO_A_ORIGEN, ROLES_MOVIL_PEDIR_LAB
from medicos.ambito import contexto_lab_permitido, contextos_lab_para_api


def _rol(user) -> str:
    return str(getattr(user, 'rol', '') or '').lower()


def _assert_medico_pedido(user) -> Medico:
    if _rol(user) not in ROLES_MOVIL_PEDIR_LAB:
        raise PermissionDenied('Solo el médico puede pedir laboratorio desde la app.')
    medico = getattr(user, 'medico', None)
    if medico is None:
        try:
            medico = Medico.objects.get(user=user)
        except Medico.DoesNotExist as exc:
            raise PermissionDenied(
                'Tu usuario no tiene ficha de médico vinculada. Pedí a administración que la asocie.'
            ) from exc
    return medico


def _contexto_sugerido(paciente_id: int) -> str:
    origen = inferir_origen_solicitud(paciente_id=paciente_id)
    if origen in (INTERNACION_UCO, INTERNACION_UCE):
        return 'INTERNACION'
    if origen == GUARDIA:
        return 'GUARDIA'
    return 'AMBULATORIO'


def _flags_paciente(paciente: Paciente) -> dict:
    internacion = _internacion_activa(paciente.pk)
    sector = ''
    if internacion and internacion.cama_id and internacion.cama.sector_id:
        sector = internacion.cama.sector.nombre or ''
    return {
        'internacion_activa': internacion is not None,
        'sector_internacion': sector or None,
        'contexto_sugerido': _contexto_sugerido(paciente.pk),
    }


def _item_examen(te: TipoExamen) -> dict:
    return {
        'kind': 'examen',
        'id': te.pk,
        'codigo': te.codigo,
        'nombre': te.nombre,
    }


def _item_panel(panel: PanelExamen) -> dict:
    return {
        'kind': 'panel',
        'id': panel.pk,
        'codigo': panel.codigo,
        'nombre': panel.nombre,
        'examenes_ids': list(panel.tipos_examen.values_list('id', flat=True)),
    }


class BaseLabMovil(APIView):
    authentication_classes = [AutenticacionMovil]
    permission_classes = [RolMovil]


class PacientesLabMovil(BaseLabMovil):
    """Búsqueda operativa de pacientes para pedir lab (mín. 2 caracteres)."""

    def get(self, request):
        _assert_medico_pedido(request.user)
        q = (request.query_params.get('q') or '').strip()
        if len(q) < 2:
            raise ValidationError('Escribí al menos 2 caracteres (DNI o apellido).')
        qs = Paciente.objects.all().order_by('apellido', 'nombre')
        if q.isdigit():
            qs = qs.filter(dni__icontains=q)
        else:
            qs = qs.filter(
                Q(apellido__icontains=q)
                | Q(nombre__icontains=q)
                | Q(dni__icontains=q)
            )
        rows = []
        for p in qs[:20]:
            flags = _flags_paciente(p)
            rows.append({
                'id': p.pk,
                'dni': p.dni or '',
                'nombre': p.nombre or '',
                'apellido': p.apellido or '',
                'nombre_completo': f'{p.apellido}, {p.nombre}'.strip(', '),
                **flags,
            })
        return Response({'results': rows})


class CatalogoLabMovil(BaseLabMovil):
    """Catálogo compacto + paquetes por contexto + favoritos del médico."""

    def get(self, request):
        medico = _assert_medico_pedido(request.user)
        contexto = (request.query_params.get('contexto') or '').strip().upper()
        q = (request.query_params.get('q') or '').strip()

        paneles_qs = PanelExamen.objects.filter(activo=True).prefetch_related('tipos_examen').order_by('nombre')
        examenes_qs = TipoExamen.objects.filter(activo=True).order_by('nombre')
        if q:
            paneles_qs = paneles_qs.filter(Q(nombre__icontains=q) | Q(codigo__icontains=q))
            examenes_qs = examenes_qs.filter(Q(nombre__icontains=q) | Q(codigo__icontains=q))

        paquetes_qs = PaqueteLabContexto.objects.filter(activo=True).prefetch_related(
            'paneles', 'examenes'
        )
        if contexto in CONTEXTO_A_ORIGEN:
            paquetes_qs = paquetes_qs.filter(contexto=contexto)

        favoritos = list(
            FavoritoLabMedico.objects.filter(medico=medico)
            .select_related('tipo_examen', 'panel')
            .prefetch_related('panel__tipos_examen')
        )
        fav_examen_ids = {f.tipo_examen_id for f in favoritos if f.tipo_examen_id}
        fav_panel_ids = {f.panel_id for f in favoritos if f.panel_id}

        favoritos_out = []
        for fav in favoritos:
            if fav.panel_id and fav.panel and fav.panel.activo:
                item = _item_panel(fav.panel)
                item['favorito'] = True
                favoritos_out.append(item)
            elif fav.tipo_examen_id and fav.tipo_examen and fav.tipo_examen.activo:
                item = _item_examen(fav.tipo_examen)
                item['favorito'] = True
                favoritos_out.append(item)

        paquetes_out = []
        for paq in paquetes_qs:
            paquetes_out.append({
                'id': paq.pk,
                'codigo': paq.codigo,
                'nombre': paq.nombre,
                'contexto': paq.contexto,
                'descripcion': paq.descripcion,
                'paneles': [_item_panel(p) for p in paq.paneles.filter(activo=True)],
                'examenes': [_item_examen(e) for e in paq.examenes.filter(activo=True)],
            })

        # Sin búsqueda: limitar listado libre (complemento vía search)
        limit = 80 if q else 40
        paneles_out = []
        for p in paneles_qs[:limit]:
            item = _item_panel(p)
            item['favorito'] = p.pk in fav_panel_ids
            paneles_out.append(item)
        examenes_out = []
        for e in examenes_qs[:limit]:
            item = _item_examen(e)
            item['favorito'] = e.pk in fav_examen_ids
            examenes_out.append(item)

        return Response({
            'contextos': contextos_lab_para_api(medico),
            'favoritos': favoritos_out,
            'paquetes': paquetes_out,
            'paneles': paneles_out,
            'examenes': examenes_out,
        })


class FavoritosLabMovil(BaseLabMovil):
    def get(self, request):
        medico = _assert_medico_pedido(request.user)
        rows = []
        for fav in FavoritoLabMedico.objects.filter(medico=medico).select_related(
            'tipo_examen', 'panel'
        ).prefetch_related('panel__tipos_examen'):
            if fav.panel_id and fav.panel:
                rows.append(_item_panel(fav.panel))
            elif fav.tipo_examen_id and fav.tipo_examen:
                rows.append(_item_examen(fav.tipo_examen))
        return Response({'results': rows})

    def put(self, request):
        medico = _assert_medico_pedido(request.user)

        class ItemIn(serializers.Serializer):
            kind = serializers.ChoiceField(choices=['examen', 'panel'])
            id = serializers.IntegerField(min_value=1)

        class Body(serializers.Serializer):
            items = ItemIn(many=True)

        datos = Body(data=request.data)
        datos.is_valid(raise_exception=True)
        items = datos.validated_data['items']
        if len(items) > 40:
            raise ValidationError('Máximo 40 favoritos.')

        examen_ids = [i['id'] for i in items if i['kind'] == 'examen']
        panel_ids = [i['id'] for i in items if i['kind'] == 'panel']
        examenes_ok = set(
            TipoExamen.objects.filter(pk__in=examen_ids, activo=True).values_list('id', flat=True)
        )
        paneles_ok = set(
            PanelExamen.objects.filter(pk__in=panel_ids, activo=True).values_list('id', flat=True)
        )

        with transaction.atomic():
            FavoritoLabMedico.objects.filter(medico=medico).delete()
            orden = 0
            for item in items:
                if item['kind'] == 'examen' and item['id'] in examenes_ok:
                    FavoritoLabMedico.objects.create(
                        medico=medico, tipo_examen_id=item['id'], orden=orden
                    )
                    orden += 1
                elif item['kind'] == 'panel' and item['id'] in paneles_ok:
                    FavoritoLabMedico.objects.create(
                        medico=medico, panel_id=item['id'], orden=orden
                    )
                    orden += 1

        return self.get(request)


class OrdenesLabMovil(BaseLabMovil):
    def get(self, request):
        medico = _assert_medico_pedido(request.user)
        hoy = timezone.localdate()
        qs = (
            SolicitudExamen.objects.filter(medico_interno=medico, fecha_solicitud__date=hoy)
            .select_related('paciente')
            .order_by('-fecha_solicitud')[:50]
        )
        rows = []
        for sol in qs:
            p = sol.paciente
            rows.append({
                'id': sol.pk,
                'numero': sol.numero,
                'estado': sol.estado,
                'origen_solicitud': sol.origen_solicitud,
                'origen_display': label_origen_solicitud(sol.origen_solicitud),
                'paciente_nombre': f'{p.apellido}, {p.nombre}'.strip(', ') if p else '',
                'paciente_dni': getattr(p, 'dni', '') or '',
                'fecha_programada_toma': sol.fecha_programada_toma,
                'merged': False,
            })
        return Response({'results': rows, 'fecha': hoy.isoformat()})

    def post(self, request):
        medico = _assert_medico_pedido(request.user)

        class Body(serializers.Serializer):
            paciente_id = serializers.IntegerField(min_value=1)
            contexto = serializers.ChoiceField(choices=list(CONTEXTO_A_ORIGEN.keys()))
            examenes_ids = serializers.ListField(
                child=serializers.IntegerField(min_value=1), required=False, allow_empty=True
            )
            paneles_ids = serializers.ListField(
                child=serializers.IntegerField(min_value=1), required=False, allow_empty=True
            )
            observaciones = serializers.CharField(required=False, allow_blank=True, max_length=500)
            fecha_programada_toma = serializers.DateField(required=False)

        datos = Body(data=request.data)
        datos.is_valid(raise_exception=True)
        vd = datos.validated_data
        if not contexto_lab_permitido(medico, vd['contexto']):
            raise PermissionDenied(
                'Tu perfil es solo ambulatorio: no podés pedir laboratorio de guardia ni internación.'
            )
        examenes_ids = vd.get('examenes_ids') or []
        paneles_ids = vd.get('paneles_ids') or []
        if not examenes_ids and not paneles_ids:
            raise ValidationError('Seleccioná al menos un panel o un examen.')
        tiene_examenes = TipoExamen.objects.filter(pk__in=examenes_ids, activo=True).exists()
        tiene_paneles = PanelExamen.objects.filter(pk__in=paneles_ids, activo=True).exists()
        if not tiene_examenes and not tiene_paneles:
            raise ValidationError('Los paneles o exámenes elegidos no existen o no están activos.')

        try:
            paciente = Paciente.objects.get(pk=vd['paciente_id'])
        except Paciente.DoesNotExist as exc:
            raise ValidationError({'paciente_id': 'Paciente no encontrado.'}) from exc

        origen = CONTEXTO_A_ORIGEN[vd['contexto']]
        fecha_toma = vd.get('fecha_programada_toma') or timezone.localdate()
        payload = {
            'paciente_id': paciente.pk,
            'medico_id': medico.pk,
            'origen_solicitud': origen,
            'examenes_ids': examenes_ids,
            'paneles_ids': paneles_ids,
            'fecha_programada_toma': fecha_toma,
            'observaciones': (vd.get('observaciones') or '').strip(),
        }
        ser = SolicitudExamenCreateSerializer(data=payload, context={'request': request})
        ser.is_valid(raise_exception=True)
        solicitud = ser.save()
        merged = bool(getattr(solicitud, '_orden_merged', False))
        log_create(
            actor=request.user,
            entity=solicitud,
            module='movil',
            metadata={
                'view': 'OrdenesLabMovil.post',
                'origen_app': 'movil',
                'contexto': vd['contexto'],
                'merged': merged,
                'examenes_count': len(examenes_ids),
                'paneles_count': len(paneles_ids),
            },
        )
        out = {
            'id': solicitud.pk,
            'numero': solicitud.numero,
            'estado': solicitud.estado,
            'origen_solicitud': solicitud.origen_solicitud,
            'origen_display': label_origen_solicitud(solicitud.origen_solicitud),
            'paciente_id': paciente.pk,
            'paciente_nombre': f'{paciente.apellido}, {paciente.nombre}'.strip(', '),
            'fecha_programada_toma': solicitud.fecha_programada_toma,
            'merged': merged,
        }
        return Response(
            {
                'orden': out,
                'merged': merged,
                'mensaje': (
                    'Se agregaron los análisis a una orden abierta del mismo día.'
                    if merged
                    else 'Orden enviada a laboratorio.'
                ),
            },
            status=status.HTTP_201_CREATED if not merged else status.HTTP_200_OK,
        )


class PacienteContextoLabMovil(BaseLabMovil):
    def get(self, request, pk: int):
        _assert_medico_pedido(request.user)
        try:
            paciente = Paciente.objects.get(pk=pk)
        except Paciente.DoesNotExist:
            return Response({'detail': 'Paciente no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        from laboratorio.restricciones_frecuencia import restricciones_ensayos_para

        flags = _flags_paciente(paciente)
        origen = inferir_origen_solicitud(paciente_id=paciente.pk)
        return Response({
            'id': paciente.pk,
            'nombre_completo': f'{paciente.apellido}, {paciente.nombre}'.strip(', '),
            'dni': paciente.dni or '',
            'origen_inferido': origen,
            'origen_display': label_origen_solicitud(origen),
            'restricciones_ensayos': restricciones_ensayos_para(request.user, paciente.pk),
            **flags,
        })


class RestriccionesEnsayosLabMovil(BaseLabMovil):
    def get(self, request, pk: int):
        _assert_medico_pedido(request.user)
        try:
            Paciente.objects.get(pk=pk)
        except Paciente.DoesNotExist:
            return Response({'detail': 'Paciente no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        from laboratorio.restricciones_frecuencia import restricciones_ensayos_para

        return Response(restricciones_ensayos_para(request.user, pk))
