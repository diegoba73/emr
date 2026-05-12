"""Rutas mínimas de gestión de usuarios (solo ``UserViewSet``).

No incluye JWT, registro público, perfiles ni ``AuthViewSet`` para evitar
duplicar semántica con ``/api/auth/*``.
"""
from rest_framework.routers import DefaultRouter

from .views import UserViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user-management')

urlpatterns = router.urls
