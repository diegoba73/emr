from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ArchivoMedicoViewSet, tipos_archivo_publicos

router = DefaultRouter()
router.register(r'archivos', ArchivoMedicoViewSet, basename='archivo-medico')

urlpatterns = [
    path('', include(router.urls)),
    path('tipos_disponibles/', tipos_archivo_publicos, name='tipos_archivo_publicos'),
]
