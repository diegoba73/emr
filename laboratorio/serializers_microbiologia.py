"""
Serializers de microbiología base — LIMS Fase B3.1.

El campo ``estado`` de ``EstudioMicrobiologia`` es read-only en el serializer
de actualización: las transiciones van por acciones POST dedicadas
(``iniciar`` / ``cancelar``) o por servicios al crear siembras / lecturas.
"""
from __future__ import annotations

from rest_framework import serializers

from laboratorio.models import Muestra, SolicitudExamen
from laboratorio.models_microbiologia import (
    AisladoMicrobiologico,
    Antibiograma,
    Antibiotico,
    EstudioMicrobiologia,
    IdentificacionMicroorganismo,
    InformeMicrobiologia,
    LecturaCultivo,
    MedioCultivo,
    Microorganismo,
    ResultadoAntibiotico,
    SiembraMicrobiologia,
)


# ---------------------------------------------------------------------------
# Medios de cultivo (catálogo)
# ---------------------------------------------------------------------------


class MedioCultivoSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedioCultivo
        fields = (
            "id",
            "codigo",
            "nombre",
            "tipo",
            "descripcion",
            "activo",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


# ---------------------------------------------------------------------------
# Estudio
# ---------------------------------------------------------------------------


class EstudioMicrobiologiaSerializer(serializers.ModelSerializer):
    """Lectura: incluye estado y campos derivados; el estado es read-only."""

    class Meta:
        model = EstudioMicrobiologia
        fields = (
            "id",
            "numero",
            "solicitud",
            "muestra",
            "paciente",
            "tipo_estudio",
            "estado",
            "observaciones",
            "fecha_inicio",
            "fecha_cierre",
            "responsable",
            "cancelado_por",
            "fecha_cancelacion",
            "motivo_cancelacion",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class EstudioMicrobiologiaCreateSerializer(serializers.Serializer):
    solicitud_id = serializers.IntegerField()
    muestra_id = serializers.IntegerField()
    tipo_estudio = serializers.ChoiceField(
        choices=[c[0] for c in EstudioMicrobiologia.TIPO_ESTUDIO_CHOICES],
        required=False,
        default="CULTIVO_RUTINA",
    )
    observaciones = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        try:
            sol = SolicitudExamen.objects.get(pk=attrs["solicitud_id"])
        except SolicitudExamen.DoesNotExist as exc:
            raise serializers.ValidationError({"solicitud_id": "Solicitud inexistente."}) from exc
        try:
            muestra = Muestra.objects.get(pk=attrs["muestra_id"])
        except Muestra.DoesNotExist as exc:
            raise serializers.ValidationError({"muestra_id": "Muestra inexistente."}) from exc
        if muestra.solicitud_id != sol.pk:
            raise serializers.ValidationError(
                {"muestra_id": "La muestra no pertenece a la solicitud indicada."}
            )
        attrs["_solicitud"] = sol
        attrs["_muestra"] = muestra
        return attrs


class EstudioMicrobiologiaPartialUpdateSerializer(serializers.ModelSerializer):
    """PATCH: campos no sensibles. ``estado`` se ignora; transiciones vía acciones."""

    class Meta:
        model = EstudioMicrobiologia
        fields = ("tipo_estudio", "observaciones")


class EstudioCancelarSerializer(serializers.Serializer):
    motivo = serializers.CharField()

    def validate_motivo(self, value):
        if not (value or "").strip():
            raise serializers.ValidationError("El motivo de cancelación es obligatorio.")
        return value.strip()


class EstudioIniciarSerializer(serializers.Serializer):
    pass


class EstudioMarcarInformadoSerializer(serializers.Serializer):
    pass


# ---------------------------------------------------------------------------
# Siembras
# ---------------------------------------------------------------------------


class SiembraMicrobiologiaSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiembraMicrobiologia
        fields = (
            "id",
            "estudio",
            "muestra",
            "medio",
            "fecha_siembra",
            "sembrado_por",
            "condicion_incubacion",
            "temperatura_c",
            "atmosfera",
            "observaciones",
            "estado",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class SiembraMicrobiologiaCreateSerializer(serializers.Serializer):
    estudio_id = serializers.IntegerField()
    medio_id = serializers.IntegerField()
    fecha_siembra = serializers.DateTimeField(required=False, allow_null=True)
    condicion_incubacion = serializers.CharField(required=False, allow_blank=True, default="")
    temperatura_c = serializers.DecimalField(
        required=False, allow_null=True, max_digits=5, decimal_places=2
    )
    atmosfera = serializers.CharField(required=False, allow_blank=True, default="")
    observaciones = serializers.CharField(required=False, allow_blank=True, default="")


class SiembraMicrobiologiaPartialUpdateSerializer(serializers.ModelSerializer):
    """PATCH: solo campos descriptivos; el estado no se modifica aquí."""

    class Meta:
        model = SiembraMicrobiologia
        fields = ("condicion_incubacion", "temperatura_c", "atmosfera", "observaciones")


# ---------------------------------------------------------------------------
# Lecturas
# ---------------------------------------------------------------------------


class LecturaCultivoSerializer(serializers.ModelSerializer):
    class Meta:
        model = LecturaCultivo
        fields = (
            "id",
            "siembra",
            "estudio",
            "fecha_lectura",
            "leido_por",
            "horas_incubacion",
            "crecimiento",
            "descripcion_colonias",
            "tincion_gram",
            "observaciones",
            "es_preliminar",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class LecturaCultivoCreateSerializer(serializers.Serializer):
    siembra_id = serializers.IntegerField()
    fecha_lectura = serializers.DateTimeField(required=False, allow_null=True)
    horas_incubacion = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    crecimiento = serializers.ChoiceField(
        choices=[c[0] for c in LecturaCultivo.CRECIMIENTO_CHOICES],
        required=False,
        default="PENDIENTE",
    )
    descripcion_colonias = serializers.CharField(required=False, allow_blank=True, default="")
    tincion_gram = serializers.CharField(required=False, allow_blank=True, default="")
    observaciones = serializers.CharField(required=False, allow_blank=True, default="")
    es_preliminar = serializers.BooleanField(required=False, default=False)


class LecturaCultivoPartialUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LecturaCultivo
        fields = (
            "horas_incubacion",
            "crecimiento",
            "descripcion_colonias",
            "tincion_gram",
            "observaciones",
            "es_preliminar",
        )


# ---------------------------------------------------------------------------
# B3.2 — Microorganismos, aislados, identificaciones
# ---------------------------------------------------------------------------


class MicroorganismoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Microorganismo
        fields = (
            "id",
            "codigo",
            "nombre",
            "genero",
            "especie",
            "grupo",
            "descripcion",
            "activo",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class AisladoMicrobiologicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AisladoMicrobiologico
        fields = (
            "id",
            "estudio",
            "lectura_origen",
            "microorganismo",
            "estado",
            "descripcion",
            "cantidad",
            "significancia",
            "requiere_antibiograma",
            "observaciones",
            "creado_por",
            "descartado_por",
            "fecha_descarte",
            "motivo_descarte",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class AisladoMicrobiologicoCreateSerializer(serializers.Serializer):
    estudio_id = serializers.IntegerField()
    lectura_id = serializers.IntegerField()
    microorganismo_id = serializers.IntegerField(required=False, allow_null=True)
    descripcion = serializers.CharField(required=False, allow_blank=True, default="")
    cantidad = serializers.CharField(required=False, allow_blank=True, default="")
    significancia = serializers.ChoiceField(
        choices=[c[0] for c in AisladoMicrobiologico.SIGNIFICANCIA_CHOICES],
        required=False,
        default="NO_DEFINIDA",
    )
    requiere_antibiograma = serializers.BooleanField(required=False, default=False)
    observaciones = serializers.CharField(required=False, allow_blank=True, default="")


class AisladoMicrobiologicoPartialUpdateSerializer(serializers.ModelSerializer):
    """PATCH limitado: estado y microorganismo no se editan vía PATCH.

    Estado solo cambia por servicio (``descartar``) o por crear identificación.
    Microorganismo se asigna al identificar formalmente.
    """

    class Meta:
        model = AisladoMicrobiologico
        fields = (
            "descripcion",
            "cantidad",
            "significancia",
            "requiere_antibiograma",
            "observaciones",
        )


class AisladoDescartarSerializer(serializers.Serializer):
    motivo = serializers.CharField()

    def validate_motivo(self, value):
        if not (value or "").strip():
            raise serializers.ValidationError("El motivo de descarte es obligatorio.")
        return value.strip()


class IdentificacionMicroorganismoSerializer(serializers.ModelSerializer):
    class Meta:
        model = IdentificacionMicroorganismo
        fields = (
            "id",
            "aislado",
            "microorganismo",
            "metodo",
            "resultado",
            "confianza",
            "fecha",
            "realizado_por",
            "observaciones",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class IdentificacionMicroorganismoCreateSerializer(serializers.Serializer):
    aislado_id = serializers.IntegerField()
    microorganismo_id = serializers.IntegerField()
    metodo = serializers.CharField(required=False, allow_blank=True, default="")
    resultado = serializers.CharField(required=False, allow_blank=True, default="")
    confianza = serializers.DecimalField(
        required=False, allow_null=True, max_digits=5, decimal_places=2
    )
    fecha = serializers.DateTimeField(required=False, allow_null=True)
    observaciones = serializers.CharField(required=False, allow_blank=True, default="")


# ---------------------------------------------------------------------------
# B3.3 — Antibiograma microbiológico
# ---------------------------------------------------------------------------


class AntibioticoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Antibiotico
        fields = (
            "id",
            "codigo",
            "nombre",
            "familia",
            "descripcion",
            "activo",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class AntibiogramaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Antibiograma
        fields = (
            "id",
            "aislado",
            "estado",
            "metodo",
            "fecha_inicio",
            "fecha_resultado",
            "realizado_por",
            "cancelado_por",
            "fecha_cancelacion",
            "motivo_cancelacion",
            "observaciones",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class AntibiogramaCreateSerializer(serializers.Serializer):
    aislado_id = serializers.IntegerField()
    metodo = serializers.CharField(required=False, allow_blank=True, default="")
    fecha_inicio = serializers.DateTimeField(required=False, allow_null=True)
    observaciones = serializers.CharField(required=False, allow_blank=True, default="")


class AntibiogramaPartialUpdateSerializer(serializers.ModelSerializer):
    """PATCH limitado: estado, fechas y motivo se mueven sólo por servicio.

    Editar campos descriptivos (`metodo`, `observaciones`) solo si el
    antibiograma no está COMPLETO ni CANCELADO.
    """

    class Meta:
        model = Antibiograma
        fields = ("metodo", "observaciones")

    def update(self, instance, validated_data):
        if instance.estado in Antibiograma.ESTADOS_BLOQUEAN_CARGA:
            raise serializers.ValidationError(
                {"detail": "No se puede modificar un antibiograma COMPLETO o CANCELADO."}
            )
        return super().update(instance, validated_data)


class AntibiogramaCancelarSerializer(serializers.Serializer):
    motivo = serializers.CharField()

    def validate_motivo(self, value):
        if not (value or "").strip():
            raise serializers.ValidationError("El motivo de cancelación es obligatorio.")
        return value.strip()


class AntibiogramaCompletarSerializer(serializers.Serializer):
    pass


class ResultadoAntibioticoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResultadoAntibiotico
        fields = (
            "id",
            "antibiograma",
            "antibiotico",
            "halo_mm",
            "mic",
            "interpretacion",
            "observaciones",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ResultadoAntibioticoCreateSerializer(serializers.Serializer):
    antibiograma_id = serializers.IntegerField()
    antibiotico_id = serializers.IntegerField()
    halo_mm = serializers.DecimalField(
        required=False, allow_null=True, max_digits=6, decimal_places=2
    )
    mic = serializers.CharField(required=False, allow_blank=True, default="")
    interpretacion = serializers.ChoiceField(
        choices=[c[0] for c in ResultadoAntibiotico.INTERPRETACION_CHOICES]
    )
    observaciones = serializers.CharField(required=False, allow_blank=True, default="")


class ResultadoAntibioticoPartialUpdateSerializer(serializers.Serializer):
    """PATCH controlado a través del servicio (sin tocar antibiograma/antibiotico)."""

    halo_mm = serializers.DecimalField(
        required=False, allow_null=True, max_digits=6, decimal_places=2
    )
    mic = serializers.CharField(required=False, allow_blank=True)
    interpretacion = serializers.ChoiceField(
        required=False,
        choices=[c[0] for c in ResultadoAntibiotico.INTERPRETACION_CHOICES],
    )
    observaciones = serializers.CharField(required=False, allow_blank=True)


# ---------------------------------------------------------------------------
# B3.4 — Informes microbiológicos
# ---------------------------------------------------------------------------


class InformeMicrobiologiaSerializer(serializers.ModelSerializer):
    class Meta:
        model = InformeMicrobiologia
        fields = (
            "id",
            "estudio",
            "tipo",
            "estado",
            "texto",
            "version",
            "emitido_por",
            "fecha_emision",
            "validado_por",
            "fecha_validacion",
            "reemplaza_a",
            "observaciones",
            "motivo_anulacion",
            "anulado_por",
            "fecha_anulacion",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class InformeMicrobiologiaCreateSerializer(serializers.Serializer):
    estudio_id = serializers.IntegerField()
    tipo = serializers.ChoiceField(choices=[c[0] for c in InformeMicrobiologia.TIPO_CHOICES])
    texto = serializers.CharField(required=False, allow_blank=True, default="")
    observaciones = serializers.CharField(required=False, allow_blank=True, default="")
    reemplaza_a_id = serializers.IntegerField(required=False, allow_null=True)


class InformeMicrobiologiaPartialUpdateSerializer(serializers.Serializer):
    texto = serializers.CharField(required=False, allow_blank=True)
    observaciones = serializers.CharField(required=False, allow_blank=True)
    version = serializers.IntegerField(required=False, min_value=1)


class InformeAnularSerializer(serializers.Serializer):
    motivo = serializers.CharField()

    def validate_motivo(self, value):
        if not (value or "").strip():
            raise serializers.ValidationError("El motivo de anulación es obligatorio.")
        return value.strip()


class InformeValidarSerializer(serializers.Serializer):
    pass
