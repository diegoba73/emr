"""Serializers para la app ``pacientes``.

Mantiene a ``Paciente`` como fuente de verdad de los datos personales del
paciente. No mueve campos hacia ``User`` ni hacia ``UserProfile``.
"""
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from catalogos.models import DiagnosticoCIE10

from .models import ObraSocial, Paciente, PacienteAfiliacion, ProblemaClinico
from .texto import normalizar_texto_paciente
from .afiliaciones import sync_principal_desde_paciente_fields
from .obras_sociales import codigo_obra_social, resolve_obra_social
from .validacion_identidad import (
    dni_dudoso,
    mensaje_dni_dudoso,
    mensaje_nombre_invalido,
    nombre_o_apellido_valido,
)

_DNI_UNIQUE_MSG = (
    "Ya existe un paciente con este DNI. Usá la ficha existente en lugar de crear otra."
)


def _normalize_name(value):
    """Normaliza un nombre/apellido: ``strip`` + mayúsculas. Tolera ``None``."""
    return normalizar_texto_paciente(value)


class ObraSocialSerializer(serializers.ModelSerializer):
    class Meta:
        model = ObraSocial
        fields = ['id', 'codigo', 'nombre', 'activo']
        read_only_fields = fields


class PacienteAfiliacionSerializer(serializers.ModelSerializer):
    obra_social = serializers.CharField(required=False, allow_blank=True)
    obra_social_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = PacienteAfiliacion
        fields = [
            "id",
            "obra_social",
            "obra_social_id",
            "numero_afiliado",
            "plan",
            "es_principal",
            "activo",
            "creado_en",
            "actualizado_en",
        ]
        read_only_fields = ["id", "creado_en", "actualizado_en"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        os = instance.obra_social
        data['obra_social'] = codigo_obra_social(os) or None
        data['obra_social_id'] = os.pk if os else None
        data['obra_social_nombre'] = (os.nombre if os else None)
        return data

    def validate_numero_afiliado(self, value):
        return normalizar_texto_paciente(value) or ""

    def validate_plan(self, value):
        return normalizar_texto_paciente(value) or ""

    def validate(self, attrs):
        attrs = super().validate(attrs)
        raw_id = attrs.pop('obra_social_id', serializers.empty)
        raw_code = attrs.pop('obra_social', serializers.empty)
        if raw_id is serializers.empty and raw_code is serializers.empty:
            if self.instance is None:
                raise serializers.ValidationError(
                    {'obra_social': 'La obra social es obligatoria.'}
                )
            return attrs
        candidate = raw_id if raw_id is not serializers.empty else raw_code
        os_obj = resolve_obra_social(candidate)
        if os_obj is None:
            raise serializers.ValidationError(
                {'obra_social': 'Obra social inválida o inactiva.'}
            )
        attrs['obra_social'] = os_obj
        return attrs


class ProblemaClinicoSerializer(serializers.ModelSerializer):
    diagnostico_cie_id = serializers.PrimaryKeyRelatedField(
        source="diagnostico_cie",
        queryset=DiagnosticoCIE10.objects.all(),
        allow_null=True,
        required=False,
    )
    diagnostico_cie_codigo = serializers.CharField(
        source="diagnostico_cie.codigo", read_only=True, allow_null=True
    )
    diagnostico_cie_descripcion = serializers.CharField(
        source="diagnostico_cie.descripcion", read_only=True, allow_null=True
    )
    display = serializers.SerializerMethodField()

    class Meta:
        model = ProblemaClinico
        fields = [
            "id",
            "texto",
            "diagnostico_cie_id",
            "diagnostico_cie_codigo",
            "diagnostico_cie_descripcion",
            "display",
            "estado",
            "es_principal",
            "notas",
            "creado_en",
            "actualizado_en",
            "resuelto_en",
        ]
        read_only_fields = [
            "id",
            "diagnostico_cie_codigo",
            "diagnostico_cie_descripcion",
            "display",
            "creado_en",
            "actualizado_en",
            "resuelto_en",
        ]

    def get_display(self, obj):
        return obj.display_texto()

    def validate_texto(self, value):
        text = " ".join((value or "").split()).strip()
        if not text:
            raise serializers.ValidationError("El diagnóstico / problema es obligatorio.")
        return text

    def validate_estado(self, value):
        if value and value not in {
            ProblemaClinico.ESTADO_ACTIVO,
            ProblemaClinico.ESTADO_RESUELTO,
        }:
            raise serializers.ValidationError("Estado inválido.")
        return value


class PacienteLightSerializer(serializers.ModelSerializer):
    """Serializer ligero para listados, búsquedas y selectores.

    Excluye campos pesados (antecedentes, observaciones) e incluye
    ``nombre_completo`` para que la UI no necesite armar la cadena a mano.
    """

    nombre_completo = serializers.ReadOnlyField()
    edad = serializers.ReadOnlyField()
    afiliaciones = PacienteAfiliacionSerializer(many=True, read_only=True)
    obra_social = serializers.SerializerMethodField()
    obra_social_id = serializers.SerializerMethodField()

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
            "direccion",
            "obra_social",
            "obra_social_id",
            "numero_afiliado",
            "plan_obra_social",
            "afiliaciones",
        ]
        read_only_fields = fields

    def get_obra_social(self, obj):
        return codigo_obra_social(obj.obra_social) or None

    def get_obra_social_id(self, obj):
        return obj.obra_social_id


class PacienteSerializer(serializers.ModelSerializer):
    """Serializer completo del modelo ``Paciente``.

    Normaliza datos demográficos (``strip`` + mayúsculas). En **creación**
    exige identidad mínima: ``dni``, ``nombre``, ``apellido`` y
    ``fecha_nacimiento``. En actualización no obliga a completar campos legacy
    vacíos. Expone ``nombre_completo`` y ``edad`` como campos derivados de
    solo lectura.
    """

    nombre_completo = serializers.ReadOnlyField()
    edad = serializers.ReadOnlyField(help_text="Edad calculada automáticamente")
    creado_por = serializers.SerializerMethodField()
    modificado_por = serializers.SerializerMethodField()
    afiliaciones = PacienteAfiliacionSerializer(many=True, read_only=True)
    # Escritura: código (`obra_social`) o PK (`obra_social_id`). Lectura: código.
    obra_social = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    obra_social_id = serializers.IntegerField(required=False, allow_null=True)

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
            "estado_civil",
            "telefono",
            "email",
            "direccion",
            "obra_social",
            "obra_social_id",
            "numero_afiliado",
            "plan_obra_social",
            "afiliaciones",
            "familiar_nombre",
            "familiar_telefono",
            "observaciones",
            "antecedentes_personales",
            "antecedentes_familiares",
            "fecha_registro",
            "ultima_actualizacion",
            "creado_por",
            "modificado_por",
        ]
        read_only_fields = [
            "fecha_registro",
            "ultima_actualizacion",
            "edad",
            "nombre_completo",
            "creado_por",
            "modificado_por",
            "afiliaciones",
        ]
        extra_kwargs = {
            "dni": {
                "validators": [
                    UniqueValidator(
                        queryset=Paciente.objects.all(),
                        message=_DNI_UNIQUE_MSG,
                    )
                ],
                "error_messages": {"unique": _DNI_UNIQUE_MSG},
            }
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        os = instance.obra_social
        data['obra_social'] = codigo_obra_social(os) or None
        data['obra_social_id'] = os.pk if os else None
        data['obra_social_nombre'] = os.nombre if os else None
        return data


    def get_creado_por(self, obj):
        if obj.creado_por_id is None:
            return None
        return obj.creado_por.username

    def get_modificado_por(self, obj):
        if obj.modificado_por_id is None:
            return None
        return obj.modificado_por.username

    def validate_nombre(self, value):
        normalized = _normalize_name(value)
        if normalized is None or (isinstance(normalized, str) and not normalized.strip()):
            return normalized
        if not nombre_o_apellido_valido(normalized):
            raise serializers.ValidationError(mensaje_nombre_invalido("nombre"))
        return normalized

    def validate_apellido(self, value):
        normalized = _normalize_name(value)
        if normalized is None or (isinstance(normalized, str) and not normalized.strip()):
            return normalized
        if not nombre_o_apellido_valido(normalized):
            raise serializers.ValidationError(mensaje_nombre_invalido("apellido"))
        return normalized

    def validate_direccion(self, value):
        return normalizar_texto_paciente(value)

    def validate_numero_afiliado(self, value):
        return normalizar_texto_paciente(value)

    def validate_dni(self, value):
        # Rechaza vacío y placeholders obvios (11111, todos iguales, muy corto).
        # No impone un único formato (DNI/pasaporte) para no romper docs reales.
        # Unicidad: UniqueValidator (mensaje ES).
        if value is None:
            raise serializers.ValidationError("El DNI es obligatorio.")
        text = str(value).strip()
        if not text:
            raise serializers.ValidationError("El DNI no puede estar vacío.")
        if dni_dudoso(text):
            raise serializers.ValidationError(mensaje_dni_dudoso())
        return text

    def validate(self, attrs):
        attrs = super().validate(attrs)
        raw_id = attrs.pop('obra_social_id', serializers.empty)
        raw_code = attrs.pop('obra_social', serializers.empty)
        os_provided = raw_id is not serializers.empty or raw_code is not serializers.empty

        if os_provided:
            candidate = (
                raw_id
                if raw_id is not serializers.empty and raw_id is not None
                else raw_code
            )
            if candidate is None or (
                isinstance(candidate, str) and not str(candidate).strip()
            ):
                if self.instance is None:
                    raise serializers.ValidationError(
                        {'obra_social': 'La obra social es obligatoria al crear un paciente.'}
                    )
                attrs['obra_social'] = None
            else:
                os_obj = resolve_obra_social(candidate)
                if os_obj is None:
                    raise serializers.ValidationError(
                        {'obra_social': 'Obra social inválida o inactiva.'}
                    )
                attrs['obra_social'] = os_obj

        if self.instance is not None:
            return attrs

        errors = {}
        nombre = attrs.get("nombre")
        if nombre is None or (isinstance(nombre, str) and not nombre.strip()):
            errors["nombre"] = "El nombre es obligatorio al crear un paciente."
        elif not nombre_o_apellido_valido(nombre):
            errors["nombre"] = mensaje_nombre_invalido("nombre")

        apellido = attrs.get("apellido")
        if apellido is None or (isinstance(apellido, str) and not apellido.strip()):
            errors["apellido"] = "El apellido es obligatorio al crear un paciente."
        elif not nombre_o_apellido_valido(apellido):
            errors["apellido"] = mensaje_nombre_invalido("apellido")

        if attrs.get("fecha_nacimiento") is None:
            errors["fecha_nacimiento"] = (
                "La fecha de nacimiento es obligatoria al crear un paciente."
            )

        if not os_provided or not attrs.get('obra_social'):
            errors["obra_social"] = (
                "La obra social es obligatoria al crear un paciente."
            )

        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def create(self, validated_data):
        instance = super().create(validated_data)
        sync_principal_desde_paciente_fields(instance)
        return instance

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        if (
            "obra_social" in validated_data
            or "numero_afiliado" in validated_data
            or "plan_obra_social" in validated_data
        ):
            sync_principal_desde_paciente_fields(instance)
        return instance