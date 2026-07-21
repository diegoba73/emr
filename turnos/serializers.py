"""
Serializers para la app turnos.
"""
from __future__ import annotations

import logging
from typing import Optional
from rest_framework import serializers
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import (
    Turno,
    Recurso,
    Atencion,
    ConsultaAmbulatoria,
    EvolucionInternacion,
    RegistroProcedimiento,
    RegistroQuirurgico,
)
from pacientes.models import Paciente
from pacientes.serializers import PacienteLightSerializer
from medicos.models import Medico
from api.serializers import MedicoSerializer

logger = logging.getLogger(__name__)

# Turnos agendados a un paciente; DISPONIBLE puede existir sin paciente (slot libre).
_ESTADOS_REQUIEREN_PACIENTE = frozenset({
    Turno.Estado.RESERVADO,
    Turno.Estado.CONFIRMADO,
    Turno.Estado.REALIZADO,
})

# Campos de texto de consulta que cuentan como "cargada" (no vacía) para el turno
_CONSULTA_CONTENIDO_FIELDS = (
    "anamnesis",
    "examen_fisico",
    "diagnostico_presuntivo",
    "plan_manejo",
    "antecedentes_relevantes",
    "alergias",
    "medicacion_actual",
    "diagnostico_definitivo",
    "observaciones_medicas",
)


def consulta_ambulatoria_tiene_contenido(consulta: Optional[ConsultaAmbulatoria]) -> bool:
    """True si la consulta ambulatoria tiene al menos un campo de texto con contenido."""
    if not consulta:
        return False
    for name in _CONSULTA_CONTENIDO_FIELDS:
        val = getattr(consulta, name, None)
        if val is not None and str(val).strip():
            return True
    return False


def turno_tiene_consulta_cargada(turno: Turno) -> bool:
    """Indica si el turno ya tiene atención con consulta ambulatoria con contenido."""
    try:
        at = turno.atencion
    except Atencion.DoesNotExist:
        return False
    try:
        return consulta_ambulatoria_tiene_contenido(at.consulta_ambulatoria)
    except ConsultaAmbulatoria.DoesNotExist:
        return False


def _mismo_momento(a, b) -> bool:
    """
    Mismo instante; tolera redondeo JSON/DB y naïve vs aware (hasta 120 s).
    """
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    try:

        def to_ts(x):
            if timezone.is_aware(x):
                return x.timestamp()
            return timezone.make_aware(
                x, timezone.get_current_timezone()
            ).timestamp()

        return abs(to_ts(a) - to_ts(b)) < 120.0
    except Exception:  # pragma: no cover
        return a == b


class RecursoSerializer(serializers.ModelSerializer):
    """Serializer para Recurso."""
    tipo_recurso_display = serializers.CharField(
        source='get_tipo_recurso_display',
        read_only=True,
    )

    class Meta:
        model = Recurso
        fields = [
            'id',
            'nombre',
            'ubicacion',
            'tipo_recurso',
            'tipo_recurso_display',
            'activo',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class TurnoSerializer(serializers.ModelSerializer):
    """
    Serializer para Turno implementando patrón Read-Nested / Write-ID.
    
    - Lectura: Paciente liviano (``PacienteLightSerializer``); médico y recurso anidados
    - Escritura: Acepta IDs (paciente_id, medico_id, recurso_id)
    Incluye validación de solapamiento y campos calculados.
    """
    # ============================================================
    # CAMPOS DE LECTURA (read_only=True) - Objetos anidados
    # ============================================================
    paciente = PacienteLightSerializer(
        read_only=True,
        allow_null=True,
        help_text="Identificación mínima del paciente (solo lectura)",
    )
    medico = MedicoSerializer(
        read_only=True,
        allow_null=True,
        help_text="Objeto completo del médico (solo lectura)"
    )
    recurso = RecursoSerializer(
        read_only=True,
        allow_null=True,
        help_text="Objeto completo del recurso (solo lectura)"
    )
    
    # Campos auxiliares de lectura para compatibilidad
    paciente_nombre = serializers.CharField(
        source='paciente.nombre_completo',
        read_only=True,
        help_text="Nombre completo del paciente (solo lectura)"
    )
    medico_nombre = serializers.CharField(
        source='medico.nombre_completo',
        read_only=True,
        help_text="Nombre completo del médico (solo lectura)"
    )
    recurso_nombre = serializers.CharField(
        source='recurso.nombre',
        read_only=True,
        help_text="Nombre del recurso (solo lectura)"
    )
    
    # ============================================================
    # CAMPOS DE ESCRITURA (write_only=True) - IDs
    # ============================================================
    paciente_id = serializers.PrimaryKeyRelatedField(
        queryset=Paciente.objects.all(),
        source='paciente',
        write_only=True,
        required=False,
        allow_null=True,
        help_text="ID del paciente (solo escritura)"
    )
    medico_id = serializers.PrimaryKeyRelatedField(
        queryset=Medico.objects.all(),
        source='medico',
        write_only=True,
        required=False,
        allow_null=True,
        help_text="ID del médico (solo escritura)"
    )
    recurso_id = serializers.PrimaryKeyRelatedField(
        queryset=Recurso.objects.all(),
        source='recurso',
        write_only=True,
        required=False,
        allow_null=True,
        help_text="ID del recurso (solo escritura)"
    )

    atencion = serializers.SerializerMethodField(
        read_only=True,
        help_text="Resumen de la atención vinculada (si existe), para el calendario y el modal de turno",
    )
    estudio_complementario = serializers.SerializerMethodField(
        read_only=True,
        help_text="Estudio complementario vinculado al turno (agenda de estudios)",
    )

    class Meta:
        model = Turno
        fields = [
            'id',
            # Campos de lectura (objetos anidados)
            'paciente',
            'medico',
            'recurso',
            # Campos auxiliares de lectura
            'paciente_nombre',
            'medico_nombre',
            'recurso_nombre',
            'atencion',
            'estudio_complementario',
            # Campos de escritura (IDs)
            'paciente_id',
            'medico_id',
            'recurso_id',
            # Campos del modelo
            'fecha_hora_inicio',
            'fecha_hora_fin',
            'estado',
            'motivo_reserva',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'paciente',
            'medico',
            'recurso',
            'paciente_nombre',
            'medico_nombre',
            'recurso_nombre',
            'atencion',
            'estudio_complementario',
            'created_at',
            'updated_at',
        ]

    def get_atencion(self, obj: Turno):
        if not obj:
            return None
        try:
            at = obj.atencion
        except Atencion.DoesNotExist:
            return None
        result: dict = {
            "id": at.id,
            "fecha_admision": at.fecha_admision,
            "tipo_atencion": at.tipo_atencion,
            "tipo_intervencion": at.tipo_intervencion,
            "estado_clinico": at.estado_clinico,
        }
        try:
            ca = at.consulta_ambulatoria
            # ConsultaAmbulatoria tiene PK = atencion (no existe atributo .id)
            result["consulta_ambulatoria"] = {"id": ca.pk}
            result["consulta_cargada"] = consulta_ambulatoria_tiene_contenido(ca)
        except ConsultaAmbulatoria.DoesNotExist:
            result["consulta_cargada"] = False
        try:
            rp = at.registro_procedimiento
            if rp:
                # RegistroProcedimiento tiene PK = atencion (no existe atributo .id)
                result["registro_procedimiento"] = {"id": rp.pk}
        except RegistroProcedimiento.DoesNotExist:
            pass
        try:
            rq = at.registro_quirurgico
            if rq:
                # RegistroQuirurgico tiene PK = atencion (no existe atributo .id)
                result["registro_quirurgico"] = {"id": rq.pk}
        except RegistroQuirurgico.DoesNotExist:
            pass
        return result

    def get_estudio_complementario(self, obj: Turno):
        try:
            ec = obj.estudio_complementario
        except Exception:
            return None
        if ec is None:
            return None
        tipo_nombre = None
        if ec.tipo_estudio_id:
            tipo_nombre = getattr(ec.tipo_estudio, 'nombre', None)
        med_sol_id = ec.medico_solicitante_id
        return {
            'id': ec.id,
            'estado': ec.estado,
            'modalidad': ec.modalidad,
            'tipo_estudio_nombre': tipo_nombre,
            'medico_solicitante_id': med_sol_id,
        }

    def validate(self, attrs):
        """
        Validación crítica:
        1. Lógica de Fechas: fecha_hora_fin > fecha_hora_inicio
        2. Si turno finalizado o consulta con contenido: no permitir *cambios* a fechas, médico, paciente, recurso
        3. Solapamiento: estados RESERVADO/CONFIRMADO, médico, rango [inicio, fin] efectivo

        En PATCH parcial, los campos faltantes se toman de la instancia.
        """
        inst = self.instance

        inicio = attrs["fecha_hora_inicio"] if "fecha_hora_inicio" in attrs else (inst and inst.fecha_hora_inicio)
        fin = attrs["fecha_hora_fin"] if "fecha_hora_fin" in attrs else (inst and inst.fecha_hora_fin)
        medico = attrs["medico"] if "medico" in attrs else (inst and inst.medico)
        estado = attrs["estado"] if "estado" in attrs else (inst and inst.estado) or Turno.Estado.DISPONIBLE
        paciente = attrs["paciente"] if "paciente" in attrs else (inst and inst.paciente)
        recurso = attrs["recurso"] if "recurso" in attrs else (inst and inst.recurso)

        if fin and inicio and fin <= inicio:
            raise serializers.ValidationError({
                "fecha_hora_fin": "La fecha/hora de fin debe ser posterior a la fecha/hora de inicio."
            })

        if estado in _ESTADOS_REQUIEREN_PACIENTE and not paciente:
            raise serializers.ValidationError({
                "paciente_id": (
                    "El paciente es obligatorio para turnos reservados, confirmados o realizados."
                ),
            })

        if inst is not None and (
            inst.estado == Turno.Estado.REALIZADO or turno_tiene_consulta_cargada(inst)
        ):
            msg = (
                "No se puede modificar el horario, el médico, el paciente o el recurso: "
                "el turno está finalizado o la consulta ya fue cargada con contenido."
            )
            if "fecha_hora_inicio" in attrs and not _mismo_momento(
                attrs["fecha_hora_inicio"], inst.fecha_hora_inicio
            ):
                raise serializers.ValidationError({"fecha_hora_inicio": msg})
            if "fecha_hora_fin" in attrs and not _mismo_momento(
                attrs.get("fecha_hora_fin"), inst.fecha_hora_fin
            ):
                raise serializers.ValidationError({"fecha_hora_fin": msg})
            if "medico" in attrs:
                nuevo_mid = medico.id if medico else None
                if nuevo_mid != inst.medico_id:
                    raise serializers.ValidationError({"medico_id": msg})
            if "paciente" in attrs:
                nuevo_pid = paciente.id if paciente else None
                if nuevo_pid != inst.paciente_id:
                    raise serializers.ValidationError({"paciente_id": msg})
            if "recurso" in attrs:
                nuevo_rid = recurso.id if recurso else None
                if nuevo_rid != inst.recurso_id:
                    raise serializers.ValidationError({"recurso_id": msg})

        if medico and inicio and estado in [Turno.Estado.CONFIRMADO, Turno.Estado.RESERVADO]:
            turnos_solapados = Turno.objects.filter(
                medico=medico,
                estado__in=[Turno.Estado.CONFIRMADO, Turno.Estado.RESERVADO],
            )
            if inst:
                turnos_solapados = turnos_solapados.exclude(id=inst.id)
            if fin:
                solapados = turnos_solapados.filter(
                    fecha_hora_inicio__lt=fin,
                    fecha_hora_fin__gt=inicio,
                )
            else:
                solapados = turnos_solapados.filter(
                    fecha_hora_inicio__lte=inicio,
                    fecha_hora_fin__gte=inicio,
                )
            if solapados.exists():
                turno_solapado = solapados.first()
                logger.warning(
                    "Intento de crear turno solapado: Médico=%s Inicio=%s Fin=%s existente_id=%s",
                    medico.id,
                    inicio,
                    fin,
                    turno_solapado.id,
                )
                raise serializers.ValidationError({
                    "fecha_hora_inicio": f"Ya existe un turno {turno_solapado.get_estado_display()} "
                    f"para este médico en el rango horario especificado. "
                    f"Turno existente: {turno_solapado.fecha_hora_inicio} - {turno_solapado.fecha_hora_fin}"
                })

        return attrs


class AtencionSerializer(serializers.ModelSerializer):
    """
    Serializer para Atencion.
    Incluye datos del paciente y médico para display.
    """
    paciente_nombre = serializers.CharField(
        source='paciente.nombre_completo',
        read_only=True
    )
    medico_nombre = serializers.CharField(
        source='medico_principal.nombre_completo',
        read_only=True
    )
    turno_id = serializers.IntegerField(
        source='turno.id',
        read_only=True
    )
    
    # Campos de escritura (IDs) con queryset explícito
    paciente = serializers.PrimaryKeyRelatedField(
        queryset=Paciente.objects.all(),
        help_text="ID del paciente"
    )
    medico_principal = serializers.PrimaryKeyRelatedField(
        queryset=Medico.objects.all(),
        help_text="ID del médico principal"
    )
    turno = serializers.PrimaryKeyRelatedField(
        queryset=Turno.objects.all(),
        required=False,
        allow_null=True,
        help_text="ID del turno asociado"
    )

    class Meta:
        model = Atencion
        fields = [
            'id',
            'turno',
            'turno_id',
            'paciente',
            'paciente_nombre',
            'medico_principal',
            'medico_nombre',
            'fecha_admision',
            'fecha_cierre',
            'tipo_atencion',
            'tipo_intervencion',
            'estado_clinico',
            'observaciones_generales',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'fecha_admision',
            'created_at',
            'updated_at',
            'paciente_nombre',
            'medico_nombre',
            'turno_id',
        ]


def _sync_hc_after_ambulatoria_save(instance: ConsultaAmbulatoria) -> None:
    from historias_clinicas.services import sync_consulta_hc_desde_ambulatoria
    sync_consulta_hc_desde_ambulatoria(instance)


class ConsultaAmbulatoriaSerializer(serializers.ModelSerializer):
    """
    Serializer para ConsultaAmbulatoria.
    Permite crear y actualizar consultas ambulatorias asociadas a una Atencion.
    El campo 'atencion' se establece desde el contexto o en el método save().
    """
    atencion = serializers.PrimaryKeyRelatedField(
        queryset=Atencion.objects.all(),
        read_only=False,
        required=False,
        help_text="ID de la atención asociada"
    )
    
    class Meta:
        model = ConsultaAmbulatoria
        fields = [
            'atencion',
            'anamnesis',
            'examen_fisico',
            'diagnostico_presuntivo',
            'plan_manejo',
            'antecedentes_relevantes',
            'alergias',
            'medicacion_actual',
            'diagnostico_definitivo',
            'observaciones_medicas',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'created_at',
            'updated_at',
        ]
    
    def validate(self, attrs):
        """
        Validación de reglas de negocio:
        - Si el estado de la atención es FINALIZADA, anamnesis es obligatoria
        - Si se proporciona atencion en el contexto, validar que no esté cerrada
        """
        atencion = self.context.get('atencion')
        
        # Si la atención viene del contexto, validar reglas adicionales
        if atencion:
            # Si la atención está cerrada, no se puede editar
            if atencion.fecha_cierre:
                raise serializers.ValidationError({
                    'atencion': 'No se puede editar una consulta de una atención ya cerrada.'
                })
            
            # Si el estado clínico es FINALIZADA, anamnesis es obligatoria
            if atencion.estado_clinico == Atencion.EstadoClinico.FINALIZADA:
                anamnesis = attrs.get('anamnesis') or (self.instance.anamnesis if self.instance else None)
                if not anamnesis or not anamnesis.strip():
                    raise serializers.ValidationError({
                        'anamnesis': 'La anamnesis es obligatoria cuando la atención está finalizada.'
                    })
        
        return attrs
    
    def save(self, **kwargs):
        """
        Sobrescribe save() para aceptar atencion como parámetro.
        Esto permite que el view pase la atención desde el contexto.
        """
        atencion = kwargs.pop('atencion', None) or self.context.get('atencion')
        
        if atencion:
            # Si es una creación (no hay instance), establecer atencion
            if not self.instance:
                kwargs['atencion'] = atencion
            # Si es una actualización, asegurar que la atencion coincida
            elif self.instance.atencion != atencion:
                raise serializers.ValidationError({
                    'atencion': 'No se puede cambiar la atención asociada a una consulta existente.'
                })
        
        instance = super().save(**kwargs)
        _sync_hc_after_ambulatoria_save(instance)
        return instance


class EvolucionInternacionSerializer(serializers.ModelSerializer):
    """Serializer para evoluciones clínicas durante internación."""

    atencion_id = serializers.IntegerField(source='atencion.id', read_only=True)
    id = serializers.IntegerField(source='atencion_id', read_only=True)
    tipo_evolucion_display = serializers.CharField(
        source='get_tipo_evolucion_display',
        read_only=True,
    )

    class Meta:
        model = EvolucionInternacion
        fields = [
            'id',
            'atencion_id',
            'tipo_evolucion',
            'tipo_evolucion_display',
            'fecha_evolucion',
            'subjetivo',
            'objetivo',
            'analisis',
            'plan',
            'signos_vitales_resumen',
            'diagnostico_actualizado',
            'plan_manejo',
            'observaciones',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['fecha_evolucion', 'created_at', 'updated_at']

    def validate(self, attrs):
        atencion = self.context.get('atencion') or getattr(self.instance, 'atencion', None)
        if atencion and atencion.fecha_cierre:
            raise serializers.ValidationError({
                'atencion': 'No se puede editar una evolución de una atención ya cerrada.',
            })
        if atencion and atencion.contexto_atencion != Atencion.ContextoAtencion.INTERNACION:
            raise serializers.ValidationError({
                'atencion': 'La atención no corresponde a un contexto de internación.',
            })
        return attrs

