/**
 * Permisos de UI para turnos — reflejan C5.8.1 (backend es fuente de verdad).
 */
import { Turno, User } from '../types';

export function normalizeRol(user?: User | null): string {
  return (user?.rol || '').toUpperCase();
}

export function canMutateTurnosGlobally(user?: User | null): boolean {
  if (!user) return false;
  if (user.is_staff || user.is_superuser) return true;
  const r = normalizeRol(user);
  return r === 'ADMIN' || r === 'SECRETARIA';
}

/** Lectura de agenda en pantalla /turnos (enfermería incluida). */
export function canViewTurnosAgenda(user?: User | null): boolean {
  if (!user) return false;
  if (user.is_staff || user.is_superuser) return true;
  const r = normalizeRol(user);
  return ['ADMIN', 'SECRETARIA', 'MEDICO', 'PACIENTE', 'ENFERMERIA'].includes(r);
}

export function canCreateTurno(user?: User | null): boolean {
  if (!user) return false;
  if (canMutateTurnosGlobally(user)) return true;
  const r = normalizeRol(user);
  return r === 'MEDICO' || r === 'PACIENTE';
}

export function canEditTurno(user?: User | null, turno?: Turno | null): boolean {
  if (!user) return false;
  if (isAgendaReadOnlyRole(user)) return false;
  if (canMutateTurnosGlobally(user) || user.is_staff || user.is_superuser) {
    return true;
  }
  const r = normalizeRol(user);
  if (r === 'MEDICO') {
    const medicoId = user.medico?.id;
    if (!medicoId) return false;
    if (!turno) return true;
    return turno.medico?.id === medicoId || turno.medico_id === medicoId;
  }
  if (r === 'PACIENTE') {
    const pacienteId = user.paciente?.id;
    if (!pacienteId) return false;
    if (!turno) return true;
    return turno.paciente?.id === pacienteId || turno.paciente_id === pacienteId;
  }
  return false;
}

/** Enfermería: ver agenda global sin crear/editar. Laboratorio: sin pantalla operativa. */
export function isAgendaReadOnlyRole(user?: User | null): boolean {
  const r = normalizeRol(user);
  return r === 'ENFERMERIA';
}

export function isLaboratorioRole(user?: User | null): boolean {
  return normalizeRol(user) === 'LABORATORIO';
}

/** DELETE físico bloqueado en API (405). */
export function canDeleteTurno(): boolean {
  return false;
}

export function shouldLockMedicoField(user?: User | null): boolean {
  return normalizeRol(user) === 'MEDICO';
}

export function shouldLockPacienteField(user?: User | null): boolean {
  return normalizeRol(user) === 'PACIENTE';
}

export function getCurrentMedicoId(user?: User | null): number | undefined {
  return user?.medico?.id;
}

export function getCurrentPacienteId(user?: User | null): number | undefined {
  return user?.paciente?.id;
}

/** POST /api/turnos/{id}/confirmar/ — RESERVADO → CONFIRMADO */
export function canConfirmarTurno(user?: User | null, turno?: Turno | null): boolean {
  if (!user || !turno || isAgendaReadOnlyRole(user) || isLaboratorioRole(user)) return false;
  if (normalizeRol(user) === 'PACIENTE') return false;
  if (!canEditTurno(user, turno)) return false;
  const st = (turno.estado || '').toUpperCase();
  return st === 'RESERVADO';
}

/** POST /api/turnos/{id}/cancelar/ — motivo obligatorio en API */
export function canCancelarTurnoAccion(user?: User | null, turno?: Turno | null): boolean {
  if (!user || !turno || isAgendaReadOnlyRole(user) || isLaboratorioRole(user)) return false;
  const st = (turno.estado || '').toUpperCase();
  if (st === 'REALIZADO' || st === 'CANCELADO') return false;
  if (canMutateTurnosGlobally(user)) return true;
  const r = normalizeRol(user);
  if (r === 'MEDICO') {
    const medicoId = user.medico?.id;
    return Boolean(medicoId && (turno.medico?.id === medicoId || turno.medico_id === medicoId));
  }
  if (r === 'PACIENTE') {
    const pacienteId = user.paciente?.id;
    return Boolean(pacienteId && (turno.paciente?.id === pacienteId || turno.paciente_id === pacienteId));
  }
  return false;
}

/** C5.9.2: el estado no se edita por formulario; solo acciones POST. */
export function canPatchEstadoEnFormulario(_user?: User | null): boolean {
  return false;
}

export function canReprogramarTurno(user?: User | null, turno?: Turno | null): boolean {
  if (!user || !turno || isAgendaReadOnlyRole(user) || isLaboratorioRole(user)) return false;
  const st = (turno.estado || '').toUpperCase();
  if (st === 'CANCELADO' || st === 'REALIZADO') return false;
  if (canMutateTurnosGlobally(user)) return true;
  const r = normalizeRol(user);
  if (r === 'MEDICO') {
    const medicoId = user.medico?.id;
    return Boolean(medicoId && (turno.medico?.id === medicoId || turno.medico_id === medicoId));
  }
  if (r === 'PACIENTE') {
    const pacienteId = user.paciente?.id;
    return Boolean(pacienteId && (turno.paciente?.id === pacienteId || turno.paciente_id === pacienteId));
  }
  return false;
}

/** POST marcar-realizado — médico solo si CONFIRMADO; admin/secretaría también desde RESERVADO. */
export function canMarcarRealizadoTurno(user?: User | null, turno?: Turno | null): boolean {
  if (!user || !turno || isAgendaReadOnlyRole(user) || isLaboratorioRole(user)) return false;
  const st = (turno.estado || '').toUpperCase();
  if (st === 'REALIZADO' || st === 'CANCELADO' || st === 'DISPONIBLE') return false;
  if (canMutateTurnosGlobally(user)) return st === 'RESERVADO' || st === 'CONFIRMADO';
  if (normalizeRol(user) === 'MEDICO') {
    const medicoId = user.medico?.id;
    return Boolean(
      medicoId &&
        (turno.medico?.id === medicoId || turno.medico_id === medicoId) &&
        st === 'CONFIRMADO',
    );
  }
  return false;
}

/** POST iniciar-atencion — flujo clínico C5.10.1 (médico propio; admin/staff; no secretaría). */
export function canIniciarAtencionTurno(user?: User | null, turno?: Turno | null): boolean {
  if (!user || !turno || isAgendaReadOnlyRole(user) || isLaboratorioRole(user)) return false;
  if (normalizeRol(user) === 'PACIENTE' || normalizeRol(user) === 'SECRETARIA') return false;
  const st = (turno.estado || '').toUpperCase();
  if (st === 'CANCELADO' || st === 'DISPONIBLE') return false;
  if (user.is_staff || user.is_superuser || normalizeRol(user) === 'ADMIN') return true;
  if (normalizeRol(user) === 'MEDICO') {
    const medicoId = user.medico?.id;
    return Boolean(
      medicoId &&
        (turno.medico?.id === medicoId || turno.medico_id === medicoId) &&
        (st === 'CONFIRMADO' || st === 'RESERVADO' || st === 'REALIZADO'),
    );
  }
  return false;
}

/** POST marcar-no-asistio — RESERVADO/CONFIRMADO → CANCELADO con metadata diferenciada. */
export function canMarcarNoAsistioTurno(user?: User | null, turno?: Turno | null): boolean {
  if (!user || !turno || isAgendaReadOnlyRole(user) || isLaboratorioRole(user)) return false;
  if (normalizeRol(user) === 'PACIENTE') return false;
  const st = (turno.estado || '').toUpperCase();
  if (st !== 'RESERVADO' && st !== 'CONFIRMADO') return false;
  if (canMutateTurnosGlobally(user)) return true;
  if (normalizeRol(user) === 'MEDICO') {
    const medicoId = user.medico?.id;
    return Boolean(medicoId && (turno.medico?.id === medicoId || turno.medico_id === medicoId));
  }
  return false;
}
