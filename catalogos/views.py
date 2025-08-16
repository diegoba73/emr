from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import CentroFisico, TipoAtencion, AreaInternacion, CamaInternacion
from .serializers import (
    CentroFisicoSerializer, 
    TipoAtencionSerializer, 
    AreaInternacionSerializer, 
    CamaInternacionSerializer
)

# Create your views here.

class CentroFisicoViewSet(viewsets.ModelViewSet):
    queryset = CentroFisico.objects.filter(activo=True)
    serializer_class = CentroFisicoSerializer
    permission_classes = [IsAuthenticated]

class TipoAtencionViewSet(viewsets.ModelViewSet):
    queryset = TipoAtencion.objects.filter(activo=True)
    serializer_class = TipoAtencionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        centro_fisico = self.request.query_params.get('centro_fisico', None)
        if centro_fisico:
            queryset = queryset.filter(centro_fisico__codigo=centro_fisico)
        return queryset

class AreaInternacionViewSet(viewsets.ModelViewSet):
    queryset = AreaInternacion.objects.filter(activo=True)
    serializer_class = AreaInternacionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        centro_fisico = self.request.query_params.get('centro_fisico', None)
        if centro_fisico:
            queryset = queryset.filter(centro_fisico__codigo=centro_fisico)
        return queryset

class CamaInternacionViewSet(viewsets.ModelViewSet):
    queryset = CamaInternacion.objects.filter(activa=True)
    serializer_class = CamaInternacionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        area = self.request.query_params.get('area', None)
        estado = self.request.query_params.get('estado', None)
        
        if area:
            queryset = queryset.filter(area__codigo=area)
        if estado:
            queryset = queryset.filter(estado=estado)
            
        return queryset
