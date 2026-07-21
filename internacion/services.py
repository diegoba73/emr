"""
Servicios de seguimiento clínico durante internación.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from turnos.models import Atencion, EvolucionInternacion

logger = logging.getLogger(__name__)


class InternacionClinicalError(Exception):
    """Error de lógica de negocio en evoluciones de internación."""


@dataclass(frozen=True)
class IniciarEvolucionOutcome:
    atencion: Atencion
    evolucion: EvolucionInternacion
    created_new: bool


class InternacionClinicalService:
    """Orquesta la creación de atenciones clínicas vinculadas a internación."""

    @staticmethod
    def _resolve_medico(medico, internacion):
        if medico is not None:
            return medico
        if internacion.medico_id:
            return internacion.medico
        raise InternacionClinicalError(
            'Debe indicar un médico responsable o asignar uno a la internación.'
        )

    @staticmethod
    def _validar_internacion_activa(internacion):
        if not internacion.activo:
            raise InternacionClinicalError(
                'No se puede registrar evolución en una internación dada de alta.'
            )

    @staticmethod
    def _existe_evolucion_diaria_hoy(internacion_id: int) -> bool:
        hoy = timezone.localdate()
        return EvolucionInternacion.objects.filter(
            atencion__internacion_id=internacion_id,
            tipo_evolucion=EvolucionInternacion.TipoEvolucion.EVOLUCION_DIARIA,
            fecha_evolucion__date=hoy,
        ).exists()

    @staticmethod
    @transaction.atomic
    def iniciar_evolucion_internacion(
        internacion,
        *,
        medico=None,
        tipo_evolucion: str = EvolucionInternacion.TipoEvolucion.EVOLUCION_DIARIA,
        observaciones_generales: str = '',
    ) -> IniciarEvolucionOutcome:
        from internacion.models import Internacion

        if not isinstance(internacion, Internacion):
            internacion = Internacion.objects.select_related(
                'paciente', 'medico', 'cama__sector'
            ).get(pk=internacion)

        InternacionClinicalService._validar_internacion_activa(internacion)
        medico_responsable = InternacionClinicalService._resolve_medico(medico, internacion)

        if tipo_evolucion == EvolucionInternacion.TipoEvolucion.EVOLUCION_DIARIA:
            if InternacionClinicalService._existe_evolucion_diaria_hoy(internacion.pk):
                raise InternacionClinicalError(
                    'Ya existe una evolución diaria registrada para hoy en esta internación.'
                )

        atencion = Atencion.objects.create(
            paciente=internacion.paciente,
            medico_principal=medico_responsable,
            contexto_atencion=Atencion.ContextoAtencion.INTERNACION,
            internacion=internacion,
            tipo_atencion=Atencion.TIPO_ATENCION_INTERNACION,
            tipo_intervencion=Atencion.TipoIntervencion.CONSULTA,
            estado_clinico=Atencion.EstadoClinico.ABIERTA,
            observaciones_generales=observaciones_generales or None,
        )
        evolucion = EvolucionInternacion.objects.create(
            atencion=atencion,
            tipo_evolucion=tipo_evolucion,
        )
        from historias_clinicas.services import ensure_consulta_hc_desde_atencion
        ensure_consulta_hc_desde_atencion(atencion)
        logger.info(
            'Evolución de internación creada: internacion=%s atencion=%s tipo=%s',
            internacion.pk,
            atencion.pk,
            tipo_evolucion,
        )
        return IniciarEvolucionOutcome(
            atencion=atencion,
            evolucion=evolucion,
            created_new=True,
        )

    @staticmethod
    def tiene_evolucion_diaria_hoy(internacion_id: int) -> bool:
        return InternacionClinicalService._existe_evolucion_diaria_hoy(internacion_id)
