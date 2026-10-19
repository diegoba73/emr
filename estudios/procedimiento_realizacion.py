"""C — realización de PROCEDIMIENTO: Atencion + RegistroProcedimiento según reglas.

RegistroProcedimiento exige Atencion (PK). Sin turno ni sala → sin atención ni registro;
documentación vía indicación + sesión + informe versionado.
"""
from __future__ import annotations

import logging

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction

from estudios.actividad_rules import MSG_ATENCION_INCOMPATIBLE

logger = logging.getLogger(__name__)


def _tiene_hijo(atencion, related_name: str) -> bool:
    try:
        getattr(atencion, related_name)
        return True
    except ObjectDoesNotExist:
        return False
    except AttributeError:
        return False


def atencion_compatible_con_procedimiento(atencion) -> bool:
    """True si la atención admite / ya tiene RegistroProcedimiento (no consulta ni quirúrgico)."""
    if _tiene_hijo(atencion, 'registro_quirurgico'):
        return False
    if _tiene_hijo(atencion, 'consulta_ambulatoria'):
        return False
    if _tiene_hijo(atencion, 'evolucion_internacion'):
        return False
    return True


def _descripcion_desde_estudio(estudio) -> str:
    cat = getattr(estudio, 'procedimiento_catalogo', None)
    if cat is not None:
        return (getattr(cat, 'nombre', None) or f'Procedimiento #{cat.pk}')[:255]
    return f'Procedimiento indicación #{estudio.pk}'[:255]


@transaction.atomic
def ensure_atencion_y_registro_procedimiento(
    *,
    estudio,
    sesion,
    medico,
    recurso=None,
    actor=None,
):
    """
    Crea o reutiliza Atencion + RegistroProcedimiento si hay turno o sala.
    Sin ambos → (None, None). Idempotente si ya existen vínculos coherentes.
    """
    from turnos.models import Atencion, Recurso, RegistroProcedimiento, Turno

    turno = None
    if sesion.turno_id:
        turno = Turno.objects.select_for_update().filter(pk=sesion.turno_id).first()

    sala = recurso
    if sala is None and turno is not None and turno.recurso_id:
        sala = turno.recurso

    necesita_atencion = bool(turno is not None or sala is not None)
    if not necesita_atencion:
        return None, None

    # Reutilizar atención ya vinculada (estudio o sesión).
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
            raise ValidationError({'atencion': 'La atención no pertenece al paciente de la indicación.'})
        if not atencion_compatible_con_procedimiento(atencion):
            raise ValidationError({'atencion': MSG_ATENCION_INCOMPATIBLE})
        if atencion.tipo_intervencion not in (
            Atencion.TipoIntervencion.PROCEDIMIENTO,
            Atencion.TipoIntervencion.ESTUDIO,
            '',
        ):
            # Permitir ESTUDIO legacy en salas; exigir no quirúrgico.
            if atencion.tipo_intervencion == Atencion.TipoIntervencion.CIRUGIA:
                raise ValidationError({'atencion': MSG_ATENCION_INCOMPATIBLE})
    else:
        tipo_atencion = Recurso.TipoRecurso.SALA_PROCEDIMIENTO
        if sala is not None:
            tipo_atencion = sala.tipo_recurso
            if tipo_atencion not in (
                Recurso.TipoRecurso.SALA_PROCEDIMIENTO,
                Recurso.TipoRecurso.SALA_HEMODINAMIA,
            ):
                raise ValidationError(
                    {'recurso_id': 'La sala debe ser de procedimiento o hemodinamia.'}
                )
            # Hemodinamia en factory global crea RegistroQuirurgico — aquí forzamos
            # RegistroProcedimiento (C: solo no quirúrgico) sin tocar ese factory.
            tipo_atencion = Recurso.TipoRecurso.SALA_PROCEDIMIENTO

        atencion = Atencion(
            turno=turno,
            paciente=estudio.paciente,
            medico_principal=medico,
            contexto_atencion=Atencion.ContextoAtencion.AMBULATORIA,
            tipo_atencion=tipo_atencion,
            tipo_intervencion=Atencion.TipoIntervencion.PROCEDIMIENTO,
            estado_clinico=Atencion.EstadoClinico.ABIERTA,
            observaciones_generales=(
                f'Realización módulo estudios/procedimientos #{estudio.pk}'
            ),
        )
        atencion.full_clean()
        atencion.save()

    registro = None
    try:
        registro = atencion.registro_procedimiento
    except ObjectDoesNotExist:
        registro = None
    if registro is None:
        registro = RegistroProcedimiento.objects.create(
            atencion=atencion,
            descripcion_procedimiento=_descripcion_desde_estudio(estudio),
            procedimiento=estudio.procedimiento_catalogo,
            # No copiar texto de informe aquí — canónico = InformeEstudioComplementario.
            informe_medico=None,
        )

    # Vínculos explícitos
    update_estudio = []
    if estudio.atencion_id != atencion.pk:
        estudio.atencion = atencion
        update_estudio.append('atencion')
    if update_estudio:
        update_estudio.append('updated_at')
        estudio.save(update_fields=update_estudio)

    sesion.atencion = atencion
    sesion.save(update_fields=['atencion', 'updated_at'])

    return atencion, registro
