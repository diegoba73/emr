"""
Serializers de microbiología base — LIMS Fase B3.1.

El campo ``estado`` de ``EstudioMicrobiologia`` es read-only en el serializer
de actualización: las transiciones van por acciones POST dedicadas
(``iniciar`` / ``cancelar``) o por servicios al crear siembras / lecturas.
"""
from __future__ import annotations

from rest_framework import serializers

from laboratorio.display_names import format_apellido_nombre, format_medico_display
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
    TipoCultivoMicrobiologia,
    TipoMuestraMicrobiologia,
)


# ---------------------------------------------------------------------------
# Catálogos cultivo / muestra micro
# ---------------------------------------------------------------------------


class TipoCultivoMicrobiologiaSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoCultivoMicrobiologia
        fields = (
            "id",
            "codigo",
            "nombre",
            "descripcion",
            "orden",
            "activo",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class TipoMuestraMicrobiologiaSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoMuestraMicrobiologia
        fields = (
            "id",
            "codigo",
            "nombre",
            "descripcion",
            "orden",
            "activo",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


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

    paciente_nombre = serializers.SerializerMethodField()
    paciente_dni = serializers.SerializerMethodField()
    paciente_email = serializers.SerializerMethodField()
    paciente_telefono = serializers.SerializerMethodField()
    medico_display = serializers.SerializerMethodField()
    medico_email = serializers.SerializerMethodField()
    medico_telefono = serializers.SerializerMethodField()
    solicitud_numero = serializers.SerializerMethodField()
    muestra_codigo_barra = serializers.SerializerMethodField()
    muestra_tipo_nombre = serializers.SerializerMethodField()
    tipo_cultivo_nombre = serializers.SerializerMethodField()
    tipo_muestra_micro_nombre = serializers.SerializerMethodField()
    tipo_pedido = serializers.SerializerMethodField()
    sin_etiquetas = serializers.SerializerMethodField()
    esperando_recepcion = serializers.SerializerMethodField()
    origen_solicitud_display = serializers.SerializerMethodField()
    procedencia_display = serializers.SerializerMethodField()
    estado_obra_social_display = serializers.SerializerMethodField()
    requiere_autorizacion_obra_social = serializers.SerializerMethodField()
    obra_social_permite_validar = serializers.SerializerMethodField()

    class Meta:
        model = EstudioMicrobiologia
        fields = (
            "id",
            "numero",
            "solicitud",
            "solicitud_numero",
            "muestra",
            "muestra_codigo_barra",
            "muestra_tipo_nombre",
            "paciente",
            "paciente_nombre",
            "paciente_dni",
            "paciente_email",
            "paciente_telefono",
            "medico_interno",
            "medico_externo_nombre",
            "medico_display",
            "medico_email",
            "medico_telefono",
            "consulta_hc",
            "origen_solicitud",
            "origen_solicitud_display",
            "procedencia_display",
            "codigo_barra",
            "etiquetas_impresas_at",
            "sin_etiquetas",
            "esperando_recepcion",
            "tipo_pedido",
            "tipo_cultivo",
            "tipo_cultivo_nombre",
            "tipo_muestra_micro",
            "tipo_muestra_micro_nombre",
            "tipo_estudio",
            "estado",
            "estado_obra_social",
            "estado_obra_social_display",
            "requiere_autorizacion_obra_social",
            "obra_social_permite_validar",
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

    def get_paciente_nombre(self, obj):
        return format_apellido_nombre(getattr(obj, "paciente", None))

    def get_paciente_dni(self, obj):
        p = getattr(obj, "paciente", None)
        return getattr(p, "dni", None) if p else None

    def get_paciente_email(self, obj):
        p = getattr(obj, "paciente", None)
        return (getattr(p, "email", None) or "").strip() or None if p else None

    def get_paciente_telefono(self, obj):
        p = getattr(obj, "paciente", None)
        return (getattr(p, "telefono", None) or "").strip() or None if p else None

    def get_medico_display(self, obj):
        mi = getattr(obj, "medico_interno", None)
        if mi:
            return format_medico_display(mi, fallback=str(mi))
        ext = (getattr(obj, "medico_externo_nombre", None) or "").strip()
        if ext:
            return ext
        sol = getattr(obj, "solicitud", None)
        if not sol:
            return None
        mi = getattr(sol, "medico_interno", None)
        if mi:
            return format_medico_display(mi, fallback=str(mi))
        return (getattr(sol, "medico_externo_nombre", None) or "").strip() or None

    def get_medico_email(self, obj):
        mi = getattr(obj, "medico_interno", None)
        if not mi:
            return None
        return (getattr(mi, "email", None) or "").strip() or None

    def get_medico_telefono(self, obj):
        mi = getattr(obj, "medico_interno", None)
        if not mi:
            return None
        return (getattr(mi, "telefono", None) or "").strip() or None

    def get_solicitud_numero(self, obj):
        sol = getattr(obj, "solicitud", None)
        return getattr(sol, "numero", None) if sol else None

    def get_muestra_codigo_barra(self, obj):
        own = getattr(obj, "codigo_barra", None)
        if own:
            return own
        m = getattr(obj, "muestra", None)
        return getattr(m, "codigo_barra", None) if m else None

    def get_muestra_tipo_nombre(self, obj):
        tm = getattr(obj, "tipo_muestra_micro", None)
        if tm:
            return tm.nombre
        m = getattr(obj, "muestra", None)
        if not m:
            return None
        lims_tm = getattr(m, "tipo_muestra", None)
        return getattr(lims_tm, "nombre", None) if lims_tm else None

    def get_tipo_cultivo_nombre(self, obj):
        tc = getattr(obj, "tipo_cultivo", None)
        return tc.nombre if tc else None

    def get_tipo_muestra_micro_nombre(self, obj):
        tm = getattr(obj, "tipo_muestra_micro", None)
        return tm.nombre if tm else None

    def get_tipo_pedido(self, obj):
        return "MICROBIOLOGIA"

    def get_sin_etiquetas(self, obj):
        return bool(getattr(obj, "sin_etiquetas", False))

    def get_esperando_recepcion(self, obj):
        return bool(getattr(obj, "esperando_recepcion", False))

    def get_origen_solicitud_display(self, obj):
        from laboratorio.origen_solicitud import label_origen_solicitud

        return label_origen_solicitud(getattr(obj, "origen_solicitud", None) or None)

    def get_procedencia_display(self, obj):
        """Misma procedencia que Lab. Clínico cuando hay solicitud o consulta HC."""
        from laboratorio.procedencia_display import resolver_procedencia_solicitud

        sol = getattr(obj, "solicitud", None)
        if sol is not None:
            return resolver_procedencia_solicitud(sol).get("procedencia_display")

        consulta = getattr(obj, "consulta_hc", None)
        if consulta is None:
            from laboratorio.origen_solicitud import label_origen_solicitud

            return label_origen_solicitud(getattr(obj, "origen_solicitud", None) or None)

        class _Proxy:
            pass

        proxy = _Proxy()
        proxy.consulta_hc = consulta
        proxy.paciente_id = getattr(obj, "paciente_id", None)
        proxy.origen_solicitud = getattr(obj, "origen_solicitud", "") or ""
        proxy.fecha_solicitud = getattr(obj, "created_at", None) or getattr(
            obj, "fecha_inicio", None
        )
        proxy.medico_externo_nombre = getattr(obj, "medico_externo_nombre", None) or ""
        return resolver_procedencia_solicitud(proxy).get("procedencia_display")

    def get_estado_obra_social_display(self, obj):
        return obj.get_estado_obra_social_display() or ""

    def get_requiere_autorizacion_obra_social(self, obj):
        from laboratorio.obra_social import origen_requiere_autorizacion_obra_social

        return origen_requiere_autorizacion_obra_social(getattr(obj, "origen_solicitud", None))

    def get_obra_social_permite_validar(self, obj):
        from laboratorio.obra_social import obra_social_permite_liberar

        return obra_social_permite_liberar(obj)


class EstudioMicrobiologiaCreateSerializer(serializers.Serializer):
    """
    Alta de estudio microbiológico independiente de LIMS química.

    Preferido: paciente_id + tipo_cultivo_id + tipo_muestra_micro_id (+ médico).
    Legado: solicitud_id + muestra_id.
    """

    paciente_id = serializers.IntegerField(required=False)
    medico_id = serializers.IntegerField(required=False, allow_null=True)
    medico_externo_nombre = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    consulta_hc_id = serializers.IntegerField(required=False, allow_null=True)
    origen_solicitud = serializers.CharField(required=False, allow_blank=True, default="")
    tipo_cultivo_id = serializers.IntegerField(required=False)
    tipo_muestra_micro_id = serializers.IntegerField(required=False)
    # Alias aceptados por compatibilidad con el front anterior.
    tipo_muestra_id = serializers.IntegerField(required=False)
    muestra_id = serializers.IntegerField(required=False)
    solicitud_id = serializers.IntegerField(required=False)
    tipo_estudio = serializers.CharField(required=False, allow_blank=True, default="")
    observaciones = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        from pacientes.models import Paciente
        from medicos.models import Medico
        from historias_clinicas.models import Consulta
        from laboratorio.origen_solicitud import normalizar_origen_solicitud

        solicitud_id = attrs.get("solicitud_id")
        muestra_id = attrs.get("muestra_id")
        paciente_id = attrs.get("paciente_id")

        if solicitud_id and muestra_id and not paciente_id:
            try:
                sol = SolicitudExamen.objects.get(pk=solicitud_id)
            except SolicitudExamen.DoesNotExist as exc:
                raise serializers.ValidationError(
                    {"solicitud_id": "Solicitud inexistente."}
                ) from exc
            try:
                muestra = Muestra.objects.get(pk=muestra_id)
            except Muestra.DoesNotExist as exc:
                raise serializers.ValidationError(
                    {"muestra_id": "Muestra inexistente."}
                ) from exc
            if muestra.solicitud_id != sol.pk:
                raise serializers.ValidationError(
                    {"muestra_id": "La muestra no pertenece a la solicitud indicada."}
                )
            attrs["_modo"] = "legado"
            attrs["_solicitud"] = sol
            attrs["_muestra"] = muestra
            return attrs

        if not paciente_id:
            raise serializers.ValidationError(
                {"paciente_id": "Indique el paciente."}
            )

        try:
            paciente = Paciente.objects.get(pk=paciente_id)
        except Paciente.DoesNotExist as exc:
            raise serializers.ValidationError(
                {"paciente_id": "Paciente inexistente."}
            ) from exc

        medico = None
        medico_id = attrs.get("medico_id")
        if medico_id:
            try:
                medico = Medico.objects.get(pk=medico_id)
            except Medico.DoesNotExist as exc:
                raise serializers.ValidationError(
                    {"medico_id": "Médico inexistente."}
                ) from exc

        tipo_cultivo_id = attrs.get("tipo_cultivo_id")
        if not tipo_cultivo_id:
            raise serializers.ValidationError(
                {"tipo_cultivo_id": "Indique el tipo de cultivo."}
            )
        try:
            cultivo = TipoCultivoMicrobiologia.objects.get(pk=tipo_cultivo_id, activo=True)
        except TipoCultivoMicrobiologia.DoesNotExist as exc:
            raise serializers.ValidationError(
                {"tipo_cultivo_id": "Tipo de cultivo inexistente o inactivo."}
            ) from exc

        tipo_muestra_micro_id = attrs.get("tipo_muestra_micro_id") or attrs.get(
            "tipo_muestra_id"
        )
        if not tipo_muestra_micro_id:
            raise serializers.ValidationError(
                {"tipo_muestra_micro_id": "Indique el tipo de muestra."}
            )
        try:
            muestra_micro = TipoMuestraMicrobiologia.objects.get(
                pk=tipo_muestra_micro_id, activo=True
            )
        except TipoMuestraMicrobiologia.DoesNotExist as exc:
            raise serializers.ValidationError(
                {"tipo_muestra_micro_id": "Tipo de muestra inexistente o inactivo."}
            ) from exc

        consulta = None
        consulta_hc_id = attrs.get("consulta_hc_id")
        if consulta_hc_id:
            try:
                consulta = Consulta.objects.get(pk=consulta_hc_id)
            except Consulta.DoesNotExist as exc:
                raise serializers.ValidationError(
                    {"consulta_hc_id": "Consulta inexistente."}
                ) from exc

        origen = normalizar_origen_solicitud(attrs.get("origen_solicitud")) or (
            attrs.get("origen_solicitud") or ""
        ).strip()

        attrs["_modo"] = "pedido"
        attrs["_paciente"] = paciente
        attrs["_medico"] = medico
        attrs["_tipo_cultivo"] = cultivo
        attrs["_tipo_muestra_micro"] = muestra_micro
        attrs["_consulta_hc"] = consulta
        attrs["_origen_solicitud"] = origen
        return attrs


class EstudioMicroItemSerializer(serializers.Serializer):
    tipo_cultivo_id = serializers.IntegerField()
    tipo_muestra_micro_id = serializers.IntegerField()


class EstudioMicrobiologiaBatchCreateSerializer(serializers.Serializer):
    paciente_id = serializers.IntegerField()
    medico_id = serializers.IntegerField(required=False, allow_null=True)
    medico_externo_nombre = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    consulta_hc_id = serializers.IntegerField(required=False, allow_null=True)
    origen_solicitud = serializers.CharField(required=False, allow_blank=True, default="")
    observaciones = serializers.CharField(required=False, allow_blank=True, default="")
    items = EstudioMicroItemSerializer(many=True)

    def validate(self, attrs):
        from pacientes.models import Paciente
        from medicos.models import Medico
        from historias_clinicas.models import Consulta
        from laboratorio.origen_solicitud import normalizar_origen_solicitud

        try:
            paciente = Paciente.objects.get(pk=attrs["paciente_id"])
        except Paciente.DoesNotExist as exc:
            raise serializers.ValidationError(
                {"paciente_id": "Paciente inexistente."}
            ) from exc

        medico = None
        medico_id = attrs.get("medico_id")
        if medico_id:
            try:
                medico = Medico.objects.get(pk=medico_id)
            except Medico.DoesNotExist as exc:
                raise serializers.ValidationError(
                    {"medico_id": "Médico inexistente."}
                ) from exc

        consulta = None
        consulta_hc_id = attrs.get("consulta_hc_id")
        if consulta_hc_id:
            try:
                consulta = Consulta.objects.get(pk=consulta_hc_id)
            except Consulta.DoesNotExist as exc:
                raise serializers.ValidationError(
                    {"consulta_hc_id": "Consulta inexistente."}
                ) from exc

        items = attrs.get("items") or []
        if not items:
            raise serializers.ValidationError({"items": "Indique al menos un cultivo."})

        seen = set()
        for item in items:
            key = (item["tipo_cultivo_id"], item["tipo_muestra_micro_id"])
            if key in seen:
                raise serializers.ValidationError(
                    {"items": "Hay cultivos duplicados con la misma muestra."}
                )
            seen.add(key)
            if not TipoCultivoMicrobiologia.objects.filter(
                pk=item["tipo_cultivo_id"], activo=True
            ).exists():
                raise serializers.ValidationError(
                    {"items": "Tipo de cultivo inexistente o inactivo."}
                )
            if not TipoMuestraMicrobiologia.objects.filter(
                pk=item["tipo_muestra_micro_id"], activo=True
            ).exists():
                raise serializers.ValidationError(
                    {"items": "Tipo de muestra inexistente o inactivo."}
                )

        origen = normalizar_origen_solicitud(attrs.get("origen_solicitud")) or (
            attrs.get("origen_solicitud") or ""
        ).strip()

        attrs["_paciente"] = paciente
        attrs["_medico"] = medico
        attrs["_consulta_hc"] = consulta
        attrs["_origen_solicitud"] = origen
        return attrs


class EstudioMicroImprimirEtiquetasSerializer(serializers.Serializer):
    estudio_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
    )


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


class EstudioRecibirPorCodigoSerializer(serializers.Serializer):
    """Escaneo de recepción micro: body con código (LAB-… canónico o legacy MICB-/MIC-)."""

    codigo_barra = serializers.CharField()

    def validate_codigo_barra(self, value):
        cb = (value or "").strip()
        if not cb:
            raise serializers.ValidationError("El código de barras es obligatorio.")
        return cb


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
    contenido_visible = serializers.SerializerMethodField()

    class Meta:
        model = InformeMicrobiologia
        fields = (
            "id",
            "estudio",
            "tipo",
            "estado",
            "texto",
            "contenido_visible",
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

    def get_contenido_visible(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None
        if user is None:
            return False
        from api.permissions import usuario_puede_ver_contenido_informe_micro

        return usuario_puede_ver_contenido_informe_micro(user, obj)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not data.get("contenido_visible"):
            data["texto"] = ""
            data["observaciones"] = ""
        return data


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
