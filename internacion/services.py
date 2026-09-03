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
    def _qs_evolucion_diaria_hoy(internacion_id: int):
        hoy = timezone.localdate()
        return EvolucionInternacion.objects.filter(
            atencion__internacion_id=internacion_id,
            tipo_evolucion=EvolucionInternacion.TipoEvolucion.EVOLUCION_DIARIA,
            fecha_evolucion__date=hoy,
        ).select_related('atencion', 'atencion__medico_principal')

    @staticmethod
    def _existe_evolucion_diaria_hoy(internacion_id: int) -> bool:
        return InternacionClinicalService._qs_evolucion_diaria_hoy(internacion_id).exists()

    @staticmethod
    def obtener_evolucion_diaria_hoy(internacion_id: int):
        return InternacionClinicalService._qs_evolucion_diaria_hoy(internacion_id).first()

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
            existente = InternacionClinicalService.obtener_evolucion_diaria_hoy(internacion.pk)
            if existente is not None:
                return IniciarEvolucionOutcome(
                    atencion=existente.atencion,
                    evolucion=existente,
                    created_new=False,
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

    @staticmethod
    def _serialize_evolucion(evo: EvolucionInternacion) -> dict:
        atencion = evo.atencion
        medico = getattr(atencion, 'medico_principal', None)
        medico_nombre = None
        if medico is not None:
            medico_nombre = f'{medico.apellido or ""}, {medico.nombre or ""}'.strip(', ')
        return {
            'atencion_id': atencion.pk,
            'estado_clinico': atencion.estado_clinico,
            'fecha_admision': atencion.fecha_admision.isoformat() if atencion.fecha_admision else None,
            'medico_nombre': medico_nombre or None,
            'tipo_evolucion': evo.tipo_evolucion,
            'tipo_evolucion_display': evo.get_tipo_evolucion_display(),
            'fecha_evolucion': evo.fecha_evolucion.isoformat() if evo.fecha_evolucion else None,
            'subjetivo': evo.subjetivo,
            'objetivo': evo.objetivo,
            'analisis': evo.analisis,
            'plan': evo.plan,
            'signos_vitales_resumen': evo.signos_vitales_resumen,
            'diagnostico_actualizado': evo.diagnostico_actualizado,
            'plan_manejo': evo.plan_manejo,
            'observaciones': evo.observaciones,
        }

    @staticmethod
    def construir_contexto_revista(internacion) -> dict:
        """Insumos de revista de sala: evoluciones SOAP, labs y estudios del episodio."""
        from django.db.models import Q
        from estudios.models import EstudioComplementario
        from laboratorio.models import SolicitudExamen
        from laboratorio.origen_solicitud import (
            AMBULATORIO_CEHTA,
            AMBULATORIO_ICPL,
            EXTERNO_CEHTA,
            EXTERNO_ICPL,
        )

        hoy = timezone.localdate()
        inicio = internacion.fecha_ingreso
        fin = internacion.fecha_alta
        paciente_id = internacion.paciente_id

        evoluciones_qs = (
            EvolucionInternacion.objects.filter(atencion__internacion_id=internacion.pk)
            .select_related('atencion', 'atencion__medico_principal')
            .order_by('-fecha_evolucion', '-atencion_id')
        )
        evoluciones = [InternacionClinicalService._serialize_evolucion(e) for e in evoluciones_qs]
        evo_hoy = InternacionClinicalService.obtener_evolucion_diaria_hoy(internacion.pk)

        origenes_no_internacion = {
            AMBULATORIO_CEHTA,
            AMBULATORIO_ICPL,
            EXTERNO_CEHTA,
            EXTERNO_ICPL,
        }
        lab_qs = (
            SolicitudExamen.objects.filter(paciente_id=paciente_id, fecha_solicitud__gte=inicio)
            .exclude(origen_solicitud__in=origenes_no_internacion)
            .prefetch_related('tipos_examen', 'paneles', 'resultados__tipo_examen')
            .order_by('-fecha_solicitud')
        )
        if fin:
            lab_qs = lab_qs.filter(fecha_solicitud__lte=fin)

        estados_con_resultado = {'INFORMADO_PARCIAL', 'LISTO_PARA_VALIDAR', 'FINALIZADO'}
        laboratorio = []
        for sol in lab_qs:
            fecha = sol.fecha_solicitud
            fecha_local = timezone.localtime(fecha).date() if fecha else None
            examenes = list(sol.tipos_examen.values_list('nombre', flat=True))
            paneles = list(sol.paneles.values_list('nombre', flat=True))
            resultados = []
            for res in sol.resultados.all():
                if not (res.valor_obtenido or '').strip():
                    continue
                tipo = getattr(res, 'tipo_examen', None)
                resultados.append({
                    'id': res.pk,
                    'examen': tipo.nombre if tipo else None,
                    'valor': res.valor_obtenido,
                    'unidad': res.unidad or '',
                    'es_patologico': bool(res.es_patologico),
                })
            laboratorio.append({
                'id': sol.pk,
                'numero': sol.numero,
                'estado': sol.estado,
                'fecha_solicitud': fecha.isoformat() if fecha else None,
                'es_de_hoy': fecha_local == hoy,
                'tiene_resultados': sol.estado in estados_con_resultado or bool(resultados),
                'examenes': examenes,
                'paneles': paneles,
                'resultados': resultados,
            })

        est_filter = Q(paciente_id=paciente_id)
        if inicio:
            est_filter &= Q(fecha_solicitud__gte=inicio) | Q(
                fecha_solicitud__isnull=True, created_at__gte=inicio
            )
        if fin:
            est_filter &= Q(fecha_solicitud__lte=fin) | Q(
                fecha_solicitud__isnull=True, created_at__lte=fin
            )
        est_qs = (
            EstudioComplementario.objects.filter(est_filter)
            .select_related('tipo_estudio')
            .order_by('-fecha_solicitud', '-id')
        )

        estudios = []
        for est in est_qs:
            fecha_sol = est.fecha_solicitud or getattr(est, 'created_at', None)
            tipo = est.tipo_estudio
            estudios.append({
                'id': est.pk,
                'estado': est.estado,
                'modalidad': est.modalidad,
                'tipo_nombre': tipo.nombre if tipo else None,
                'fecha_solicitud': fecha_sol.isoformat() if fecha_sol else None,
                'fecha_realizacion': est.fecha_realizacion.isoformat() if est.fecha_realizacion else None,
            })

        diagnostico = None
        cie = internacion.diagnostico_cie
        if cie is not None:
            diagnostico = f'{cie.codigo} - {cie.descripcion}'
        else:
            diagnostico = internacion.diagnostico_ingreso or None

        dieta_obj = internacion.tipo_dieta
        dieta = dieta_obj.nombre if dieta_obj is not None else None
        dias = None
        if internacion.fecha_ingreso:
            delta = (fin or timezone.now()) - internacion.fecha_ingreso
            dias = max(delta.days, 0)

        def _reg(obj, extra: dict):
            user = obj.registrado_por
            nombre = None
            if user:
                nombre = f'{user.last_name or ""}, {user.first_name or ""}'.strip(', ') or user.username
            payload = {
                'id': obj.pk,
                'fecha': obj.fecha.isoformat() if obj.fecha else None,
                'registrado_por_nombre': nombre,
            }
            payload.update(extra)
            return payload

        hc = {
            'alergias': internacion.alergias or '',
            'anamnesis_ingreso': internacion.anamnesis_ingreso or '',
            'examen_fisico_ingreso': internacion.examen_fisico_ingreso or '',
            'medicacion_habitual': internacion.medicacion_habitual or '',
            'indicaciones': [
                _reg(x, {'indicaciones': x.indicaciones, 'vigente': x.vigente})
                for x in internacion.indicaciones_medicas.select_related('registrado_por').all()[:30]
            ],
            'medicaciones': [
                _reg(x, {'medicamento': x.medicamento, 'dosis': x.dosis, 'activa': x.activa})
                for x in internacion.medicaciones.select_related('registrado_por').all()[:40]
            ],
            'controles_enfermeria': [
                _reg(x, {'turno': x.turno, 'tension_arterial': x.tension_arterial})
                for x in internacion.controles_enfermeria.select_related('registrado_por').all()[:40]
            ],
            'balances_hidricos': [
                _reg(x, {'turno': x.turno})
                for x in internacion.balances_hidricos.select_related('registrado_por').all()[:40]
            ],
            'notas_enfermeria': [
                _reg(x, {'observaciones': (x.observaciones or '')[:240]})
                for x in internacion.notas_enfermeria.select_related('registrado_por').all()[:40]
            ],
            'kinesiologia': [
                _reg(x, {'evolucion': (x.evolucion or '')[:240]})
                for x in internacion.registros_kinesiologia.select_related('registrado_por').all()[:40]
            ],
        }

        return {
            'internacion_id': internacion.pk,
            'paciente_id': paciente_id,
            'fecha_ingreso': internacion.fecha_ingreso.isoformat() if internacion.fecha_ingreso else None,
            'diagnostico': diagnostico,
            'tipo_dieta': dieta,
            'dias_internacion': dias,
            'evolucion_hoy': InternacionClinicalService._serialize_evolucion(evo_hoy) if evo_hoy else None,
            'evoluciones': evoluciones,
            'laboratorio': laboratorio,
            'estudios': estudios,
            'hc': hc,
        }
