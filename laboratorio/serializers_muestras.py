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
            "lugar_extraccion",
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
        fields = ("tipo_contenedor", "ubicacion_actual", "lugar_extraccion", "observaciones")

    def validate_lugar_extraccion(self, value):
        text = " ".join((value or "").split()).strip()
        if not text:
            return None
        return text.upper()

    def update(self, instance, validated_data):
        """
        Una sola transaction + select_for_update:
        - no UPDATE parcial de lugar previo al save;
        - save solo con update_fields (evita stale overwrite de snapshot);
        - rollback completo si falla cualquier parte.
        """
        from django.db import transaction
        from django.utils import timezone

        with transaction.atomic():
            locked = Muestra.objects.select_for_update().get(pk=instance.pk)

            data = dict(validated_data)
            if locked.estado in ("DESCARTADA", "CANCELADA", "RECHAZADA"):
                data.pop("tipo_contenedor", None)

            lugar_nuevo = data.pop("lugar_extraccion", serializers.empty)
            update_fields: list[str] = []

            if lugar_nuevo is not serializers.empty and lugar_nuevo is not None:
                if locked.estado == "PENDIENTE_TOMA" or locked.fecha_toma is None:
                    raise serializers.ValidationError(
                        {
                            "lugar_extraccion": (
                                "El lugar de extracción se registra en la toma; "
                                "no puede anticiparse mientras la muestra está pendiente."
                            )
                        }
                    )
                if (locked.lugar_extraccion or "").strip():
                    raise serializers.ValidationError(
                        {
                            "lugar_extraccion": (
                                "El lugar de extracción ya está registrado y no puede modificarse."
                            )
                        }
                    )
                locked.lugar_extraccion = lugar_nuevo
                update_fields.append("lugar_extraccion")

            for attr, value in data.items():
                setattr(locked, attr, value)
                update_fields.append(attr)

            if update_fields:
                if hasattr(locked, "updated_at"):
                    locked.updated_at = timezone.now()
                    update_fields.append("updated_at")
                locked.save(update_fields=update_fields)

            # Mantener la instancia del ViewSet alineada con la fila bloqueada.
            instance.refresh_from_db()
            return instance


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
    # Opcional para compatibilidad con clientes que envían {}. La UI nueva lo solicita.
    lugar_extraccion = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_lugar_extraccion(self, value):
        return " ".join((value or "").split()).strip()


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
            "lugar_extraccion",
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
    lugar_extraccion = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_codigo_barra(self, value):
        cb = (value or "").strip()
        if not cb:
            raise serializers.ValidationError("El código de barras es obligatorio.")
        return cb

    def validate_lugar_extraccion(self, value):
        return " ".join((value or "").split()).strip()
