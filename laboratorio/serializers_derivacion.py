"""Serializer LaboratorioDerivacion."""
from rest_framework import serializers

from laboratorio.models_derivacion import LaboratorioDerivacion


class LaboratorioDerivacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LaboratorioDerivacion
        fields = [
            "id",
            "codigo",
            "nombre",
            "ciudad",
            "acepta_sangre",
            "acepta_orina",
            "acepta_cultivo",
            "acepta_cualquier",
            "activo",
        ]
