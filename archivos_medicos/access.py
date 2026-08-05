"""Reglas de acceso clínico a archivos por paciente (C6.2)."""

from __future__ import annotations

from django.core.exceptions import ObjectDoesNotExist

from historias_clinicas.models import Consulta
from medicos.models import Medico
from pacientes.models import Paciente
from turnos.models import Atencion, Turno


def get_medico_perfil(user) -> Medico | None:
    """Perfil Medico del usuario, o None si no hay vínculo user↔Medico."""
    if user is None or not getattr(user, 'is_authenticated', False):
        return None
    try:
        medico = user.medico
        if medico is not None:
            return medico
    except ObjectDoesNotExist:
        pass
    except Exception:
        pass
    pk = getattr(user, 'pk', None)
    if not pk:
        return None
    return Medico.objects.filter(user_id=pk).first()


def paciente_ids_vinculados_a_medico(medico) -> set[int]:
    """Pacientes vinculados por consulta HC, atención moderna o turno."""
    ids: set[int] = set()
    ids.update(
        Consulta.objects.filter(medico=medico)
        .values_list('historia_clinica__paciente_id', flat=True)
    )
    ids.update(
        Atencion.objects.filter(medico_principal=medico).values_list('paciente_id', flat=True)
    )
    ids.update(
        Turno.objects.filter(medico=medico).values_list('paciente_id', flat=True)
    )
    return {i for i in ids if i}


def medico_puede_acceder_paciente(medico, paciente) -> bool:
    return paciente.id in paciente_ids_vinculados_a_medico(medico)


def consulta_pertenece_a_paciente(consulta, paciente_id: int) -> bool:
    """HistoriaClinica usa paciente como PK; historia_clinica_id == paciente_id."""
    return consulta.historia_clinica_id == paciente_id


def resolver_consulta_para_paciente(consulta_id: int, paciente_id: int) -> Consulta:
    """Existe y pertenece al paciente; si no, lanza ValueError con mensaje."""
    try:
        consulta = Consulta.objects.select_related('medico', 'atencion', 'atencion__medico_principal').get(
            pk=consulta_id
        )
    except Consulta.DoesNotExist as exc:
        raise ValueError('Consulta no encontrada.') from exc
    if not consulta_pertenece_a_paciente(consulta, paciente_id):
        raise ValueError('La consulta no pertenece al paciente indicado.')
    return consulta


def _medico_es_dueno_consulta(
    medico: Medico,
    consulta: Consulta,
    *,
    atencion: Atencion | None = None,
) -> bool:
    """
    True si el médico es dueño clínico de la consulta HC.

    Criterios (en orden):
    - ``consulta.medico_id`` es el médico autenticado; o
    - la consulta está (o puede quedar) ligada a una atención cuyo
      ``medico_principal`` es el autenticado.
    """
    if consulta.medico_id == medico.id:
        return True

    att = atencion
    if att is None and consulta.atencion_id:
        att = getattr(consulta, 'atencion', None)
        if att is None:
            att = Atencion.objects.filter(pk=consulta.atencion_id).first()
    if att is None or att.medico_principal_id != medico.id:
        return False
    if consulta.atencion_id and consulta.atencion_id != att.pk:
        return False
    # Médico ajeno en HC solo se tolera si la consulta ya está 1:1 a mi atención.
    if consulta.medico_id and consulta.medico_id != medico.id:
        return consulta.atencion_id == att.pk
    return True


def validar_consulta_archivo_para_usuario(
    user,
    consulta: Consulta,
    paciente_id: int,
    *,
    atencion: Atencion | None = None,
) -> None:
    """Permiso de vínculo consulta↔archivo; lanza ValueError si no procede."""
    rol = str(getattr(user, 'rol', '') or '').lower()
    if user.is_superuser or rol == 'admin':
        return
    if rol == 'paciente':
        try:
            if user.paciente.id != paciente_id:
                raise ValueError('No puede asociar consultas de otro paciente.')
        except AttributeError as exc:
            raise ValueError('Paciente no vinculado.') from exc
        return
    if rol == 'medico':
        medico = get_medico_perfil(user)
        if medico is None:
            raise ValueError(
                'Médico no vinculado. Tu usuario no tiene perfil de médico asociado.'
            )
        # Si hay atención en el mismo POST, debe ser coherente con la consulta.
        if atencion is not None:
            if atencion.paciente_id != paciente_id:
                raise ValueError('La atención no pertenece al paciente indicado.')
            if consulta.atencion_id and consulta.atencion_id != atencion.pk:
                raise ValueError('La consulta HC no corresponde a la atención indicada.')
        if not _medico_es_dueno_consulta(medico, consulta, atencion=atencion):
            # Mensaje más claro si la atención/HC apunta a un médico sin login.
            principal = None
            if atencion is not None:
                principal = atencion.medico_principal
            elif consulta.atencion_id:
                principal = getattr(getattr(consulta, 'atencion', None), 'medico_principal', None)
            if principal is not None and principal.user_id is None:
                raise ValueError(
                    'La consulta/atención está asignada a un médico del catálogo sin usuario de sistema. '
                    'Pedile a administración que vincule ese médico a un login o reasigne la atención.'
                )
            raise ValueError('No puede asociar una consulta de otro médico.')
        paciente = Paciente.objects.get(pk=paciente_id)
        if not medico_puede_acceder_paciente(medico, paciente):
            raise ValueError('No tiene vínculo clínico con el paciente de la consulta.')
        return
    raise ValueError('No tiene permiso para asociar consultas clínicas.')


def resolver_atencion_para_paciente(atencion_id: int, paciente_id: int) -> Atencion:
    try:
        atencion = Atencion.objects.select_related('medico_principal', 'paciente').get(
            pk=atencion_id
        )
    except Atencion.DoesNotExist as exc:
        raise ValueError('Atención no encontrada.') from exc
    if atencion.paciente_id != paciente_id:
        raise ValueError('La atención no pertenece al paciente indicado.')
    return atencion


def validar_atencion_archivo_para_usuario(user, atencion: Atencion, paciente_id: int) -> None:
    rol = str(getattr(user, 'rol', '') or '').lower()
    if user.is_superuser or rol == 'admin':
        return
    if rol == 'paciente':
        try:
            if user.paciente.id != paciente_id:
                raise ValueError('No puede asociar atenciones de otro paciente.')
        except AttributeError as exc:
            raise ValueError('Paciente no vinculado.') from exc
        return
    if rol == 'medico':
        medico = get_medico_perfil(user)
        if medico is None:
            raise ValueError(
                'Médico no vinculado. Tu usuario no tiene perfil de médico asociado.'
            )
        if atencion.medico_principal_id and atencion.medico_principal_id != medico.id:
            principal = atencion.medico_principal
            if principal is not None and principal.user_id is None:
                raise ValueError(
                    'Esta atención está asignada a un médico del catálogo sin usuario de sistema. '
                    'Pedile a administración que vincule ese médico a un login o reasigne la atención.'
                )
            raise ValueError('No puede adjuntar archivos a atenciones ajenas.')
        paciente = Paciente.objects.get(pk=paciente_id)
        if not medico_puede_acceder_paciente(medico, paciente):
            raise ValueError('No tiene vínculo clínico con el paciente de la atención.')
        return
    raise ValueError('No tiene permiso para adjuntar archivos clínicos.')
