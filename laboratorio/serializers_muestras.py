"""
Serializers LIMS Fase B0/B1: catálogos de laboratorio y muestra transaccional.
"""
from __future__ import annotations

from rest_framework import serializers

from laboratorio.models import SolicitudExamen, TipoMuestra
from laboratorio.models_catalog import AreaLaboratorio, EventoMuestra, Muestra, SeccionLaboratorio, TipoContenedor


class AreaLaboratorioSerializer(serializers.ModelSerializer):
    class Meta:
        model = AreaLaboratorio
        fields = ("id", "codigo", "nombre", "descripcion", "activo", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class SeccionLaboratorioSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeccionLaboratorio
        fields = (
            "id",
            "area",
            "codigo",
            "nombre",
            "descripcion",
            "activo",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class TipoContenedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoContenedor
        fields = (
            "id",
            "codigo",
            "nombre",
            "descripcion",
            "color",
            "volumen_ml",
            "aditivo",
            "activo",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class EventoMuestraSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventoMuestra
        fields = (
            "id",
            "accion",
            "estado_anterior",
            "estado_nuevo",
            "actor",
            "fecha",
            "observaciones",
            "metadata",
            "request_id",
            "created_at",
        )
        read_only_fields = fields


class MuestraSerializer(serializers.ModelSerializer):
    """Lectura (estado y vínculos core read-only vía acciones)."""

    eventos = EventoMuestraSerializer(many=True, read_only=True)

    class Meta:
        model = Muestra
        fields = (
            "id",
            "codigo_barra",
            "solicitud",
            "paciente",
            "tipo_muestra",
            "tipo_contenedor",
            "estado",
            "fecha_toma",
            "tomada_por",
            "fecha_recepcion",
            "recibida_por",
            "fecha_rechazo",
            "rechazada_por",
            "motivo_rechazo",
            "ubicacion_actual",
            "fecha_conservacion",
            "fecha_descarte",
            "descartada_por",
            "observaciones",
            "created_at",
            "updated_at",
            "eventos",
        )
        read_only_fields = fields


class MuestraPartialUpdateSerializer(serializers.ModelSerializer):
    """PATCH: solo campos no sensibles; el estado no se modifica aquí."""

    class Meta:
        model = Muestra
        fields = ("tipo_contenedor", "ubicacion_actual", "observaciones")

    def update(self, instance, validated_data):
        if instance.estado in ("DESCARTADA", "CANCELADA", "RECHAZADA"):
            validated_data.pop("tipo_contenedor", None)
        return super().update(instance, validated_data)


class MuestraCreateSerializer(serializers.Serializer):
    solicitud_id = serializers.IntegerField()
    tipo_muestra_id = serializers.IntegerField()
    tipo_contenedor_id = serializers.IntegerField(required=False, allow_null=True)
    codigo_barra = serializers.CharField(required=False, allow_blank=True, default="")
    observaciones = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        try:
            sol = SolicitudExamen.objects.get(pk=attrs["solicitud_id"])
        except SolicitudExamen.DoesNotExist as exc:
            raise serializers.ValidationError({"solicitud_id": "Solicitud inexistente."}) from exc
        try:
            tm = TipoMuestra.objects.get(pk=attrs["tipo_muestra_id"])
        except TipoMuestra.DoesNotExist as exc:
            raise serializers.ValidationError({"tipo_muestra_id": "Tipo de muestra inexistente."}) from exc
        if not tm.activo:
            raise serializers.ValidationError({"tipo_muestra_id": "Tipo de muestra inactivo."})
        tc_id = attrs.get("tipo_contenedor_id")
        if tc_id is not None:
            try:
                tc = TipoContenedor.objects.get(pk=tc_id)
            except TipoContenedor.DoesNotExist as exc:
                raise serializers.ValidationError({"tipo_contenedor_id": "Tipo de contenedor inexistente."}) from exc
            if not tc.activo:
                raise serializers.ValidationError({"tipo_contenedor_id": "Tipo de contenedor inactivo."})
        cb = (attrs.get("codigo_barra") or "").strip()
        if cb and Muestra.objects.filter(codigo_barra=cb).exists():
            raise serializers.ValidationError({"codigo_barra": "Código de barras ya registrado."})
        attrs["_solicitud"] = sol
        return attrs


class MuestraTomarSerializer(serializers.Serializer):
    observaciones = serializers.CharField(required=False, allow_blank=True, default="")


class MuestraRecibirSerializer(serializers.Serializer):
    observaciones = serializers.CharField(required=False, allow_blank=True, default="")
    ubicacion_actual = serializers.CharField(required=False, allow_blank=True, default="")


class MuestraRechazarSerializer(serializers.Serializer):
    motivo_rechazo = serializers.CharField()
    observaciones = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_motivo_rechazo(self, value):
        if not (value or "").strip():
            raise serializers.ValidationError("El motivo de rechazo es obligatorio.")
        return value.strip()


class MuestraConservarSerializer(serializers.Serializer):
    ubicacion_actual = serializers.CharField(required=False, allow_blank=True, default="")
    observaciones = serializers.CharField(required=False, allow_blank=True, default="")


class MuestraCambiarUbicacionSerializer(serializers.Serializer):
    ubicacion = serializers.CharField()
    observaciones = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_ubicacion(self, value):
        if not (value or "").strip():
            raise serializers.ValidationError("La ubicación es obligatoria.")
        return value.strip()


class MuestraDescartarSerializer(serializers.Serializer):
    observaciones = serializers.CharField(required=False, allow_blank=True, default="")


class MuestraCancelarSerializer(serializers.Serializer):
    motivo = serializers.CharField(required=False, allow_blank=True, default="")
    observaciones = serializers.CharField(required=False, allow_blank=True, default="")


class EventoMuestraLookupSerializer(serializers.ModelSerializer):
    """Historial de custodia para consulta por escaneo (sin metadata de auditoría)."""

    class Meta:
        model = EventoMuestra
        fields = (
            "id",
            "accion",
            "estado_anterior",
            "estado_nuevo",
            "actor",
            "fecha",
            "observaciones",
            "created_at",
        )
        read_only_fields = fields


class MuestraLookupSerializer(serializers.ModelSerializer):
    """Respuesta enriquecida para lookup exacto por código de barras."""

    solicitud_numero = serializers.CharField(source="solicitud.numero", read_only=True)
    paciente_nombre = serializers.CharField(source="paciente.nombre_completo", read_only=True)
    paciente_dni = serializers.CharField(source="paciente.dni", read_only=True)
    tipo_muestra_codigo = serializers.CharField(source="tipo_muestra.codigo", read_only=True)
    tipo_muestra_nombre = serializers.CharField(source="tipo_muestra.nombre", read_only=True)
    eventos = EventoMuestraLookupSerializer(many=True, read_only=True)

    class Meta:
        model = Muestra
        fields = (
            "id",
            "codigo_barra",
            "solicitud",
            "solicitud_numero",
            "paciente",
            "paciente_nombre",
            "paciente_dni",
            "tipo_muestra",
            "tipo_muestra_codigo",
            "tipo_muestra_nombre",
            "tipo_contenedor",
            "estado",
            "fecha_toma",
            "fecha_recepcion",
            "ubicacion_actual",
            "observaciones",
            "created_at",
            "updated_at",
            "eventos",
        )
        read_only_fields = fields


class MuestraRecibirPorCodigoSerializer(serializers.Serializer):
    codigo_barra = serializers.CharField()
    ubicacion_actual = serializers.CharField(required=False, allow_blank=True, default="")
    observaciones = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_codigo_barra(self, value):
        cb = (value or "").strip()
        if not cb:
            raise serializers.ValidationError("El código de barras es obligatorio.")
        return cb


class MuestraTomarPorCodigoSerializer(serializers.Serializer):
    codigo_barra = serializers.CharField()
    observaciones = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_codigo_barra(self, value):
        cb = (value or "").strip()
        if not cb:
            raise serializers.ValidationError("El código de barras es obligatorio.")
        return cb
