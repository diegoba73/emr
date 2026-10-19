"""D — realización de CIRUGIA: Atencion + RegistroQuirurgico (siempre).

Sin turno ficticio. Requiere profesional, anestesista real y diagnóstico preoperatorio.
Protocolo canónico = InformeEstudioComplementario (proyección; vacía al acto).
"""
from __future__ import annotations

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction

from estudios.actividad_rules import MSG_ATENCION_INCOMPATIBLE

MSG_RECURSO_CIRUGIA = (
    'Indique quirófano o sala de hemodinamia para registrar la cirugía '
    '(sin inventar un turno).'
)
MSG_RECURSO_TIPO = 'El recurso debe ser quirófano o sala de hemodinamia.'
MSG_ANESTESISTA = (
    'Indique el anestesista real (obligatorio; no se admite No aplica ni placeholders).'
)
MSG_DX_PRE = 'El diagnóstico preoperatorio es obligatorio (texto real, sin relleno).'


def _tiene_hijo(atencion, related_name: str) -> bool:
    try:
        getattr(atencion, related_name)
        return True
    except ObjectDoesNotExist:
        return False
    except AttributeError:
        return False


def atencion_compatible_con_cirugia(atencion) -> bool:
    if _tiene_hijo(atencion, 'registro_procedimiento'):
        return False
    if _tiene_hijo(atencion, 'consulta_ambulatoria'):
        return False
    if _tiene_hijo(atencion, 'evolucion_internacion'):
        return False
    return True


def _recurso_admitido_cirugia(recurso) -> bool:
    from turnos.models import Recurso

    return recurso.tipo_recurso in (
        Recurso.TipoRecurso.QUIROFANO,
        Recurso.TipoRecurso.SALA_HEMODINAMIA,
    )


@transaction.atomic
def ensure_atencion_y_registro_quirurgico(
    *,
    estudio,
    sesion,
    medico,
    anestesista,
    diagnostico_preoperatorio: str,
    recurso=None,
    actor=None,
):
    """Crea/reutiliza Atencion + RegistroQuirurgico. Siempre exige ambos.

    Con turno: usa sala del turno si no se pasa recurso.
    Sin turno: exige recurso quirófano/hemodinamia.
    """
    from turnos.models import Atencion, RegistroQuirurgico, Turno

    if anestesista is None:
        raise ValidationError({'anestesista_id': MSG_ANESTESISTA})
    dx = (diagnostico_preoperatorio or '').strip()
    if not dx:
        raise ValidationError({'diagnostico_preoperatorio': MSG_DX_PRE})

    turno = None
    if sesion.turno_id:
        turno = Turno.objects.select_for_update().filter(pk=sesion.turno_id).first()

    sala = recurso
    if sala is None and turno is not None and turno.recurso_id:
        sala = turno.recurso

    if sala is None:
        raise ValidationError({'recurso_id': MSG_RECURSO_CIRUGIA})
    if not _recurso_admitido_cirugia(sala):
        raise ValidationError({'recurso_id': MSG_RECURSO_TIPO})

    atencion = None
    if estudio.atencion_id:
        atencion = Atencion.objects.select_for_update().filter(pk=estudio.atencion_id).first()
    elif sesion.atencion_id:
        atencion = Atencion.objects.select_for_update().filter(pk=sesion.atencion_id).first()
    elif turno is not None:
        existing = getattr(turno, 'atencion', None)
        if existing is not None:
            atencion = Atencion.objects.select_for_update().filter(pk=existing.pk).first()

    if atencion is not None:
        if atencion.paciente_id != estudio.paciente_id:
            raise ValidationError(
                {'atencion': 'La atención no pertenece al paciente de la indicación.'}
            )
        if not atencion_compatible_con_cirugia(atencion):
            raise ValidationError({'atencion': MSG_ATENCION_INCOMPATIBLE})
        if atencion.tipo_intervencion not in (
            Atencion.TipoIntervencion.CIRUGIA,
            '',
        ):
            if atencion.tipo_intervencion == Atencion.TipoIntervencion.PROCEDIMIENTO:
                raise ValidationError({'atencion': MSG_ATENCION_INCOMPATIBLE})
    else:
        # tipo_atencion refleja el recurso real; el hijo lo crea este módulo
        # (no el factory global con placeholders).
        atencion = Atencion(
            turno=turno,
            paciente=estudio.paciente,
            medico_principal=medico,
            contexto_atencion=Atencion.ContextoAtencion.AMBULATORIA,
            tipo_atencion=sala.tipo_recurso,
            tipo_intervencion=Atencion.TipoIntervencion.CIRUGIA,
            estado_clinico=Atencion.EstadoClinico.ABIERTA,
            observaciones_generales=(
                f'Realización módulo estudios/cirugía #{estudio.pk}'
            ),
        )
        atencion.full_clean()
        atencion.save()

    try:
        registro = atencion.registro_quirurgico
    except ObjectDoesNotExist:
        registro = None

    if registro is None:
        # Proyección vacía: canónico = informe versionado; sin texto de relleno.
        registro = RegistroQuirurgico.objects.create(
            atencion=atencion,
            anestesista=anestesista,
            diagnostico_preoperatorio=dx,
            protocolo_quirurgico='',
            procedimiento=estudio.procedimiento_catalogo,
        )
    else:
        updates = []
        if registro.anestesista_id != anestesista.pk:
            registro.anestesista = anestesista
            updates.append('anestesista')
        if (registro.diagnostico_preoperatorio or '').strip() != dx:
            registro.diagnostico_preoperatorio = dx
            updates.append('diagnostico_preoperatorio')
        if (
            estudio.procedimiento_catalogo_id
            and registro.procedimiento_id != estudio.procedimiento_catalogo_id
        ):
            registro.procedimiento = estudio.procedimiento_catalogo
            updates.append('procedimiento')
        if updates:
            registro.save(update_fields=updates + ['updated_at'])

    if estudio.atencion_id != atencion.pk:
        estudio.atencion = atencion
        estudio.save(update_fields=['atencion', 'updated_at'])

    sesion.atencion = atencion
    sesion.save(update_fields=['atencion', 'updated_at'])

    return atencion, registro


def sincronizar_proyeccion_protocolo(registro, texto: str) -> None:
    """Escribe proyección desde el canónico versionado (única vía de escritura)."""
    t = texto or ''
    if registro.protocolo_quirurgico != t:
        registro.protocolo_quirurgico = t
        registro.save(update_fields=['protocolo_quirurgico', 'updated_at'])


def registro_quirurgico_vinculado_a_circuito_modulo(registro) -> bool:
    from estudios.models import EstudioComplementario

    return EstudioComplementario.objects.filter(
        tipo_actividad=EstudioComplementario.TipoActividad.CIRUGIA,
        atencion_id=registro.pk,
    ).exists()
