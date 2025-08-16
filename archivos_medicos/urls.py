from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ArchivoMedicoViewSet, get_csrf_token

router = DefaultRouter()
router.register(r'archivos', ArchivoMedicoViewSet, basename='archivo-medico')

urlpatterns = [
    path('', include(router.urls)),
    path('csrf-token/', get_csrf_token, name='get-csrf-token'),
]
