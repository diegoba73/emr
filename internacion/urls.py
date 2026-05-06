from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'sectores', views.SectorViewSet, basename='sector')
router.register(r'camas', views.CamaViewSet, basename='cama')
router.register(r'internaciones', views.InternacionViewSet, basename='internacion')

urlpatterns = [
    path('', include(router.urls)),
]

