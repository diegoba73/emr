from rest_framework import serializers
from .models import CentroFisico, TipoAtencion, AreaInternacion, CamaInternacion

class CentroFisicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CentroFisico
        fields = '__all__'

class TipoAtencionSerializer(serializers.ModelSerializer):
    centro_fisico = CentroFisicoSerializer(read_only=True)
    centro_fisico_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = TipoAtencion
        fields = '__all__'

class AreaInternacionSerializer(serializers.ModelSerializer):
    centro_fisico = CentroFisicoSerializer(read_only=True)
    centro_fisico_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = AreaInternacion
        fields = '__all__'

class CamaInternacionSerializer(serializers.ModelSerializer):
    area = AreaInternacionSerializer(read_only=True)
    area_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = CamaInternacion
        fields = '__all__'


