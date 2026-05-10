"""ViewSets y vistas de la app ``usuarios`` (capa de identidad y auth).

Hardening aplicado en este módulo (sin tocar routing global):

- ``UserSerializer`` bloquea escalada a ``is_superuser``/``is_staff``/
  ``rol='admin'`` salvo que el actor sea ``superuser`` (validado contra
  ``context['request'].user``).
- ``UserViewSet.bulk_activate``/``bulk_deactivate`` intersectan los IDs
  recibidos con ``self.get_queryset()`` para que un staff regular no pueda
  alcanzar superusers no visibles.
- ``UserViewSet.destroy`` está bloqueado (405): no se permite borrado físico
  de usuarios (trazabilidad y FKs); usar ``activate``/``deactivate``.
- ``UserProfileViewSet.destroy`` está bloqueado (405). El perfil contiene
  PHI (alergias, medicamentos, contacto de emergencia) y no debe poder
  borrarse físicamente vía API.
- Acciones de escritura (create/update/activate/deactivate/bulk_*/
  change_password) y operaciones sobre ``UserProfile`` se auditan en modo
  best-effort vía ``_safe_audit`` (un fallo de auditoría nunca corta el
  flujo principal).
- ``PacienteRegisterView`` deja de loggear DNI/email completos y devuelve
  mensajes genéricos ante errores internos para no filtrar trazas de DB.
"""
import hashlib
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password  # noqa: F401  (re-export usage)
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction, models  # noqa: F401  (models re-exported)
from rest_framework import generics, permissions, serializers, status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView  # noqa: F401  (re-export)

from auditoria.audit_service import log_create, log_update
from auditoria.context import get_request_id
from auditoria.snapshot import safe_model_snapshot

from .models import UserProfile
from .serializers import (
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
    PacienteRegistrationSerializer,
    RefreshTokenSerializer,  # noqa: F401  (re-export)
    UserDetailSerializer,
    UserListSerializer,
    UserProfileSerializer,
    UserSerializer,
)

User = get_user_model()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _safe_audit(callable_, *args, **kwargs):
    """Wrapper best-effort: fallos de auditoría nunca rompen el flujo principal."""
    try:
        callable_(*args, **kwargs)
    except Exception:  # pragma: no cover - defensiva
        logger.exception(
            "Fallo silencioso en auditoría: %s",
            getattr(callable_, "__name__", "audit"),
        )


def _hash_pii(value: str) -> str:
    """Devuelve un hash corto y estable para correlacionar sin exponer PII.

    Se usa solo en logs (no en respuestas al cliente). Permite seguir
    eventos del mismo DNI/email entre líneas de log sin volcar el dato.
    """
    if not value:
        return "<empty>"
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return digest[:12]


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------
class CustomTokenObtainPairView(TokenObtainPairView):
    """Vista personalizada para obtener tokens JWT con metadata extra del usuario."""

    serializer_class = CustomTokenObtainPairSerializer


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
class UserViewSet(viewsets.ModelViewSet):
    """Gestión de usuarios por administradores (``IsAdminUser`` = ``is_staff``).

    Visibilidad (``get_queryset``):
    - ``is_superuser``: ve todos los usuarios.
    - ``is_staff`` regular: ve usuarios no-superuser únicamente.

    Anti-escalada en serializer y en bulk actions: aunque ``IsAdminUser``
    permita el acceso, ningún actor no-superuser puede modificar superusers
    ni escalarse a sí mismo (ver ``UserSerializer.validate``).

    ``destroy`` (DELETE) está deshabilitado: no hay borrado físico vía API;
    use las acciones ``activate`` / ``deactivate``.
    """

    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    pagination_class = None

    def get_serializer_class(self):
        if self.action == 'list':
            return UserListSerializer
        elif self.action == 'retrieve':
            return UserDetailSerializer
        return UserSerializer

    def get_queryset(self):
        if self.request.user.is_superuser:
            return User.objects.all()
        return User.objects.filter(is_superuser=False)

    def get_serializer_context(self):
        """Garantiza que ``request`` esté en el context para los validadores."""
        ctx = super().get_serializer_context()
        ctx.setdefault('request', self.request)
        return ctx

    # ------------------------------------------------------------------
    # CRUD con auditoría best-effort
    # ------------------------------------------------------------------
    def perform_create(self, serializer):
        with transaction.atomic():
            instance = serializer.save()
            _safe_audit(
                log_create,
                actor=self.request.user,
                entity=instance,
                module="usuarios",
                metadata={"view": "UserViewSet.perform_create"},
            )

    def perform_update(self, serializer):
        before = safe_model_snapshot(self.get_object())
        with transaction.atomic():
            instance = serializer.save()
            _safe_audit(
                log_update,
                actor=self.request.user,
                entity=instance,
                before=before,
                module="usuarios",
                metadata={"view": "UserViewSet.perform_update"},
            )

    def destroy(self, request, *args, **kwargs):
        """Bloquea DELETE físico del modelo User (auditoría e integridad referencial)."""
        raise MethodNotAllowed(
            "DELETE",
            detail=(
                "El borrado físico de usuarios no está permitido. "
                "Use desactivación para preservar trazabilidad."
            ),
        )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    @action(detail=True, methods=['post'])
    def change_password(self, request, pk=None):
        """Cambia el password de un usuario visible para el actor.

        Requiere ``old_password`` (no es un reset administrativo). Auditamos
        el cambio sin loggear ni guardar el password en sí mismo.
        """
        user = self.get_object()
        serializer = ChangePasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        if not user.check_password(serializer.validated_data['old_password']):
            return Response(
                {'error': 'La contraseña actual es incorrecta'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        before = safe_model_snapshot(user)
        with transaction.atomic():
            user.set_password(serializer.validated_data['new_password'])
            user.save(update_fields=['password'])
            _safe_audit(
                log_update,
                actor=request.user,
                entity=user,
                before=before,
                module="usuarios",
                metadata={"view": "UserViewSet.change_password"},
            )
        return Response({'message': 'Contraseña actualizada correctamente'})

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        user = self.get_object()
        before = safe_model_snapshot(user)
        with transaction.atomic():
            user.is_active = True
            user.save(update_fields=['is_active'])
            _safe_audit(
                log_update,
                actor=request.user,
                entity=user,
                before=before,
                module="usuarios",
                metadata={"view": "UserViewSet.activate"},
            )
        return Response({'message': 'Usuario activado correctamente'})

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        user = self.get_object()
        before = safe_model_snapshot(user)
        with transaction.atomic():
            user.is_active = False
            user.save(update_fields=['is_active'])
            _safe_audit(
                log_update,
                actor=request.user,
                entity=user,
                before=before,
                module="usuarios",
                metadata={"view": "UserViewSet.deactivate"},
            )
        return Response({'message': 'Usuario desactivado correctamente'})

    @action(detail=False, methods=['get'])
    def stats(self, request):
        stats = {
            'total_users': User.objects.count(),
            'active_users': User.objects.filter(is_active=True).count(),
            'inactive_users': User.objects.filter(is_active=False).count(),
            'by_role': {},
        }
        for role, _ in User.ROL_CHOICES:
            stats['by_role'][role] = User.objects.filter(rol=role).count()
        return Response(stats)

    @action(detail=False, methods=['post'])
    def bulk_activate(self, request):
        """Activa varios usuarios respetando ``get_queryset``.

        Un staff regular nunca puede alcanzar superusers (que no están en
        su queryset visible).
        """
        affected = self._bulk_set_active(request, value=True)
        return Response({
            'message': f'{affected} usuarios activados',
            'affected': affected,
        })

    @action(detail=False, methods=['post'])
    def bulk_deactivate(self, request):
        affected = self._bulk_set_active(request, value=False)
        return Response({
            'message': f'{affected} usuarios desactivados',
            'affected': affected,
        })

    def _bulk_set_active(self, request, *, value: bool) -> int:
        """Aplica ``is_active=value`` solo a usuarios visibles.

        Auditamos uno por uno (best-effort) para mantener trazabilidad
        granular. Si la lista es vacía o no contiene IDs visibles, devuelve
        ``0`` sin error.
        """
        user_ids = request.data.get('user_ids', []) or []
        if not isinstance(user_ids, list):
            user_ids = []

        visible_qs = self.get_queryset().filter(id__in=user_ids)
        affected_users = list(visible_qs)
        if not affected_users:
            return 0

        with transaction.atomic():
            visible_qs.update(is_active=value)
            for u in affected_users:
                # Refrescamos para que el snapshot ``after`` tenga el nuevo valor
                # sin volver a hitar la DB para los antes-y-después.
                u.is_active = value
                _safe_audit(
                    log_update,
                    actor=request.user,
                    entity=u,
                    before=None,
                    module="usuarios",
                    metadata={
                        "view": (
                            "UserViewSet.bulk_activate"
                            if value
                            else "UserViewSet.bulk_deactivate"
                        ),
                    },
                )
        return len(affected_users)


# ---------------------------------------------------------------------------
# UserProfile
# ---------------------------------------------------------------------------
class UserProfileViewSet(viewsets.ModelViewSet):
    """Gestión de perfiles. DELETE bloqueado (PHI no se borra físicamente)."""

    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get_queryset(self):
        if self.request.user.is_staff:
            return UserProfile.objects.all()
        return UserProfile.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        with transaction.atomic():
            instance = serializer.save(user=self.request.user)
            _safe_audit(
                log_create,
                actor=self.request.user,
                entity=instance,
                module="usuarios",
                metadata={"view": "UserProfileViewSet.perform_create"},
            )

    def perform_update(self, serializer):
        before = safe_model_snapshot(self.get_object())
        with transaction.atomic():
            instance = serializer.save()
            _safe_audit(
                log_update,
                actor=self.request.user,
                entity=instance,
                before=before,
                module="usuarios",
                metadata={"view": "UserProfileViewSet.perform_update"},
            )

    def destroy(self, request, *args, **kwargs):
        """Bloquea DELETE físico de perfiles (contienen PHI relevante)."""
        raise MethodNotAllowed(
            "DELETE",
            detail=(
                "El borrado físico de UserProfile no está permitido. "
                "Edite el perfil o solicite anonimización al administrador."
            ),
        )


# ---------------------------------------------------------------------------
# Auth helpers (logout/me)
# ---------------------------------------------------------------------------
class AuthViewSet(viewsets.ViewSet):
    """Operaciones de autenticación para clientes JWT."""

    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    @action(detail=False, methods=['post'])
    def logout(self, request):
        """Invalida el refresh token del cliente (requiere blacklist habilitado)."""
        try:
            refresh_token = request.data.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({'message': 'Sesión cerrada correctamente'})
        except Exception:
            # ``token_blacklist`` puede no estar instalado o el token puede
            # ser inválido. No exponemos detalles internos.
            return Response(
                {'error': 'Error al cerrar sesión'},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=['get'])
    def me(self, request):
        return Response(UserDetailSerializer(request.user).data)


# ---------------------------------------------------------------------------
# Registro público de pacientes
# ---------------------------------------------------------------------------
class PacienteRegisterView(generics.CreateAPIView):
    """Auto-registro público de pacientes.

    Hardening:
    - El serializer fuerza ``rol='paciente'`` y nunca acepta flags privilegiados.
    - Logs no contienen DNI/email en claro (se usan hashes cortos para
      correlación) y no exponen trazas de DB al cliente.
    - El ``request_id`` (si está disponible vía middleware de auditoría) se
      incluye en cada línea de log para correlación.
    """

    permission_classes = [permissions.AllowAny]
    serializer_class = PacienteRegistrationSerializer

    def create(self, request, *args, **kwargs):
        rid = get_request_id() or "no-request-id"
        # Solo logueamos hashes cortos para correlacionar incidentes sin
        # exponer PII en archivos de log.
        dni_hash = _hash_pii(str(request.data.get('dni', '')))
        email_hash = _hash_pii(str(request.data.get('email', '')))
        logger.info(
            "Registro paciente recibido (rid=%s dni_h=%s email_h=%s)",
            rid, dni_hash, email_hash,
        )

        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            logger.info(
                "Registro paciente OK (rid=%s user_id=%s)", rid, user.id,
            )
            return Response(
                {
                    'message': 'Registro exitoso. Ya puedes iniciar sesión.',
                    'user_id': user.id,
                },
                status=status.HTTP_201_CREATED,
            )

        except serializers.ValidationError as e:
            logger.warning(
                "Registro paciente: validación fallida (rid=%s)", rid,
            )
            return Response(
                {'error': 'Error de validación', 'details': e.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except (ObjectDoesNotExist, ValidationError) as e:
            # Errores conocidos del dominio: no exponer trazas.
            logger.warning(
                "Registro paciente: error de dominio (rid=%s)", rid,
            )
            return Response(
                {'error': 'No se pudo completar el registro.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:  # noqa: BLE001
            # Errores inesperados: log con stack interno, respuesta genérica.
            logger.exception(
                "Registro paciente: error inesperado (rid=%s)", rid,
            )
            response_body = {
                'error': 'Error interno del servidor. Por favor, intenta nuevamente más tarde.',
            }
            if settings.DEBUG:
                response_body['debug_message'] = str(e)
            return Response(
                response_body,
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
