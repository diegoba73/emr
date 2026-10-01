import hashlib
from django.utils import timezone
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission
from .models import SesionMovil
from .roles import ROLES_MOVIL


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


class AutenticacionMovil(BaseAuthentication):
    def authenticate_header(self, request):
        return 'Bearer'

    def authenticate(self, request):
        parts = get_authorization_header(request).split()
        if not parts:
            return None
        if len(parts) != 2 or parts[0].lower() != b'bearer':
            raise AuthenticationFailed('Iniciá sesión nuevamente.')
        try:
            sesion = SesionMovil.objects.select_related('user').get(
                token_hash=token_hash(parts[1].decode()), revocada=False, expira_en__gt=timezone.now())
        except (SesionMovil.DoesNotExist, UnicodeDecodeError):
            raise AuthenticationFailed('La sesión venció. Iniciá sesión nuevamente.') from None
        if not sesion.user.is_active:
            raise AuthenticationFailed('La sesión no está disponible.')
        return sesion.user, sesion


class RolMovil(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and str(request.user.rol).lower() in ROLES_MOVIL
        )
