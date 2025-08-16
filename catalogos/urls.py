from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CentroFisicoViewSet, 
    TipoAtencionViewSet, 
    AreaInternacionViewSet, 
    CamaInternacionViewSet
)

router = DefaultRouter()
router.register(r'centros-fisicos', CentroFisicoViewSet)
router.register(r'tipos-atencion', TipoAtencionViewSet)
router.register(r'areas-internacion', AreaInternacionViewSet)
router.register(r'camas-internacion', CamaInternacionViewSet)

urlpatterns = [
    path('', include(router.urls)),
]


