"""Serializers para la app ``pacientes``.

Mantiene a ``Paciente`` como fuente de verdad de los datos personales del
paciente. No mueve campos hacia ``User`` ni hacia ``UserProfile``.
"""
from rest_framework import serializers

from .models import Paciente


def _normalize_name(value):
    """Normaliza un nombre/apellido: ``strip`` + ``title``. Tolera ``None``."""
    if value is None:
        return value
    text = str(value).strip()
    if not text:
        return ""
    return text.title()


class PacienteLightSerializer(serializers.ModelSerializer):
    """Serializer ligero para listados, búsquedas y selectores.

    Excluye campos pesados (antecedentes, observaciones) e incluye
    ``nombre_completo`` para que la UI no necesite armar la cadena a mano.
    """

    nombre_completo = serializers.ReadOnlyField()
    edad = serializers.ReadOnlyField()

    class Meta:
        model = Paciente
        fields = [
            "id",
            "nombre",
            "apellido",
            "nombre_completo",
            "dni",
            "fecha_nacimiento",
            "edad",
            "sexo",
            "telefono",
            "email",
        ]
        read_only_fields = fields


class PacienteSerializer(serializers.ModelSerializer):
    """Serializer completo del modelo ``Paciente``.

    Normaliza ``nombre`` y ``apellido`` (``strip`` + ``title``) tolerando
    ``None``. Expone ``nombre_completo`` y ``edad`` como campos derivados de
    solo lectura.
    """

    nombre_completo = serializers.ReadOnlyField()
    edad = serializers.ReadOnlyField(help_text="Edad calculada automáticamente")

    class Meta:
        model = Paciente
        fields = [
            "id",
            "user",
            "nombre",
            "apellido",
            "nombre_completo",
            "dni",
            "fecha_nacimiento",
            "edad",
            "sexo",
            "telefono",
            "email",
            "direccion",
            "obra_social",
            "numero_afiliado",
            "observaciones",
            "antecedentes_personales",
            "antecedentes_familiares",
            "fecha_registro",
            "ultima_actualizacion",
        ]
        read_only_fields = [
            "fecha_registro",
            "ultima_actualizacion",
            "edad",
            "nombre_completo",
        ]

    def validate_nombre(self, value):
        return _normalize_name(value)

    def validate_apellido(self, value):
        return _normalize_name(value)

    def validate_dni(self, value):
        # Validación mínima y conservadora: rechaza cadenas vacías o solo
        # whitespace. No impone formato específico (DNI/pasaporte/cuit) para no
        # romper datos preexistentes.
        if value is None:
            raise serializers.ValidationError("El DNI es obligatorio.")
        text = str(value).strip()
        if not text:
            raise serializers.ValidationError("El DNI no puede estar vacío.")
        return text
