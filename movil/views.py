import secrets
from django.conf import settings
from datetime import timedelta, date
from django.contrib.auth import authenticate
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView
from .authentication import AutenticacionMovil, RolMovil, token_hash
from .models import SesionMovil, DispositivoPush
from pacientes.services import ensure_paciente_linked_to_user
from medicos.views import MedicoViewSet
from turnos.views import TurnoViewSet, _safe_audit
from turnos.models import Turno, Atencion
from auditoria.audit_service import log_update
from auditoria.snapshot import safe_model_snapshot


def perfil(user):
    paciente = ensure_paciente_linked_to_user(user) if str(user.rol).lower() == 'paciente' else None
    medico = getattr(user, 'medico', None)
    return {'id': user.pk, 'nombre': user.get_full_name() or user.username,
            'rol': str(user.rol).lower(), 'medico_id': getattr(medico, 'pk', None),
            'paciente_id': getattr(paciente, 'pk', None)}


class LoginThrottle(SimpleRateThrottle):
    scope = 'movil_login'
    rate = '10/min'
    def get_cache_key(self, request, view):
        return self.cache_format % {'scope': self.scope, 'ident': self.get_ident(request)}


class LoginMovil(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]

    def post(self, request):
        class Input(serializers.Serializer):
            username = serializers.CharField(max_length=150)
            password = serializers.CharField(max_length=256, trim_whitespace=False)
        datos = Input(data=request.data); datos.is_valid(raise_exception=True)
        user = authenticate(request=request, **datos.validated_data)
        if not user or str(user.rol).lower() not in ('paciente', 'medico'):
            raise AuthenticationFailed('No se pudo iniciar sesión con esas credenciales.')
        token = secrets.token_urlsafe(48)
        expira = timezone.now() + timedelta(days=30)
        SesionMovil.objects.create(user=user, token_hash=token_hash(token), expira_en=expira)
        return Response({'token': token, 'expira_en': expira.isoformat(), 'user': perfil(user)})


class BaseMovil(APIView):
    authentication_classes = [AutenticacionMovil]
    permission_classes = [RolMovil]


class MiPerfil(BaseMovil):
    def get(self, request):
        return Response(perfil(request.user))


class LogoutMovil(BaseMovil):
    def post(self, request):
        with transaction.atomic():
            request.auth.revocada = True
            request.auth.save(update_fields=['revocada'])
            DispositivoPush.objects.filter(sesion=request.auth).update(activo=False)
        return Response(status=204)


class PushMovil(BaseMovil):
    def post(self, request):
        class Input(serializers.Serializer):
            token = serializers.RegexField(r'^(ExponentPushToken|ExpoPushToken)\[[A-Za-z0-9_-]+\]$', max_length=255)
            plataforma = serializers.ChoiceField(choices=['android', 'ios'])
        datos = Input(data=request.data); datos.is_valid(raise_exception=True)
        with transaction.atomic():
            DispositivoPush.objects.update_or_create(token=datos.validated_data['token'], defaults={
                'sesion': request.auth, 'plataforma': datos.validated_data['plataforma'], 'activo': True})
        return Response({'activo': True, 'servicio_activo': settings.MOBILE_PUSH_ENABLED})

    def delete(self, request):
        DispositivoPush.objects.filter(sesion=request.auth).update(activo=False)
        return Response(status=204)


class TurnoMovilSerializer(serializers.ModelSerializer):
    paciente_nombre = serializers.CharField(source='paciente.nombre_completo', default='')
    medico_nombre = serializers.CharField(source='medico.nombre_completo', default='')
    medico_id = serializers.IntegerField(read_only=True)
    tipo = serializers.SerializerMethodField()
    def get_tipo(self, obj):
        from medicos.agenda import tipo_para_recurso
        return tipo_para_recurso(obj.recurso)
    class Meta:
        model = Turno
        fields = ['id', 'medico_id', 'medico_nombre', 'paciente_nombre', 'fecha_hora_inicio',
                  'fecha_hora_fin', 'estado', 'asistencia_confirmada_en', 'tipo']
        read_only_fields = fields


class TurnosMovil(TurnoViewSet):
    authentication_classes = [AutenticacionMovil]
    permission_classes = [RolMovil]
    serializer_class = TurnoMovilSerializer

    def get_queryset(self):
        # El rol médico conserva únicamente su propia agenda incluso con is_staff.
        qs = Turno.objects.select_related('medico', 'paciente', 'recurso')
        if str(self.request.user.rol).lower() == 'medico':
            qs = qs.filter(medico__user=self.request.user)
        else:
            paciente = ensure_paciente_linked_to_user(self.request.user)
            qs = qs.filter(paciente=paciente) if paciente else qs.none()
        fecha = self.request.query_params.get('fecha')
        if fecha:
            try:
                qs = qs.filter(fecha_hora_inicio__date=date.fromisoformat(fecha))
            except ValueError:
                raise ValidationError('Fecha inválida.') from None
        return qs.order_by('fecha_hora_inicio')

    def confirmar_asistencia(self, request, pk=None):
        if str(request.user.rol).lower() != 'paciente':
            raise PermissionDenied('La asistencia la confirma el propio paciente.')
        with transaction.atomic():
            turno = self._get_turno_locked_for_estado_action(pk)
            if turno.estado not in ('RESERVADO', 'CONFIRMADO') or turno.fecha_hora_inicio <= timezone.now():
                raise ValidationError('Este turno ya no admite confirmación de asistencia.')
            if Atencion.objects.filter(turno=turno).exists():
                raise ValidationError('La atención de este turno ya comenzó.')
            if turno.asistencia_confirmada_en is None:
                before = safe_model_snapshot(turno)
                turno.asistencia_confirmada_en = timezone.now()
                turno.save(update_fields=['asistencia_confirmada_en', 'updated_at'])
                _safe_audit(log_update, actor=request.user, entity=turno, before=before,
                    module='turnos', metadata={'accion': 'confirmar_asistencia_paciente'})
        return Response(self.get_serializer(turno).data)

    def reprogramar_horario(self, request, pk=None):
        from medicos.models import DisponibilidadMedico
        from medicos.agenda import validar_reserva, DURACION
        from turnos import turno_estado
        class Input(serializers.Serializer):
            horario_id = serializers.IntegerField(min_value=1)
            inicio = serializers.DateTimeField()
            motivo = serializers.CharField(max_length=255, allow_blank=False)
        datos = Input(data=request.data); datos.is_valid(raise_exception=True)
        with transaction.atomic():
            turno = self._get_turno_locked_for_estado_action(pk)
            if not turno_estado.puede_reprogramar_turno(request.user, turno):
                raise PermissionDenied('No puede reprogramar este turno.')
            try:
                horario = DisponibilidadMedico.objects.select_related('medico', 'recurso').get(
                    pk=datos.validated_data['horario_id'], medico_id=turno.medico_id, activo=True)
            except DisponibilidadMedico.DoesNotExist:
                raise ValidationError('Seleccione un horario del mismo médico.') from None
            from medicos.agenda import tipo_para_recurso
            if horario.tipo != tipo_para_recurso(turno.recurso):
                raise ValidationError('Seleccione el mismo tipo de atención.')
            inicio = datos.validated_data['inicio']
            validar_reserva(horario.medico, inicio, inicio+DURACION, horario.recurso,
                            excluir=turno.pk, exigir_horario=True, horario_id=horario.pk)
            try:
                resultado = turno_estado.reprogramar_turno(turno, actor=request.user,
                    fecha_hora_inicio=inicio, fecha_hora_fin=inicio+DURACION,
                    motivo=datos.validated_data['motivo'], recurso=horario.recurso)
            except turno_estado.TurnoEstadoTransitionError as exc:
                raise ValidationError(str(exc)) from exc
        return Response(self.get_serializer(resultado.turno).data)


class MedicosMovil(MedicoViewSet):
    authentication_classes = [AutenticacionMovil]
    permission_classes = [RolMovil]


class InstitucionMovil(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        if not settings.MOBILE_INSTITUTION_CODE or not settings.MOBILE_INSTITUTION_NAME:
            return Response({'detail': 'Institución móvil no configurada.'}, status=503)
        return Response({'code': settings.MOBILE_INSTITUTION_CODE, 'name': settings.MOBILE_INSTITUTION_NAME})
