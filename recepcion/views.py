from django.utils import timezone
from django.db.models import Prefetch, Q
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, NotFound

from pacientes.models import Paciente
from turnos.models import Turno

from .models import LlegadaRecepcion, PuestoRecepcion, ReglaRuteoRecepcion
from .permissions import (
    RecepcionConfigPermission,
    RecepcionOperacionPermission,
    es_laboratorio_recepcion,
    es_medico_recepcion,
    es_solo_laboratorio,
    medico_ids_para_cola,
    medico_perfil,
    medico_puede_ver_llegada,
    puede_derivar_a_medico,
    puede_llamar_o_atender,
    puede_operar_recepcion,
)
from .serializers import (
    CoberturaRecepcionSerializer,
    LlegadaRecepcionSerializer,
    PantallaLlamadoSerializer,
    PuestoRecepcionSerializer,
    ReglaRuteoRecepcionSerializer,
)
from . import services
from .kiosco_origen import resolver_origen_espera_kiosco
from .ruteo import contexto_desde_turno, resolver_puesto, ContextoRuteo, tipo_actividad_desde_turno


class PuestoRecepcionViewSet(viewsets.ModelViewSet):
    queryset = PuestoRecepcion.objects.all()
    serializer_class = PuestoRecepcionSerializer
    permission_classes = [IsAuthenticated, RecepcionConfigPermission]
    filterset_fields = ['activo', 'modo', 'ubicacion']
    ordering = ['orden', 'id']

    def get_queryset(self):
        qs = super().get_queryset()
        from usuarios.sedes import sedes_efectivas

        sedes = sedes_efectivas(self.request.user)
        if sedes is not None:
            qs = qs.filter(Q(ubicacion__isnull=True) | Q(ubicacion='') | Q(ubicacion__in=sedes))
        return qs


class ReglaRuteoRecepcionViewSet(viewsets.ModelViewSet):
    queryset = ReglaRuteoRecepcion.objects.select_related('puesto', 'recurso', 'medico')
    serializer_class = ReglaRuteoRecepcionSerializer
    permission_classes = [IsAuthenticated, RecepcionConfigPermission]
    filterset_fields = ['activo', 'puesto', 'tipo_actividad']
    ordering = ['prioridad', 'id']

    def get_queryset(self):
        qs = super().get_queryset()
        from usuarios.sedes import sedes_efectivas

        sedes = sedes_efectivas(self.request.user)
        if sedes is not None:
            qs = qs.filter(
                Q(puesto__ubicacion__isnull=True)
                | Q(puesto__ubicacion='')
                | Q(puesto__ubicacion__in=sedes)
            )
        return qs


class LlegadaRecepcionViewSet(viewsets.ModelViewSet):
    serializer_class = LlegadaRecepcionSerializer
    permission_classes = [IsAuthenticated, RecepcionOperacionPermission]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']
    filterset_fields = ['puesto', 'estado_flujo', 'tipo_actividad', 'fecha']

    def get_queryset(self):
        qs = LlegadaRecepcion.objects.select_related(
            'paciente',
            'puesto',
            'turno',
            'turno__medico',
            'turno__recurso',
            'destino_recurso',
        ).prefetch_related(
            Prefetch('turno'),
        )
        fecha = self.request.query_params.get('fecha') or timezone.localdate().isoformat()
        qs = qs.filter(fecha=fecha)
        puesto = self.request.query_params.get('puesto')
        if puesto:
            qs = qs.filter(puesto_id=puesto)
        user = self.request.user
        # Laboratorio: solo cola L (extracciones).
        if es_solo_laboratorio(user):
            qs = qs.filter(tipo_actividad='EXTRACCION').exclude(
                estado_flujo__in=['CANCELADO', 'NO_ASISTIO', 'PROGRAMADO']
            )
        # Médico: solo pacientes de sus turnos (incluye homónimos huérfanos).
        elif es_medico_recepcion(user) and not getattr(user, 'is_superuser', False):
            ids = medico_ids_para_cola(user)
            if not ids:
                return qs.none()
            # Solo cola clínica (tras check-in de secretaría). No recepción / llamado a ventanilla.
            qs = qs.filter(turno__medico_id__in=ids).filter(
                Q(
                    estado_flujo__in=[
                        LlegadaRecepcion.EstadoFlujo.EN_ESPERA,
                        LlegadaRecepcion.EstadoFlujo.EN_ATENCION,
                        LlegadaRecepcion.EstadoFlujo.ATENDIDO,
                    ]
                )
                | Q(
                    estado_flujo=LlegadaRecepcion.EstadoFlujo.LLAMADO,
                    zona_llamado='MEDICO',
                )
            )
        # Secretaría: no L; filtrar por tipos de su cobertura del día (si tiene).
        elif not getattr(user, 'is_superuser', False):
            if puede_operar_recepcion(user) and not es_laboratorio_recepcion(user):
                qs = qs.exclude(tipo_actividad='EXTRACCION')
                cov = services.cobertura_hoy(usuario=user)
                if cov and cov.tipos:
                    # En espera recepción: solo mis tipos. Ya derivados/llamados: visibles.
                    qs = qs.filter(
                        Q(
                            estado_flujo=LlegadaRecepcion.EstadoFlujo.EN_ESPERA_RECEPCION,
                            tipo_actividad__in=list(cov.tipos),
                        )
                        | ~Q(estado_flujo=LlegadaRecepcion.EstadoFlujo.EN_ESPERA_RECEPCION)
                    )
        from usuarios.sedes import sedes_efectivas

        sedes = sedes_efectivas(self.request.user)
        if sedes is not None:
            qs = qs.filter(
                Q(puesto__ubicacion__isnull=True)
                | Q(puesto__ubicacion='')
                | Q(puesto__ubicacion__in=sedes)
                | Q(
                    puesto__isnull=True,
                    turno__recurso__ubicacion__in=sedes,
                )
            )
        return qs.order_by('checkin_en', 'id')

    def create(self, request, *args, **kwargs):
        raise ValidationError('Usá checkin-turno o checkin-walkin.')

    @action(detail=False, methods=['post'], url_path='checkin-turno')
    def checkin_turno(self, request):
        turno_id = request.data.get('turno_id')
        if not turno_id:
            raise ValidationError({'turno_id': 'Requerido.'})
        try:
            turno = Turno.objects.select_related('recurso', 'medico', 'paciente').get(pk=turno_id)
        except Turno.DoesNotExist:
            raise NotFound('Turno no encontrado.')
        # Prefetch estudio si existe
        try:
            _ = turno.estudio_complementario
        except Exception:
            pass
        llegada = services.checkin_turno(
            turno=turno,
            puesto_id=request.data.get('puesto_id'),
            user=request.user,
        )
        data = LlegadaRecepcionSerializer(llegada).data
        data['mensaje_paciente'] = getattr(llegada, '_mensaje_paciente', data.get('mensaje_paciente'))
        return Response(data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='checkin-walkin')
    def checkin_walkin(self, request):
        paciente_id = request.data.get('paciente_id')
        if not paciente_id:
            raise ValidationError({'paciente_id': 'Requerido.'})
        try:
            paciente = Paciente.objects.get(pk=paciente_id)
        except Paciente.DoesNotExist:
            raise NotFound('Paciente no encontrado.')
        llegada = services.checkin_walkin(
            paciente=paciente,
            tipo_actividad=request.data.get('tipo_actividad') or 'SIN_TURNO',
            puesto_id=request.data.get('puesto_id'),
            notas=request.data.get('notas') or '',
        )
        data = LlegadaRecepcionSerializer(llegada).data
        data['mensaje_paciente'] = getattr(llegada, '_mensaje_paciente', None)
        return Response(data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='mover-puesto')
    def mover_puesto(self, request, pk=None):
        llegada = self.get_object()
        puesto_id = request.data.get('puesto_id')
        if not puesto_id:
            raise ValidationError({'puesto_id': 'Requerido.'})
        llegada = services.mover_puesto(llegada, int(puesto_id))
        return Response(LlegadaRecepcionSerializer(llegada).data)

    @action(detail=True, methods=['post'], url_path='derivar-espera')
    def derivar_espera(self, request, pk=None):
        """Check-in administrativo: pasa de recepción a cola del médico."""
        llegada = self.get_object()
        if not puede_derivar_a_medico(request.user, llegada):
            raise ValidationError(
                {'detalle': 'No podés pasar esta llegada a la cola del médico.'}
            )
        llegada = services.derivar_a_espera_clinica(llegada)
        return Response(LlegadaRecepcionSerializer(llegada).data)

    @action(detail=True, methods=['post'], url_path='llamar')
    def llamar(self, request, pk=None):
        llegada = self.get_object()
        if not puede_llamar_o_atender(request.user, llegada):
            if llegada.tipo_actividad == 'EXTRACCION':
                raise ValidationError(
                    {'detalle': 'Extracción/laboratorio: solo el usuario de laboratorio puede llamar.'}
                )
            raise ValidationError(
                {'detalle': 'Este paciente ya está en la cola del médico; solo el médico puede llamarlo.'}
            )
        llegada = services.llamar_paciente(llegada, user=request.user)
        return Response(LlegadaRecepcionSerializer(llegada).data)

    @action(detail=True, methods=['post'], url_path='en-atencion')
    def en_atencion(self, request, pk=None):
        llegada = self.get_object()
        if not puede_llamar_o_atender(request.user, llegada):
            raise ValidationError(
                {'detalle': 'Este paciente ya está con el médico; secretaría no marca atención.'}
            )
        llegada = services.marcar_en_atencion(llegada)
        return Response(LlegadaRecepcionSerializer(llegada).data)

    @action(detail=True, methods=['post'], url_path='atendido')
    def atendido(self, request, pk=None):
        llegada = self.get_object()
        if not puede_llamar_o_atender(request.user, llegada):
            raise ValidationError(
                {'detalle': 'Este paciente ya está con el médico; secretaría no marca atendido.'}
            )
        llegada = services.marcar_atendido(llegada)
        return Response(LlegadaRecepcionSerializer(llegada).data)

    @action(detail=True, methods=['post'], url_path='no-asistio')
    def no_asistio(self, request, pk=None):
        llegada = services.marcar_no_asistio(self.get_object())
        return Response(LlegadaRecepcionSerializer(llegada).data)

    @action(detail=False, methods=['post'], url_path='atendido-por-turno')
    def atendido_por_turno(self, request):
        """Al guardar/cerrar consulta: pasar la llegada del turno a ATENDIDO."""
        turno_id = request.data.get('turno_id')
        if not turno_id:
            raise ValidationError({'turno_id': 'Requerido.'})
        try:
            turno_id = int(turno_id)
        except (TypeError, ValueError) as exc:
            raise ValidationError({'turno_id': 'Inválido.'}) from exc
        llegada = (
            LlegadaRecepcion.objects.select_related('turno', 'turno__medico')
            .filter(turno_id=turno_id, fecha=timezone.localdate())
            .exclude(
                estado_flujo__in=[
                    LlegadaRecepcion.EstadoFlujo.CANCELADO,
                    LlegadaRecepcion.EstadoFlujo.NO_ASISTIO,
                ]
            )
            .order_by('-id')
            .first()
        )
        if not llegada:
            return Response({'ok': True, 'actualizado': False})
        if es_medico_recepcion(request.user) and not getattr(request.user, 'is_superuser', False):
            if not medico_puede_ver_llegada(request.user, llegada):
                raise ValidationError({'detalle': 'No podés marcar atendido este turno.'})
        ya_atendido = llegada.estado_flujo == LlegadaRecepcion.EstadoFlujo.ATENDIDO
        if not ya_atendido:
            llegada = services.marcar_atendido(llegada)
        return Response(
            {
                'ok': True,
                'actualizado': not ya_atendido,
                'llegada': LlegadaRecepcionSerializer(llegada).data,
            }
        )

    @action(detail=False, methods=['get'], url_path='tablero')
    def tablero(self, request):
        """Turnos de hoy + llegadas del puesto, para el tablero operativo."""
        from datetime import datetime, timedelta

        fecha = request.query_params.get('fecha') or timezone.localdate().isoformat()
        puesto_id = request.query_params.get('puesto')
        llegadas = list(self.filter_queryset(self.get_queryset()))
        start = timezone.make_aware(datetime.strptime(fecha, '%Y-%m-%d'))
        end = start + timedelta(days=1)

        turnos_qs = (
            Turno.objects.filter(
                fecha_hora_inicio__gte=start,
                fecha_hora_inicio__lt=end,
            )
            .exclude(estado='CANCELADO')
            .filter(paciente__isnull=False)
            .select_related('paciente', 'medico', 'recurso')
        )
        if es_medico_recepcion(request.user) and not getattr(request.user, 'is_superuser', False):
            ids = medico_ids_para_cola(request.user)
            turnos_qs = turnos_qs.filter(medico_id__in=ids) if ids else turnos_qs.none()
        llegada_turno_ids = {l.turno_id for l in llegadas if l.turno_id}
        pendientes = []
        for t in turnos_qs:
            if t.id in llegada_turno_ids:
                continue
            try:
                ctx = contexto_desde_turno(t)
                r = resolver_puesto(ctx)
                if puesto_id and str(r.puesto.id) != str(puesto_id):
                    continue
                pendientes.append(
                    {
                        'turno_id': t.id,
                        'paciente_id': t.paciente_id,
                        'paciente_nombre': f'{t.paciente.apellido}, {t.paciente.nombre}',
                        'paciente_dni': t.paciente.dni,
                        'medico_nombre': (
                            f'{t.medico.apellido}, {t.medico.nombre}' if t.medico else ''
                        ),
                        'recurso_nombre': t.recurso.nombre if t.recurso else '',
                        'tipo_actividad': ctx.tipo_actividad,
                        'inicio': t.fecha_hora_inicio,
                        'estado': t.estado,
                        'puesto_sugerido_id': r.puesto.id,
                        'puesto_sugerido_label': r.puesto.label_publico,
                        'mensaje': r.mensaje,
                    }
                )
            except Exception:
                continue

        return Response(
            {
                'fecha': fecha,
                'llegadas': LlegadaRecepcionSerializer(llegadas, many=True).data,
                'turnos_pendientes_checkin': pendientes,
            }
        )


def _ser_item(obj):
    return PantallaLlamadoSerializer(obj).data if obj else None


def _pack_mitad_tv(*, llamando, proximo, recientes) -> dict:
    """
    llamando: todos en LLAMADO (el más reciente = grande; el resto = historial llamando).
    proximo: siguiente en cola (debajo).
    historial: recién atendidos (arriba, chicos).
    """
    llamando_list = list(llamando)
    recientes_data = PantallaLlamadoSerializer(recientes, many=True).data
    llamando_data = PantallaLlamadoSerializer(llamando_list, many=True).data
    actual = llamando_data[0] if llamando_data else None
    otros_llamando = llamando_data[1:] if len(llamando_data) > 1 else []
    prox = _ser_item(proximo)
    return {
        'actual': actual,
        'llamando': llamando_data,
        'proximo': prox,
        'historial': recientes_data,
        'otros_llamando': otros_llamando,
        # compat
        'pendientes': list(llamando_data) + ([prox] if prox else []) + list(recientes_data),
    }


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def pantalla_llamados(request):
    """
    TV de sala en 2 mitades (sin PHI sensible).

    Por mitad:
    - actual / llamando[0]: último LLAMADO (grande)
    - llamando / otros_llamando: resto aún en LLAMADO (historial de llamando)
    - proximo: siguiente en cola (debajo)
    - historial: EN_ATENCION/ATENDIDO recientes (arriba)
    """
    from datetime import timedelta
    limite = min(int(request.query_params.get('limit') or 8), 20)
    desde = timezone.now() - timedelta(hours=4)
    base = LlegadaRecepcion.objects.select_related(
        'paciente', 'puesto', 'destino_recurso', 'turno'
    ).filter(fecha=timezone.localdate())

    zona_rec = Q(zona_llamado='RECEPCION') | Q(zona_llamado='') | Q(zona_llamado__isnull=True)

    llamando_rec = list(
        base.filter(
            estado_flujo=LlegadaRecepcion.EstadoFlujo.LLAMADO,
            llamado_en__gte=desde,
        )
        .filter(zona_rec)
        .exclude(zona_llamado='MEDICO')
        .order_by('-llamado_en')[:limite]
    )
    proximo_rec = (
        base.filter(estado_flujo=LlegadaRecepcion.EstadoFlujo.EN_ESPERA_RECEPCION)
        .order_by('checkin_en', 'id')
        .first()
    )
    recientes_rec = list(
        base.filter(
            estado_flujo__in=[
                LlegadaRecepcion.EstadoFlujo.EN_ATENCION,
                LlegadaRecepcion.EstadoFlujo.ATENDIDO,
            ],
            llamado_en__gte=desde,
        )
        .filter(zona_rec)
        .exclude(zona_llamado='MEDICO')
        .order_by('-llamado_en', '-updated_at')[:limite]
    )

    llamando_med = list(
        base.filter(
            estado_flujo=LlegadaRecepcion.EstadoFlujo.LLAMADO,
            zona_llamado='MEDICO',
            llamado_en__gte=desde,
        ).order_by('-llamado_en')[:limite]
    )
    proximo_med = (
        base.filter(estado_flujo=LlegadaRecepcion.EstadoFlujo.EN_ESPERA)
        .exclude(tipo_actividad='EXTRACCION')
        .order_by('checkin_en', 'id')
        .first()
    )
    recientes_med = list(
        base.filter(
            estado_flujo__in=[
                LlegadaRecepcion.EstadoFlujo.EN_ATENCION,
                LlegadaRecepcion.EstadoFlujo.ATENDIDO,
            ],
            zona_llamado='MEDICO',
            llamado_en__gte=desde,
        ).order_by('-llamado_en', '-updated_at')[:limite]
    )

    mitad_recepcion = _pack_mitad_tv(
        llamando=llamando_rec, proximo=proximo_rec, recientes=recientes_rec
    )
    mitad_medico = _pack_mitad_tv(
        llamando=llamando_med, proximo=proximo_med, recientes=recientes_med
    )

    todos_llamados = (
        base.filter(
            estado_flujo=LlegadaRecepcion.EstadoFlujo.LLAMADO,
            llamado_en__gte=desde,
        ).order_by('-llamado_en')[:limite]
    )

    return Response(
        {
            'mitad_recepcion': mitad_recepcion,
            'mitad_medico': mitad_medico,
            'llamados': PantallaLlamadoSerializer(todos_llamados, many=True).data,
        }
    )


def _payload_kiosco(
    llegada,
    *,
    modo: str,
    prioridad: dict,
    tipo_actividad: str,
    request=None,
    prefijo: str = '',
):
    llegada = services.ensure_token_publico(llegada)
    path = f'/espera/{llegada.token_publico}'
    origen_info = resolver_origen_espera_kiosco(request)
    espera_origin = origen_info.get('espera_origin') or ''
    espera_url = f'{espera_origin}{path}' if espera_origin else ''
    msg_default = getattr(
        llegada, '_mensaje_paciente', f'Andá al {llegada.puesto.label_publico}.'
    )
    if tipo_actividad == 'EXTRACCION':
        msg_default = (
            f'Tu código es {llegada.codigo_llamado or "—"}. '
            f'Esperá el llamado de laboratorio ({llegada.puesto.label_publico}).'
        )
    else:
        msg_default = (
            f'Tu código es {llegada.codigo_llamado or "—"}. '
            f'Esperá en recepción ({llegada.puesto.label_publico}).'
        )
    return {
        'ok': True,
        'modo': modo,
        'mensaje': msg_default,
        'puesto': llegada.puesto.label_publico,
        'destino': llegada.destino_label
        or (llegada.destino_recurso.nombre if llegada.destino_recurso_id else ''),
        'numero_orden_dia': llegada.numero_orden_dia,
        'codigo_llamado': llegada.codigo_llamado,
        'prefijo_llamado': llegada.prefijo_llamado or prefijo,
        'tipo_actividad': tipo_actividad,
        'llegada_id': llegada.id,
        'prioridad': prioridad,
        'token_espera': llegada.token_publico,
        'espera_path': path,
        'espera_origin': espera_origin,
        'espera_url': espera_url,
        'espera_origen_fuente': origen_info.get('fuente') or '',
        'espera_es_lan': bool(origen_info.get('es_lan')),
    }


@csrf_exempt
@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def kiosco_config(request):
    """Orígenes LAN configurados para el QR (sin Internet / dominio público)."""
    info = resolver_origen_espera_kiosco(request)
    return Response(
        {
            'ok': True,
            'espera_origin': info.get('espera_origin') or '',
            'espera_origins': info.get('espera_origins') or [],
            'lan_ips': info.get('lan_ips') or [],
            'fuente': info.get('fuente') or '',
            'es_lan': bool(info.get('es_lan')),
        }
    )


@csrf_exempt
@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def kiosco_qr_png(request):
    """QR PNG generado en el servidor (offline; no depende de APIs externas)."""
    import io

    import qrcode
    from django.http import HttpResponse

    data = (request.query_params.get('data') or '').strip()
    if not data or len(data) > 2048:
        raise ValidationError({'detail': 'data inválido.'})
    # Enlaces http(s) o rutas de espera / kiosco de anuncio
    if not (
        data.startswith('http://')
        or data.startswith('https://')
        or data.startswith('/espera/')
        or data.startswith('/kiosco-recepcion')
    ):
        raise ValidationError({'detail': 'Solo se permiten URLs de anuncio o espera.'})
    img = qrcode.make(data, border=2)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return HttpResponse(buf.getvalue(), content_type='image/png')


@csrf_exempt
@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def espera_paciente(request, token: str):
    """
    Estado público de una llegada (QR en celular). Sin DNI ni nombre completo.
    """
    token = (token or '').strip()
    if len(token) < 12:
        raise NotFound()
    llegada = (
        LlegadaRecepcion.objects.select_related(
            'puesto', 'destino_recurso', 'turno', 'paciente'
        )
        .filter(token_publico=token)
        .first()
    )
    if not llegada:
        raise NotFound()

    destino = llegada.destino_label or (
        llegada.destino_recurso.nombre if llegada.destino_recurso_id else ''
    )
    prioridad = services.evaluar_prioridad_horario(
        turno=llegada.turno if llegada.turno_id else None
    )
    llamado = llegada.estado_flujo == LlegadaRecepcion.EstadoFlujo.LLAMADO
    finalizado = llegada.estado_flujo in (
        LlegadaRecepcion.EstadoFlujo.ATENDIDO,
        LlegadaRecepcion.EstadoFlujo.NO_ASISTIO,
        LlegadaRecepcion.EstadoFlujo.CANCELADO,
        LlegadaRecepcion.EstadoFlujo.EN_ATENCION,
    )

    if llamado:
        titulo = 'Te están llamando'
        detalle = f'Acercate a {destino or llegada.puesto.label_publico}.'
    elif llegada.estado_flujo == LlegadaRecepcion.EstadoFlujo.EN_ATENCION:
        titulo = 'En atención'
        detalle = 'Ya estás siendo atendido.'
    elif finalizado:
        titulo = 'Listo'
        detalle = 'Tu turno de recepción finalizó.'
    else:
        titulo = 'En espera'
        detalle = (
            f'{prioridad.get("detalle") or "Te vamos a avisar acá cuando te llamen."} '
            f'Puesto: {llegada.puesto.label_publico}.'
        )

    return Response(
        {
            'ok': True,
            'estado_flujo': llegada.estado_flujo,
            'llamado': llamado,
            'finalizado': finalizado,
            'titulo': titulo,
            'detalle': detalle.strip(),
            'puesto': llegada.puesto.label_publico,
            'destino': destino,
            'numero_orden_dia': llegada.numero_orden_dia,
            'codigo_llamado': llegada.codigo_llamado,
            'prefijo_llamado': llegada.prefijo_llamado,
            'prioridad': prioridad,
            'llamado_en': llegada.llamado_en,
            'paciente_nombre_publico': services.nombre_publico_paciente(llegada.paciente),
        }
    )


@csrf_exempt
@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def espera_ya_voy(request, token: str):
    """Paciente confirma el llamado («Ya voy»): sale de TV mitad médico / recepción."""
    token = (token or '').strip()
    if len(token) < 12:
        raise NotFound()
    llegada = LlegadaRecepcion.objects.filter(token_publico=token).first()
    if not llegada:
        raise NotFound()
    llegada = services.paciente_ya_voy(llegada)
    return Response(
        {
            'ok': True,
            'estado_flujo': llegada.estado_flujo,
            'codigo_llamado': llegada.codigo_llamado,
        }
    )


@csrf_exempt
@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def kiosco_checkin(request):
    """
    Anuncio público por QR papel: solo recepción (puesto 1) o sala de extracción.
    Consulta/estudio con turno: app «Estoy en sala» (no este endpoint).
    """
    dni = (request.data.get('dni') or '').strip()
    apellido = (request.data.get('apellido') or '').strip()
    motivo = (request.data.get('tipo_actividad') or request.data.get('motivo') or '').strip().upper()
    if motivo not in services.MOTIVOS_KIOSCO_PAPEL:
        raise ValidationError(
            {
                'detail': (
                    'Desde el QR solo podés anunciarte en recepción (puesto 1) '
                    'o en la sala de extracción. Si tenés turno, usá la app.'
                )
            }
        )
    if len(dni) < 6 or len(apellido) < 2:
        raise ValidationError({'detail': 'Ingresá DNI y apellido válidos.'})

    pacientes = Paciente.objects.filter(dni__iexact=dni)
    if not pacientes.exists():
        raise ValidationError({'detail': 'No encontramos ese DNI. Acercate a recepción.'})

    match = None
    ap_norm = apellido.upper()
    for p in pacientes:
        if (p.apellido or '').upper() == ap_norm or ap_norm in (p.apellido or '').upper():
            match = p
            break
    if not match:
        raise ValidationError({'detail': 'DNI y apellido no coinciden. Acercate a recepción.'})

    prefijo = services.prefijo_desde_motivo(motivo)
    puesto_id = None
    if motivo == 'SIN_TURNO':
        puesto_id = services.puesto_recepcion_1().pk

    llegada = services.checkin_walkin(
        paciente=match,
        tipo_actividad=motivo,
        puesto_id=puesto_id,
        motivo=motivo,
    )
    prioridad = services.evaluar_prioridad_horario(turno=None)
    return Response(
        _payload_kiosco(
            llegada,
            modo='walkin',
            prioridad=prioridad,
            tipo_actividad=motivo,
            request=request,
            prefijo=prefijo,
        )
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated, RecepcionOperacionPermission])
def resolver_puesto_preview(request):
    ctx = ContextoRuteo(
        tipo_actividad=request.data.get('tipo_actividad') or 'CONSULTA',
        tipo_recurso=request.data.get('tipo_recurso') or '',
        recurso_id=request.data.get('recurso_id'),
        medico_id=request.data.get('medico_id'),
    )
    r = resolver_puesto(ctx)
    return Response(
        {
            'puesto_id': r.puesto.id,
            'puesto_nombre': r.puesto.nombre,
            'label_publico': r.puesto.label_publico,
            'mensaje': r.mensaje,
            'motivo': r.motivo,
            'regla_id': r.regla_id,
        }
    )


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated, RecepcionOperacionPermission])
def cobertura_hoy(request):
    """Cobertura dinámica del día: puesto físico + tipos que atiende la secretaría."""
    fecha = timezone.localdate()
    if request.method == 'GET':
        cov = services.cobertura_hoy(usuario=request.user, fecha=fecha)
        puestos = PuestoRecepcion.objects.filter(activo=True).exclude(
            codigo='sala-extraccion'
        ).order_by('orden', 'id')
        payload = {
            'fecha': fecha.isoformat(),
            'cobertura': CoberturaRecepcionSerializer(cov).data if cov else None,
            'puestos_disponibles': PuestoRecepcionSerializer(puestos, many=True).data,
            'tipos_disponibles': list(services.TIPOS_COBERTURA_SECRETARIA),
        }
        return Response(payload)

    puesto_id = request.data.get('puesto') or request.data.get('puesto_id')
    tipos = request.data.get('tipos')
    sede = request.data.get('sede')
    if not puesto_id:
        return Response({'detail': 'Indicá el puesto donde estás hoy.'}, status=status.HTTP_400_BAD_REQUEST)
    if tipos is None:
        return Response({'detail': 'Indicá los tipos que atendés (T/S/E/P).'}, status=status.HTTP_400_BAD_REQUEST)
    if not isinstance(tipos, list):
        return Response({'detail': 'tipos debe ser una lista.'}, status=status.HTTP_400_BAD_REQUEST)
    cov = services.guardar_cobertura_hoy(
        usuario=request.user,
        puesto_id=int(puesto_id),
        tipos=tipos,
        sede=sede,
        fecha=fecha,
    )
    return Response(CoberturaRecepcionSerializer(cov).data)
