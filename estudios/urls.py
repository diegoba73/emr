from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import EstudioComplementarioViewSet, TipoEstudioComplementarioViewSet

router = DefaultRouter()
router.register(r'tipos', TipoEstudioComplementarioViewSet, basename='tipo-estudio-complementario')
router.register(r'', EstudioComplementarioViewSet, basename='estudio-complementario')

urlpatterns = [
    path('', include(router.urls)),
]
