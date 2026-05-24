from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import EstudioComplementarioViewSet

router = DefaultRouter()
router.register(r'', EstudioComplementarioViewSet, basename='estudio-complementario')

urlpatterns = [
    path('', include(router.urls)),
]
