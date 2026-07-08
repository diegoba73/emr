"""Reglas de acceso clínico a archivos por paciente (C6.2)."""

from __future__ import annotations

from historias_clinicas.models import Consulta
from pacientes.models import Paciente
from turnos.models import Atencion, Turno


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
        consulta = Consulta.objects.select_related('medico').get(pk=consulta_id)
    except Consulta.DoesNotExist as exc:
        raise ValueError('Consulta no encontrada.') from exc
    if not consulta_pertenece_a_paciente(consulta, paciente_id):
        raise ValueError('La consulta no pertenece al paciente indicado.')
    return consulta


def validar_consulta_archivo_para_usuario(user, consulta: Consulta, paciente_id: int) -> None:
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
        try:
            medico = user.medico
        except Exception as exc:
            raise ValueError('Médico no vinculado.') from exc
        if consulta.medico_id and consulta.medico_id != medico.id:
            raise ValueError('No puede asociar una consulta de otro médico.')
        from pacientes.models import Paciente

        paciente = Paciente.objects.get(pk=paciente_id)
        if not medico_puede_acceder_paciente(medico, paciente):
            raise ValueError('No tiene vínculo clínico con el paciente de la consulta.')
        return
    raise ValueError('No tiene permiso para asociar consultas clínicas.')


def resolver_atencion_para_paciente(atencion_id: int, paciente_id: int) -> Atencion:
    try:
        atencion = Atencion.objects.select_related('medico_principal', 'paciente').get(pk=atencion_id)
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
        try:
            medico = user.medico
        except Exception as exc:
            raise ValueError('Médico no vinculado.') from exc
        if atencion.medico_principal_id and atencion.medico_principal_id != medico.id:
            raise ValueError('No puede adjuntar archivos a atenciones ajenas.')
        paciente = Paciente.objects.get(pk=paciente_id)
        if not medico_puede_acceder_paciente(medico, paciente):
            raise ValueError('No tiene vínculo clínico con el paciente de la atención.')
        return
    raise ValueError('No tiene permiso para adjuntar archivos clínicos.')
