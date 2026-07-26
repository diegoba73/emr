"""
Agregador de línea de tiempo clínica por paciente.

Fuente operacional: Atencion (+ hijos). Internación de camas: internacion.Internacion.
Deduplica Consulta HC cuando ya hay Atencion vinculada.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from django.utils import timezone


def _iso(dt) -> str | None:
    if dt is None:
        return None
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt.isoformat()


def _parse_sort_key(iso_or_dt) -> datetime:
    if iso_or_dt is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if isinstance(iso_or_dt, datetime):
        dt = iso_or_dt
        if timezone.is_naive(dt):
            return timezone.make_aware(dt, timezone.get_current_timezone())
        return dt
    try:
        return datetime.fromisoformat(str(iso_or_dt).replace('Z', '+00:00'))
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)


def build_paciente_timeline(paciente_id: int, user=None) -> list[dict[str, Any]]:
    """Construye eventos normalizados para Patient 360 / portal.

    Si se pasa ``user``, los eventos LIMS se filtran con la misma regla de
    lectura que ``GET /api/lab/solicitudes/{id}/`` (p. ej. médico: solo
    órdenes con ``medico_interno.user`` = usuario). Evita enlaces rotos
    desde la timeline.
    """
    from turnos.models import Atencion, Turno
    from historias_clinicas.models import Consulta
    from internacion.models import Internacion

    events: list[dict[str, Any]] = []

    # --- Turnos ---
    for t in Turno.objects.filter(paciente_id=paciente_id).select_related('recurso'):
        start = t.fecha_hora_inicio
        if not start:
            continue
        events.append({
            'id': f'turno-{t.id}',
            'type': 'turno',
            'title': f'Turno ambulatorio ({t.estado})',
            'subtitle': t.motivo_reserva or (t.recurso.nombre if t.recurso_id else None),
            'date': _iso(start),
            'critical': t.estado == 'CANCELADO',
            'navigate_to': '/turnos',
            'meta': {'turno_id': t.id, 'estado': t.estado},
        })

    # --- Internaciones (camas = SoT) ---
    internaciones = list(
        Internacion.objects.filter(paciente_id=paciente_id)
        .select_related('cama', 'cama__sector')
        .order_by('-fecha_ingreso')
    )
    internacion_ids = {i.id for i in internaciones}

    for internacion in internaciones:
        group_id = f'internacion-{internacion.id}'
        sector_label = (
            internacion.cama.nombre if internacion.cama_id else f'Internación #{internacion.id}'
        )
        events.append({
            'id': f'int-ingreso-{internacion.id}',
            'type': 'internacion_ingreso',
            'title': f'Ingreso — {internacion.numero_internacion or group_id}',
            'subtitle': internacion.diagnostico_ingreso or internacion.motivo_ingreso or sector_label,
            'date': _iso(internacion.fecha_ingreso),
            'episode_group_id': group_id,
            'episode_group_title': f'Episodio de internación · {sector_label}',
            'navigate_to': '/internacion',
            'meta': {'internacion_id': internacion.id},
        })
        if internacion.fecha_alta:
            events.append({
                'id': f'int-alta-{internacion.id}',
                'type': 'internacion_alta',
                'title': 'Alta médica',
                'subtitle': internacion.numero_internacion or None,
                'date': _iso(internacion.fecha_alta),
                'episode_group_id': group_id,
                'nested': True,
                'navigate_to': '/internacion',
                'meta': {'internacion_id': internacion.id},
            })

    # --- Atenciones (hub operacional) ---
    atenciones = (
        Atencion.objects.filter(paciente_id=paciente_id)
        .select_related('evolucion_internacion')
        .prefetch_related('signos_vitales')
    )
    atencion_ids_con_hc: set[int] = set()

    for a in atenciones:
        d = a.fecha_admision
        if not d:
            continue
        consulta_hc_id = None
        try:
            from historias_clinicas.services import consulta_hc_id_para_atencion
            consulta_hc_id = consulta_hc_id_para_atencion(a)
            if consulta_hc_id:
                atencion_ids_con_hc.add(a.id)
        except Exception:
            pass

        is_internacion = (
            a.contexto_atencion == Atencion.ContextoAtencion.INTERNACION
            or bool(a.internacion_id)
        )
        if is_internacion and a.internacion_id and a.internacion_id in internacion_ids:
            evo = getattr(a, 'evolucion_internacion', None)
            tipo_evo = (
                evo.get_tipo_evolucion_display()
                if evo is not None
                else 'Evolución'
            )
            fecha_evo = evo.fecha_evolucion if evo is not None else d
            events.append({
                'id': f'atencion-{a.id}',
                'type': 'internacion_evolucion',
                'title': tipo_evo,
                'subtitle': f'Estado: {a.estado_clinico}' if a.estado_clinico else None,
                'date': _iso(fecha_evo),
                'episode_group_id': f'internacion-{a.internacion_id}',
                'nested': True,
                'critical': a.estado_clinico == 'ABIERTA',
                'atencion_id': a.id,
                'consulta_hc_id': consulta_hc_id,
                'navigate_to': '/atenciones',
                'meta': {'openAtencionId': a.id},
            })
            continue

        tipo = a.tipo_intervencion or 'CONSULTA'
        is_guardia = a.contexto_atencion == Atencion.ContextoAtencion.GUARDIA
        if is_guardia:
            ttype = 'guardia'
            title = 'Atención de guardia'
        elif tipo == 'ESTUDIO':
            ttype = 'estudio'
            title = 'Estudio / procedimiento diagnóstico'
        elif tipo == 'PROCEDIMIENTO':
            ttype = 'procedimiento'
            title = 'Procedimiento'
        elif tipo == 'CIRUGIA':
            ttype = 'procedimiento'
            title = 'Cirugía'
        else:
            ttype = 'consulta'
            title = 'Consulta ambulatoria'

        events.append({
            'id': f'atencion-{a.id}',
            'type': ttype,
            'title': title,
            'subtitle': a.estado_clinico,
            'date': _iso(d),
            'critical': a.estado_clinico == 'ABIERTA',
            'atencion_id': a.id,
            'consulta_hc_id': consulta_hc_id,
            'navigate_to': '/atenciones',
            'meta': {'openAtencionId': a.id},
        })

    # --- Consultas HC sin atención vinculada (legacy / longitudinal only) ---
    consultas = (
        Consulta.objects.filter(historia_clinica_id=paciente_id)
        .select_related('medico')
    )
    for c in consultas:
        if c.atencion_id and c.atencion_id in atencion_ids_con_hc:
            continue
        if c.atencion_id:
            # Ya representada por atención aunque no estuviera en set
            continue
        events.append({
            'id': f'consulta-hc-{c.id}',
            'type': 'consulta',
            'title': 'Consulta (historia clínica)',
            'subtitle': (c.motivo_consulta_detalle or '')[:120] or None,
            'date': _iso(c.fecha_hora_consulta),
            'consulta_hc_id': c.id,
            'navigate_to': '/atenciones',
            'meta': {'consulta_hc_id': c.id},
        })

    # --- Órdenes LIMS (visibles según permiso de lectura del rol) ---
    try:
        from api.permissions import usuario_puede_ver_solicitud_lims
        from laboratorio.models import SolicitudExamen

        lab_qs = SolicitudExamen.objects.filter(paciente_id=paciente_id).select_related(
            'medico_interno', 'paciente'
        )
        for s in lab_qs:
            if user is not None and not usuario_puede_ver_solicitud_lims(user, s):
                continue
            events.append({
                'id': f'lab-{s.id}',
                'type': 'solicitud',
                'title': f'Laboratorio {s.numero or s.id}',
                'subtitle': s.estado,
                'date': _iso(s.fecha_solicitud),
                'navigate_to': f'/solicitudes/{s.id}',
                'meta': {'solicitud_examen_id': s.id},
            })
    except Exception:
        pass

    # --- Estudios complementarios ---
    try:
        from estudios.models import EstudioComplementario
        for e in EstudioComplementario.objects.filter(paciente_id=paciente_id).only(
            'id', 'estado', 'fecha_solicitud', 'modalidad'
        ):
            events.append({
                'id': f'estudio-comp-{e.id}',
                'type': 'estudio',
                'title': f'Estudio complementario ({e.modalidad or "IMG"})',
                'subtitle': e.estado,
                'date': _iso(getattr(e, 'fecha_solicitud', None) or getattr(e, 'created_at', None)),
                'navigate_to': f'/estudios-complementarios/{e.id}',
                'meta': {'estudio_id': e.id},
            })
    except Exception:
        pass

    # --- Archivos médicos ---
    try:
        from archivos_medicos.models import ArchivoMedico
        for ar in ArchivoMedico.objects.filter(paciente_id=paciente_id).only(
            'id', 'titulo', 'tipo_archivo', 'fecha_carga', 'created_at'
        )[:50]:
            fecha = getattr(ar, 'fecha_carga', None) or getattr(ar, 'created_at', None)
            events.append({
                'id': f'archivo-{ar.id}',
                'type': 'otro',
                'title': ar.titulo or 'Archivo médico',
                'subtitle': ar.tipo_archivo,
                'date': _iso(fecha),
                'navigate_to': '/archivos',
                'meta': {'archivo_id': ar.id},
            })
    except Exception:
        pass

    events.sort(key=lambda e: _parse_sort_key(e.get('date')), reverse=True)
    return events
