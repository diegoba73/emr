"""
Servicios de sincronización entre Atención/ConsultaAmbulatoria y Consulta (HC).

La Consulta de historias_clinicas es el eje documental: archivos, pedidos LIMS
y estudios complementarios se vinculan a ``consulta_hc``.
"""
from __future__ import annotations

from django.db import transaction

from historias_clinicas.models import Consulta, HistoriaClinica
from turnos.models import Atencion, ConsultaAmbulatoria


def _motivo_consulta_desde_atencion(atencion: Atencion) -> str:
    if atencion.contexto_atencion == Atencion.ContextoAtencion.INTERNACION:
        evo = getattr(atencion, 'evolucion_internacion', None)
        if evo is not None:
            return f'Internación — {evo.get_tipo_evolucion_display()}'
        return 'Internación — evolución clínica'
    if atencion.contexto_atencion == Atencion.ContextoAtencion.GUARDIA:
        return 'Guardia cardiológica'
    return 'Consulta médica'


def ensure_consulta_hc_desde_atencion(atencion: Atencion) -> Consulta:
    """Obtiene o crea la Consulta HC vinculada a una atención."""
    existing = (
        Consulta.objects.filter(atencion_id=atencion.pk).first()
        if atencion.pk
        else None
    )
    if existing is not None:
        return existing

    turno = atencion.turno
    if turno is not None:
        consulta = Consulta.objects.filter(turno_id=turno.pk).first()
        if consulta is not None:
            if not consulta.atencion_id:
                consulta.atencion = atencion
                consulta.save(update_fields=['atencion'])
            return consulta

    historia, _ = HistoriaClinica.objects.get_or_create(paciente=atencion.paciente)
    motivo = _motivo_consulta_desde_atencion(atencion)
    fecha = atencion.fecha_admision
    if turno is not None:
        motivo = turno.motivo_reserva or motivo
        fecha = turno.fecha_hora_inicio

    return Consulta.objects.create(
        historia_clinica=historia,
        medico=atencion.medico_principal,
        turno=turno,
        atencion=atencion,
        fecha_hora_consulta=fecha,
        motivo_consulta_detalle=motivo,
    )


def _notas_desde_ambulatoria(consulta_amb: ConsultaAmbulatoria) -> str:
    partes: list[str] = []
    if consulta_amb.antecedentes_relevantes:
        partes.append(f'Antecedentes: {consulta_amb.antecedentes_relevantes}')
    if consulta_amb.alergias:
        partes.append(f'Alergias: {consulta_amb.alergias}')
    if consulta_amb.medicacion_actual:
        partes.append(f'Medicación actual: {consulta_amb.medicacion_actual}')
    if consulta_amb.observaciones_medicas:
        partes.append(consulta_amb.observaciones_medicas)
    return '\n\n'.join(partes).strip()


@transaction.atomic
def sync_consulta_hc_desde_ambulatoria(consulta_amb: ConsultaAmbulatoria) -> Consulta | None:
    """Refleja el contenido clínico ambulatorio en la Consulta HC asociada."""
    atencion = consulta_amb.atencion
    if atencion.tipo_intervencion != Atencion.TipoIntervencion.CONSULTA:
        return None

    hc = ensure_consulta_hc_desde_atencion(atencion)

    if consulta_amb.anamnesis is not None:
        hc.anamnesis = consulta_amb.anamnesis
    if consulta_amb.examen_fisico is not None:
        hc.examen_fisico = consulta_amb.examen_fisico
    if consulta_amb.plan_manejo is not None:
        hc.plan_manejo = consulta_amb.plan_manejo

    dx = consulta_amb.diagnostico_definitivo or consulta_amb.diagnostico_presuntivo
    if dx:
        hc.diagnostico_presuntivo = dx

    notas = _notas_desde_ambulatoria(consulta_amb)
    if notas:
        hc.notas_medicas = notas

    if not hc.medico_id and atencion.medico_principal_id:
        hc.medico_id = atencion.medico_principal_id

    hc.save()
    return hc


def consulta_hc_id_para_atencion(atencion: Atencion) -> int | None:
    """Devuelve el id de Consulta HC para una atención, sin crear si no existe."""
    cid = (
        Consulta.objects.filter(atencion_id=atencion.pk)
        .values_list('pk', flat=True)
        .first()
    )
    if cid:
        return cid
    if atencion.turno_id:
        cid = (
            Consulta.objects.filter(turno_id=atencion.turno_id)
            .values_list('pk', flat=True)
            .first()
        )
        if cid:
            return cid
    return None
