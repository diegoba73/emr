"""
Serializers para la app laboratorio (LIMS).
"""
import logging
from decimal import Decimal

from rest_framework import serializers
from django.db import transaction
from .models import (
    TipoMuestra,
    TipoExamen,
    PanelExamen,
    SolicitudExamen,
    ResultadoExamen,
)
from .models_catalog import TipoContenedor
from pacientes.models import Paciente
from medicos.models import Medico
from historias_clinicas.models import Consulta
from laboratorio.panel_componentes_orden import ordenar_ids_por_panel, ordenar_queryset_panel
from laboratorio.procedencia_display import resolver_procedencia_solicitud
from laboratorio.origen_solicitud import (
    es_origen_ambulatorio_externo,
    inferir_origen_solicitud,
    label_origen_solicitud,
    normalizar_origen_solicitud,
)

logger = logging.getLogger(__name__)


# ============================================================================
# SERIALIZERS DE INFRAESTRUCTURA
# ============================================================================

class TipoMuestraSerializer(serializers.ModelSerializer):
    """Serializer para TipoMuestra."""

    class Meta:
        model = TipoMuestra
        fields = [
            'id',
            'codigo',
            'nombre',
            'color_tubo',
            'activo',
        ]
        read_only_fields = ['id']

    def validate_codigo(self, value):
        codigo = (value or '').strip().upper()
        if not codigo:
            raise serializers.ValidationError('El código es obligatorio.')
        if len(codigo) > 64:
            raise serializers.ValidationError('Máximo 64 caracteres.')
        qs = TipoMuestra.objects.filter(codigo__iexact=codigo)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Ya existe un tipo de muestra con ese código.')
        return codigo

    def validate_nombre(self, value):
        nombre = (value or '').strip()
        if not nombre:
            raise serializers.ValidationError('El nombre es obligatorio.')
        return nombre


class NullableDecimalField(serializers.DecimalField):
    """DecimalField que trata '' como null (PATCH parcial desde UI)."""

    def to_internal_value(self, data):
        if data in ('', None):
            return None
        return super().to_internal_value(data)


class TipoExamenSerializer(serializers.ModelSerializer):
    """Serializer para TipoExamen (catálogo LIMS)."""
    tipo_muestra_nombre = serializers.CharField(
        source='tipo_muestra_requerida.nombre',
        read_only=True
    )
    tipo_muestra_codigo = serializers.CharField(
        source='tipo_muestra_requerida.codigo',
        read_only=True
    )
    tipo_contenedor_codigo = serializers.CharField(
        source='tipo_contenedor.codigo',
        read_only=True,
        allow_null=True,
    )
    tipo_contenedor_nombre = serializers.CharField(
        source='tipo_contenedor.nombre',
        read_only=True,
        allow_null=True,
    )
    tipo_muestra_requerida = serializers.PrimaryKeyRelatedField(
        queryset=TipoMuestra.objects.all(),
        help_text="ID del tipo de muestra requerida"
    )
    tipo_contenedor = serializers.PrimaryKeyRelatedField(
        queryset=TipoContenedor.objects.all(),
        required=False,
        allow_null=True,
        help_text="ID del tipo de tubo / contenedor",
    )
    metodo = serializers.CharField(required=False, allow_blank=True, allow_null=True, default='')
    unidad_default = serializers.CharField(required=False, allow_blank=True, allow_null=True, default='')
    abreviatura = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    formato_informe_entrada = serializers.CharField(required=False, allow_blank=True, allow_null=True, default='')
    multiplicador_clinico = NullableDecimalField(
        max_digits=16,
        decimal_places=6,
        required=False,
        allow_null=True,
    )
    laboratorio_derivacion_codigo = serializers.CharField(
        source='laboratorio_derivacion.codigo',
        read_only=True,
        allow_null=True,
    )
    laboratorio_derivacion_nombre = serializers.CharField(
        source='laboratorio_derivacion.nombre',
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = TipoExamen
        fields = [
            'id',
            'codigo',
            'nombre',
            'abreviatura',
            'tipo_muestra_requerida',
            'tipo_muestra_nombre',
            'tipo_muestra_codigo',
            'tipo_contenedor',
            'tipo_contenedor_codigo',
            'tipo_contenedor_nombre',
            'seccion',
            'tipo_resultado',
            'metodo',
            'unidad_default',
            'precio',
            'rango_referencia_texto',
            'rango_min',
            'rango_max',
            'valor_critico_min',
            'valor_critico_max',
            'permite_resultado_texto',
            'requiere_muestra',
            'modo_entrada',
            'ticket_decimales',
            'multiplicador_clinico',
            'formato_informe_entrada',
            'laboratorio_derivacion',
            'laboratorio_derivacion_codigo',
            'laboratorio_derivacion_nombre',
            'activo',
        ]
        read_only_fields = [
            'id',
            'tipo_muestra_nombre',
            'tipo_muestra_codigo',
            'tipo_contenedor_codigo',
            'tipo_contenedor_nombre',
            'laboratorio_derivacion_codigo',
            'laboratorio_derivacion_nombre',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance is not None:
            self.fields['codigo'].read_only = True

    def validate_codigo(self, value):
        codigo = (value or '').strip().upper()
        if not codigo:
            raise serializers.ValidationError('El código es obligatorio.')
        return codigo

    def validate_nombre(self, value):
        nombre = (value or '').strip()
        if not nombre:
            raise serializers.ValidationError('El nombre es obligatorio.')
        return nombre

    def validate_metodo(self, value):
        if value is None:
            return ''
        return (value or '').strip()

    def validate_unidad_default(self, value):
        if value is None:
            return ''
        return (value or '').strip()

    def validate_multiplicador_clinico(self, value):
        if value in (None, ''):
            return Decimal('1')
        return value

    def validate(self, attrs):
        for field in ('formato_informe_entrada', 'abreviatura', 'rango_referencia_texto'):
            if field in attrs and attrs[field] is None:
                attrs[field] = ''

        modo = attrs.get(
            'modo_entrada',
            getattr(self.instance, 'modo_entrada', TipoExamen.ModoEntradaResultado.ESTANDAR),
        )
        if modo == TipoExamen.ModoEntradaResultado.ESTANDAR:
            attrs['ticket_decimales'] = 0
            attrs['multiplicador_clinico'] = Decimal('1')
            attrs['formato_informe_entrada'] = ''

        ticket_dec = attrs.get(
            'ticket_decimales',
            getattr(self.instance, 'ticket_decimales', 0),
        )
        formato = attrs.get(
            'formato_informe_entrada',
            getattr(self.instance, 'formato_informe_entrada', ''),
        )
        if modo in (
            TipoExamen.ModoEntradaResultado.TICKET_ENTERO,
            TipoExamen.ModoEntradaResultado.FORMULA_PORCENTAJE,
        ):
            if not (formato or '').strip():
                raise serializers.ValidationError(
                    {
                        'formato_informe_entrada': (
                            'Obligatorio cuando el modo de entrada es ticket o fórmula.'
                        )
                    }
                )
            if ticket_dec > 4:
                raise serializers.ValidationError(
                    {'ticket_decimales': 'Máximo 4 decimales implícitos.'}
                )
        elif modo == TipoExamen.ModoEntradaResultado.ESTANDAR and ticket_dec != 0:
            raise serializers.ValidationError(
                {'ticket_decimales': 'Debe ser 0 en modo estándar.'}
            )
        return attrs


class PanelExamenSerializer(serializers.ModelSerializer):
    """Serializer para PanelExamen."""
    tipos_examen_nombres = serializers.SerializerMethodField()
    tipos_examen_detalle = serializers.SerializerMethodField()
    tipos_examen_ids = serializers.PrimaryKeyRelatedField(
        queryset=TipoExamen.objects.all(),
        many=True,
        write_only=True,
        required=False,
        source='tipos_examen'
    )

    class Meta:
        model = PanelExamen
        fields = [
            'id',
            'codigo',
            'nombre',
            'tipos_examen',
            'tipos_examen_ids',
            'tipos_examen_nombres',
            'tipos_examen_detalle',
            'activo',
        ]
        read_only_fields = ['id', 'tipos_examen_nombres', 'tipos_examen_detalle']

    def get_tipos_examen_nombres(self, obj):
        """Retorna los nombres de los tipos de examen del panel (orden clínico)."""
        return [te.nombre for te in ordenar_queryset_panel(obj)]

    def get_tipos_examen_detalle(self, obj):
        """Componentes ordenados con id/código/nombre para UI de catálogo."""
        return [
            {"id": te.id, "codigo": te.codigo, "nombre": te.nombre}
            for te in ordenar_queryset_panel(obj)
        ]

    def validate_codigo(self, value):
        codigo = (value or "").strip().upper()
        if not codigo:
            raise serializers.ValidationError("El código es obligatorio.")
        qs = PanelExamen.objects.filter(codigo__iexact=codigo)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ya existe un panel con ese código.")
        return codigo


# ============================================================================
# SERIALIZERS DE RESULTADOS
# ============================================================================

class ResultadoExamenSerializer(serializers.ModelSerializer):
    """
    Serializer para ResultadoExamen.
    Lectura: Incluye datos del tipo_examen (nested).
    Escritura: Campos valor_obtenido, es_patologico, observaciones.
    """
    tipo_examen_nombre = serializers.CharField(
        source='tipo_examen.nombre',
        read_only=True
    )
    tipo_examen_codigo = serializers.CharField(
        source='tipo_examen.codigo',
        read_only=True
    )
    tipo_examen_rango_referencia = serializers.CharField(
        source='tipo_examen.rango_referencia_texto',
        read_only=True
    )
    validado_por_nombre = serializers.CharField(
        source='validado_por.username',
        read_only=True
    )
    muestra_id = serializers.IntegerField(read_only=True, allow_null=True)
    muestra_estado = serializers.CharField(
        source="muestra.estado",
        read_only=True,
        allow_null=True,
        default=None,
    )
    tipo_muestra_nombre = serializers.CharField(
        source="muestra.tipo_muestra.nombre",
        read_only=True,
        allow_null=True,
        default=None,
    )
    tipo_examen_muestra_codigo = serializers.CharField(
        source="tipo_examen.tipo_muestra_requerida.codigo",
        read_only=True,
        allow_null=True,
        default=None,
    )
    laboratorio_derivacion = serializers.PrimaryKeyRelatedField(read_only=True, allow_null=True)
    laboratorio_derivacion_codigo = serializers.CharField(
        source="laboratorio_derivacion.codigo",
        read_only=True,
        allow_null=True,
    )
    laboratorio_derivacion_nombre = serializers.CharField(
        source="laboratorio_derivacion.nombre",
        read_only=True,
        allow_null=True,
    )
    laboratorio_derivacion_ciudad = serializers.CharField(
        source="laboratorio_derivacion.ciudad",
        read_only=True,
        allow_null=True,
    )
    estado_derivacion = serializers.CharField(read_only=True)
    fecha_envio_derivacion = serializers.DateTimeField(read_only=True, allow_null=True)
    observaciones_derivacion = serializers.CharField(read_only=True)

    class Meta:
        model = ResultadoExamen
        fields = [
            'id',
            'solicitud',
            'tipo_examen',
            'tipo_examen_nombre',
            'tipo_examen_codigo',
            'tipo_examen_rango_referencia',
            'valor_obtenido',
            'valor_numerico',
            'unidad',
            'rango_referencia_snapshot',
            'rango_min_snapshot',
            'rango_max_snapshot',
            'es_patologico',
            'es_critico',
            'valor_critico_min_snapshot',
            'valor_critico_max_snapshot',
            'validado_por',
            'validado_por_nombre',
            'fecha_validacion',
            'observaciones',
            'muestra_id',
            'muestra_estado',
            'tipo_muestra_nombre',
            'tipo_examen_muestra_codigo',
            'laboratorio_derivacion',
            'laboratorio_derivacion_codigo',
            'laboratorio_derivacion_nombre',
            'laboratorio_derivacion_ciudad',
            'estado_derivacion',
            'fecha_envio_derivacion',
            'observaciones_derivacion',
        ]
        read_only_fields = [
            'id',
            'solicitud',
            'tipo_examen',
            'tipo_examen_nombre',
            'tipo_examen_codigo',
            'tipo_examen_rango_referencia',
            'validado_por_nombre',
            'fecha_validacion',
            'muestra_id',
            'muestra_estado',
            'tipo_muestra_nombre',
            'tipo_examen_muestra_codigo',
            'laboratorio_derivacion',
            'laboratorio_derivacion_codigo',
            'laboratorio_derivacion_nombre',
            'laboratorio_derivacion_ciudad',
            'estado_derivacion',
            'fecha_envio_derivacion',
            'observaciones_derivacion',
        ]


# ============================================================================
# SERIALIZERS DE SOLICITUDES
# ============================================================================

class SolicitudExamenSerializer(serializers.ModelSerializer):
    """
    Serializer de lectura para SolicitudExamen.
    Incluye paciente (nombre, dni), medico (lógica híbrida), y resultados (nested many=True).
    """
    paciente_nombre = serializers.CharField(
        source='paciente.nombre_completo',
        read_only=True
    )
    paciente_dni = serializers.CharField(
        source='paciente.dni',
        read_only=True
    )
    paciente_email = serializers.EmailField(
        source='paciente.email',
        read_only=True,
    )
    paciente_telefono = serializers.CharField(
        source='paciente.telefono',
        read_only=True,
    )
    medico_display = serializers.CharField(read_only=True)
    medico_interno_nombre = serializers.CharField(
        source='medico_interno.nombre_completo',
        read_only=True
    )
    medico_email = serializers.SerializerMethodField()
    medico_telefono = serializers.SerializerMethodField()
    resultados = ResultadoExamenSerializer(many=True, read_only=True)
    tipos_examen_nombres = serializers.SerializerMethodField()
    paneles_nombres = serializers.SerializerMethodField()
    paneles_resumen = serializers.SerializerMethodField()
    procedencia_tipo = serializers.SerializerMethodField()
    procedencia_display = serializers.SerializerMethodField()
    origen_solicitud_display = serializers.SerializerMethodField()
    fecha_toma_muestra = serializers.DateTimeField(read_only=True, required=False)
    extraccion_completa = serializers.SerializerMethodField()
    tubos_pendientes_extraccion = serializers.SerializerMethodField()
    orden_abierta = serializers.SerializerMethodField()
    esperando_recepcion = serializers.SerializerMethodField()
    puede_agregar_examenes = serializers.SerializerMethodField()
    pedido_adicional = serializers.SerializerMethodField()
    merged = serializers.SerializerMethodField()
    derivaciones_resumen = serializers.SerializerMethodField()
    
    class Meta:
        model = SolicitudExamen
        fields = [
            'id',
            'numero',
            'paciente',
            'paciente_nombre',
            'paciente_dni',
            'paciente_email',
            'paciente_telefono',
            'medico_interno',
            'medico_interno_nombre',
            'medico_externo_nombre',
            'medico_display',
            'medico_email',
            'medico_telefono',
            'origen_solicitud',
            'origen_solicitud_display',
            'tipos_examen',
            'tipos_examen_nombres',
            'paneles',
            'paneles_nombres',
            'paneles_resumen',
            'procedencia_tipo',
            'procedencia_display',
            'estado',
            'fecha_solicitud',
            'fecha_toma_muestra',
            'fecha_entrega_prometida',
            'observaciones',
            'fecha_informe_enviado',
            'informe_enviado_email',
            'informe_enviado_whatsapp',
            'consulta_hc',
            'resultados',
            'orden_grupos_informe',
            'extraccion_completa',
            'tubos_pendientes_extraccion',
            'orden_abierta',
            'esperando_recepcion',
            'puede_agregar_examenes',
            'pedido_adicional',
            'merged',
            'derivaciones_resumen',
        ]
        read_only_fields = [
            'id',
            'numero',
            'fecha_solicitud',
            'estado',
            'paciente_nombre',
            'paciente_dni',
            'paciente_email',
            'paciente_telefono',
            'medico_display',
            'medico_interno_nombre',
            'medico_email',
            'medico_telefono',
            'tipos_examen_nombres',
            'paneles_nombres',
            'extraccion_completa',
            'tubos_pendientes_extraccion',
            'orden_abierta',
            'esperando_recepcion',
            'puede_agregar_examenes',
            'pedido_adicional',
            'merged',
            'derivaciones_resumen',
        ]
    
    def get_medico_email(self, obj):
        medico = getattr(obj, 'medico_interno', None)
        if not medico:
            return None
        return (getattr(medico, 'email', None) or '').strip() or None

    def get_medico_telefono(self, obj):
        medico = getattr(obj, 'medico_interno', None)
        if not medico:
            return None
        return (getattr(medico, 'telefono', None) or '').strip() or None

    def get_tipos_examen_nombres(self, obj):
        """Retorna los nombres de los tipos de examen."""
        return [te.nombre for te in obj.tipos_examen.all()]
    
    def get_paneles_nombres(self, obj):
        """Retorna los nombres de los paneles."""
        return [p.nombre for p in obj.paneles.all()]

    def get_paneles_resumen(self, obj):
        """Paneles de la orden con ids de exámenes componentes (agrupación en UI)."""
        out = []
        for p in obj.paneles.all():
            pares = list(p.tipos_examen.values_list("id", "codigo"))
            out.append(
                {
                    "id": p.id,
                    "codigo": p.codigo,
                    "nombre": p.nombre,
                    "tipos_examen_ids": ordenar_ids_por_panel(p.codigo, pares),
                }
            )
        return out

    def _procedencia(self, obj):
        cached = getattr(obj, "_cached_procedencia", None)
        if cached is None:
            cached = resolver_procedencia_solicitud(obj)
            obj._cached_procedencia = cached
        return cached

    def get_procedencia_tipo(self, obj):
        return self._procedencia(obj).get("procedencia_tipo")

    def get_procedencia_display(self, obj):
        return self._procedencia(obj).get("procedencia_display")

    def get_origen_solicitud_display(self, obj):
        return label_origen_solicitud(getattr(obj, 'origen_solicitud', None))

    def get_extraccion_completa(self, obj):
        from laboratorio.muestra_estado import extraccion_completa

        return extraccion_completa(obj.pk)

    def get_tubos_pendientes_extraccion(self, obj):
        from laboratorio.muestra_estado import tubos_pendientes_extraccion

        out = []
        for p in tubos_pendientes_extraccion(obj.pk):
            out.append(
                {
                    "id": p.pk,
                    "codigo_barra": p.codigo_barra,
                    "tipo_contenedor_codigo": p.tipo_contenedor.codigo if p.tipo_contenedor_id else None,
                    "tipo_contenedor_nombre": p.tipo_contenedor.nombre if p.tipo_contenedor_id else None,
                    "estado": p.estado,
                }
            )
        return out

    def get_orden_abierta(self, obj):
        from laboratorio.solicitud_orden_abierta import orden_esta_abierta

        return orden_esta_abierta(obj)

    def get_esperando_recepcion(self, obj):
        from laboratorio.solicitud_orden_abierta import orden_esperando_recepcion

        return orden_esperando_recepcion(obj)

    def get_puede_agregar_examenes(self, obj):
        from laboratorio.solicitud_orden_abierta import orden_permite_intentar_agregar_examenes

        return orden_permite_intentar_agregar_examenes(obj)

    def get_pedido_adicional(self, obj):
        """
        Orden PENDIENTE editable creada mientras el paciente ya tiene otra
        orden en curso (EN_PROCESO / parcial / a validar).
        """
        from laboratorio.solicitud_orden_abierta import (
            orden_esta_abierta,
            paciente_tiene_orden_bloqueada,
        )

        if not orden_esta_abierta(obj):
            return False
        return paciente_tiene_orden_bloqueada(
            obj.paciente_id, exclude_solicitud_id=obj.pk
        )

    def get_merged(self, obj):
        return bool(getattr(obj, "_orden_merged", False))

    def get_derivaciones_resumen(self, obj):
        out = []
        for r in obj.resultados.all():
            if getattr(r, "estado_derivacion", "LOCAL") == "LOCAL" and not r.laboratorio_derivacion_id:
                continue
            out.append(
                {
                    "resultado_id": r.id,
                    "tipo_examen_codigo": r.tipo_examen.codigo if r.tipo_examen_id else None,
                    "tipo_examen_nombre": r.tipo_examen.nombre if r.tipo_examen_id else None,
                    "laboratorio_codigo": (
                        r.laboratorio_derivacion.codigo if r.laboratorio_derivacion_id else None
                    ),
                    "laboratorio_nombre": (
                        r.laboratorio_derivacion.nombre if r.laboratorio_derivacion_id else None
                    ),
                    "estado_derivacion": r.estado_derivacion,
                }
            )
        return out


class SolicitudExamenCreateSerializer(serializers.ModelSerializer):
    """
    Serializer de escritura para SolicitudExamen.
    Campos: paciente_id, medico_id (opcional), medico_externo_nombre (opcional),
    origen_solicitud, examenes_ids (ListField de ints), paneles_ids (ListField de ints).
    Método create: Crea la Solicitud y los ResultadoExamen asociados en estado PENDIENTE.
    """
    paciente_id = serializers.PrimaryKeyRelatedField(
        queryset=Paciente.objects.all(),
        source='paciente',
        write_only=True,
        help_text="ID del paciente"
    )
    medico_id = serializers.PrimaryKeyRelatedField(
        queryset=Medico.objects.all(),
        source='medico_interno',
        write_only=True,
        required=False,
        allow_null=True,
        help_text="ID del médico interno (opcional)"
    )
    examenes_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        allow_empty=True
    )
    paneles_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        allow_empty=True
    )
    consulta_hc_id = serializers.PrimaryKeyRelatedField(
        queryset=Consulta.objects.all(),
        source='consulta_hc',
        write_only=True,
        required=False,
        allow_null=True,
    )
    
    class Meta:
        model = SolicitudExamen
        fields = [
            'id',
            'paciente_id',
            'medico_id',
            'medico_externo_nombre',
            'origen_solicitud',
            'examenes_ids',
            'paneles_ids',
            'consulta_hc_id',
            'fecha_entrega_prometida',
            'observaciones',
        ]
        read_only_fields = ['id']
    
    def validate_origen_solicitud(self, value):
        normalizado = normalizar_origen_solicitud(value)
        if value and not normalizado:
            raise serializers.ValidationError('Origen clínico no válido.')
        return normalizado or value

    def validate(self, attrs):
        origen = normalizar_origen_solicitud(attrs.get('origen_solicitud')) or attrs.get('origen_solicitud')
        consulta = attrs.get('consulta_hc')
        medico_ext = (attrs.get('medico_externo_nombre') or '').strip()
        medico_int = attrs.get('medico_interno')

        if consulta and es_origen_ambulatorio_externo(origen):
            raise serializers.ValidationError(
                {'origen_solicitud': 'Una orden vinculada a consulta no puede ser ambulatorio externo.'}
            )
        if es_origen_ambulatorio_externo(origen) and not medico_ext and not medico_int:
            raise serializers.ValidationError(
                {'medico_externo_nombre': 'Indique el médico solicitante de la receta externa.'}
            )
        if es_origen_ambulatorio_externo(origen):
            attrs['medico_interno'] = None
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        """
        Método create atómico:
        - Si el paciente ya tiene orden abierta (PENDIENTE sin toma), fusiona exámenes.
        - Si no: crea Solicitud + ResultadoExamen (directos y de paneles, sin duplicados).
        """
        from laboratorio.solicitud_orden_abierta import (
            agregar_examenes_a_solicitud,
            buscar_orden_abierta,
        )

        examenes_ids = validated_data.pop('examenes_ids', [])
        paneles_ids = validated_data.pop('paneles_ids', [])
        origen_explicito = validated_data.pop('origen_solicitud', None)
        paciente = validated_data.get('paciente')
        consulta_hc = validated_data.get('consulta_hc')
        validated_data['origen_solicitud'] = inferir_origen_solicitud(
            paciente_id=paciente.pk,
            consulta_hc=consulta_hc,
            origen_explicito=origen_explicito,
        )

        abierta = buscar_orden_abierta(paciente.pk)
        if abierta is not None:
            solicitud = agregar_examenes_a_solicitud(
                abierta,
                examenes_ids=examenes_ids,
                paneles_ids=paneles_ids,
            )
            solicitud._orden_merged = True
            return solicitud

        solicitud = SolicitudExamen.objects.create(**validated_data)
        solicitud._orden_merged = False

        if paneles_ids:
            solicitud.paneles.set(paneles_ids)

        tipos_examen_creados = set()
        from laboratorio.derivacion_service import defaults_derivacion_para_tipo

        for tipo_examen_id in examenes_ids:
            try:
                tipo_examen = TipoExamen.objects.select_related(
                    "laboratorio_derivacion"
                ).get(id=tipo_examen_id)
                ResultadoExamen.objects.create(
                    solicitud=solicitud,
                    tipo_examen=tipo_examen,
                    valor_obtenido='',
                    es_patologico=False,
                    **defaults_derivacion_para_tipo(tipo_examen),
                )
                tipos_examen_creados.add(tipo_examen_id)
            except TipoExamen.DoesNotExist:
                logger.warning(f"TipoExamen con ID {tipo_examen_id} no existe")

        for panel_id in paneles_ids:
            try:
                panel = PanelExamen.objects.get(id=panel_id)
                tipos_examen_panel = ordenar_queryset_panel(panel)

                for tipo_examen in tipos_examen_panel:
                    if tipo_examen.id not in tipos_examen_creados:
                        te = TipoExamen.objects.select_related(
                            "laboratorio_derivacion"
                        ).get(pk=tipo_examen.id)
                        ResultadoExamen.objects.create(
                            solicitud=solicitud,
                            tipo_examen=te,
                            valor_obtenido='',
                            es_patologico=False,
                            **defaults_derivacion_para_tipo(te),
                        )
                        tipos_examen_creados.add(tipo_examen.id)
            except PanelExamen.DoesNotExist:
                logger.warning(f"PanelExamen con ID {panel_id} no existe")
            except TipoExamen.DoesNotExist:
                logger.warning("TipoExamen de panel inexistente")

        if tipos_examen_creados:
            solicitud.tipos_examen.set(list(tipos_examen_creados))

        return solicitud


class TomarMuestraItemSerializer(serializers.Serializer):
    """Ítem de toma física al marcar la orden en etapa de muestra."""

    tipo_muestra_id = serializers.IntegerField()
    tipo_contenedor_id = serializers.IntegerField(required=False, allow_null=True)
    observaciones = serializers.CharField(required=False, allow_blank=True, default="")


class TomarMuestraOrdenSerializer(serializers.Serializer):
    """Payload opcional para POST …/tomar-muestra/ (crear tubos/etiquetas; toma por escaneo)."""

    muestras = TomarMuestraItemSerializer(many=True, required=False, allow_empty=True)


class EnviarInformeOrdenSerializer(serializers.Serializer):
    """POST …/enviar-informe/ — canales de entrega al paciente y/o médico solicitante."""

    email = serializers.BooleanField(required=False, default=False)
    whatsapp = serializers.BooleanField(required=False, default=False)
    email_medico = serializers.BooleanField(required=False, default=False)
    whatsapp_medico = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        if not (
            attrs.get("email")
            or attrs.get("whatsapp")
            or attrs.get("email_medico")
            or attrs.get("whatsapp_medico")
        ):
            raise serializers.ValidationError(
                "Indique al menos un canal: email o whatsapp (paciente y/o médico)."
            )
        return attrs

