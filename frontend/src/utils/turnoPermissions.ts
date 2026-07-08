/**
 * Permisos de UI para turnos — reflejan C5.8.1 (backend es fuente de verdad).
 */
import { Turno, User } from '../types';
import { isEmrStaffOrAdmin } from './permissions';
import { isProfesionalEstudioRole, ROLES_ESTUDIO_COMPLEMENTARIO } from './roles';
import { isTurnoEstudio } from './recursosEstudio';

export function normalizeRol(user?: User | null): string {
  return (user?.rol || '').toUpperCase();
}

/** True si el médico ya inició la atención clínica vinculada al turno. */
export function turnoTieneAtencionClinica(turno?: Turno | null): boolean {
  if (!turno) return false;
  return Boolean(turno.atencion?.id);
}

/** Paciente puede mutar turno propio solo antes de finalizar (consulta o estudio). */
export function pacientePuedeMutarTurno(user?: User | null, turno?: Turno | null): boolean {
  if (!user || normalizeRol(user) !== 'PACIENTE') return true;
  if (!turno) return true;
  const pacienteId = user.paciente?.id;
  if (!pacienteId) return false;
  const ownsTurno =
    turno.paciente?.id === pacienteId || turno.paciente_id === pacienteId;
  if (!ownsTurno) return false;
  const st = (turno.estado || '').toUpperCase();
  if (st === 'REALIZADO' || st === 'CANCELADO') return false;
  if (turnoTieneAtencionClinica(turno)) return false;
  return true;
}

/** True si el médico puede operar el turno (consulta propia o estudio vinculado). */
export function medicoEsDuenoTurno(user?: User | null, turno?: Turno | null): boolean {
  if (!user || !turno) return false;
  const medicoId = user.medico?.id;
  if (!medicoId) return false;
  if (turno.medico?.id === medicoId || turno.medico_id === medicoId) return true;
  if (turno.estudio_complementario?.medico_solicitante_id === medicoId) return true;
  if (isTurnoEstudio(turno) && !turno.medico && !turno.medico_id) {
    return true;
  }
  return false;
}

export function canMutateTurnosGlobally(user?: User | null): boolean {
  if (!user) return false;
  if (isEmrStaffOrAdmin(user)) return true;
  const r = normalizeRol(user);
  return r === 'ADMIN' || r === 'SECRETARIA';
}

/** Lectura de agenda en pantalla /turnos. */
export function canViewTurnosAgenda(user?: User | null): boolean {
  if (!user) return false;
  if (isEmrStaffOrAdmin(user)) return true;
  const r = normalizeRol(user);
  return [
    'ADMIN',
    'SECRETARIA',
    'MEDICO',
    'PACIENTE',
    'ENFERMERIA',
    'LABORATORIO',
    ...ROLES_ESTUDIO_COMPLEMENTARIO.map((rol) => rol.toUpperCase()),
  ].includes(r);
}

/** Alias para navegación / rutas. */
export const canAccessTurnosAgenda = canViewTurnosAgenda;

export function canCreateTurno(user?: User | null): boolean {
  if (!user) return false;
  if (canMutateTurnosGlobally(user)) return true;
  const r = normalizeRol(user);
  return r === 'MEDICO' || r === 'PACIENTE';
}

export function canEditTurno(user?: User | null, turno?: Turno | null): boolean {
  if (!user) return false;
  if (isAgendaReadOnlyRole(user)) return false;
  if (canMutateTurnosGlobally(user) || isEmrStaffOrAdmin(user)) {
    return true;
  }
  const r = normalizeRol(user);
  if (r === 'MEDICO') {
    if (!user.medico?.id) return false;
    if (!turno) return true;
    return medicoEsDuenoTurno(user, turno);
  }
  if (r === 'PACIENTE') {
    return pacientePuedeMutarTurno(user, turno);
  }
  return false;
}

/** Enfermería, laboratorio y profesionales de estudio: ver agenda global sin crear/editar. */
export function isAgendaReadOnlyRole(user?: User | null): boolean {
  const r = normalizeRol(user);
  if (r === 'ENFERMERIA' || r === 'LABORATORIO') return true;
  return isProfesionalEstudioRole(r.toLowerCase());
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
  if (!user || !turno || isAgendaReadOnlyRole(user)) return false;
  if (normalizeRol(user) === 'PACIENTE') return false;
  if (!canEditTurno(user, turno)) return false;
  const st = (turno.estado || '').toUpperCase();
  return st === 'RESERVADO';
}

/** POST /api/turnos/{id}/cancelar/ — motivo obligatorio en API */
export function canCancelarTurnoAccion(user?: User | null, turno?: Turno | null): boolean {
  if (!user || !turno || isAgendaReadOnlyRole(user)) return false;
  const st = (turno.estado || '').toUpperCase();
  if (st === 'REALIZADO' || st === 'CANCELADO') return false;
  if (canMutateTurnosGlobally(user)) return true;
  const r = normalizeRol(user);
  if (r === 'MEDICO') {
    return medicoEsDuenoTurno(user, turno);
  }
  if (r === 'PACIENTE') {
    return pacientePuedeMutarTurno(user, turno);
  }
  return false;
}

/** C5.9.2: el estado no se edita por formulario; solo acciones POST. */
export function canPatchEstadoEnFormulario(_user?: User | null): boolean {
  return false;
}

export function canReprogramarTurno(user?: User | null, turno?: Turno | null): boolean {
  if (!user || !turno || isAgendaReadOnlyRole(user)) return false;
  const st = (turno.estado || '').toUpperCase();
  if (st === 'CANCELADO' || st === 'REALIZADO') return false;
  if (canMutateTurnosGlobally(user)) return true;
  const r = normalizeRol(user);
  if (r === 'MEDICO') {
    return medicoEsDuenoTurno(user, turno);
  }
  if (r === 'PACIENTE') {
    return pacientePuedeMutarTurno(user, turno);
  }
  return false;
}

/** POST marcar-realizado — médico solo si CONFIRMADO; admin/secretaría también desde RESERVADO. */
export function canMarcarRealizadoTurno(user?: User | null, turno?: Turno | null): boolean {
  if (!user || !turno || isAgendaReadOnlyRole(user)) return false;
  const st = (turno.estado || '').toUpperCase();
  if (st === 'REALIZADO' || st === 'CANCELADO' || st === 'DISPONIBLE') return false;
  if (canMutateTurnosGlobally(user)) return st === 'RESERVADO' || st === 'CONFIRMADO';
  if (normalizeRol(user) === 'MEDICO') {
    return medicoEsDuenoTurno(user, turno) && st === 'CONFIRMADO';
  }
  return false;
}

/** POST iniciar-atencion — flujo clínico C5.10.1 (médico propio; admin/staff; no secretaría). */
export function canIniciarAtencionTurno(user?: User | null, turno?: Turno | null): boolean {
  if (!user || !turno || isAgendaReadOnlyRole(user)) return false;
  if (normalizeRol(user) === 'PACIENTE' || normalizeRol(user) === 'SECRETARIA') return false;
  const st = (turno.estado || '').toUpperCase();
  if (st === 'CANCELADO' || st === 'DISPONIBLE') return false;
  if (isEmrStaffOrAdmin(user)) return true;
  if (normalizeRol(user) === 'MEDICO') {
    return (
      medicoEsDuenoTurno(user, turno) &&
      (st === 'CONFIRMADO' || st === 'RESERVADO' || st === 'REALIZADO')
    );
  }
  return false;
}

/** POST marcar-no-asistio — RESERVADO/CONFIRMADO → CANCELADO con metadata diferenciada. */
export function canMarcarNoAsistioTurno(user?: User | null, turno?: Turno | null): boolean {
  if (!user || !turno || isAgendaReadOnlyRole(user)) return false;
  if (normalizeRol(user) === 'PACIENTE') return false;
  const st = (turno.estado || '').toUpperCase();
  if (st !== 'RESERVADO' && st !== 'CONFIRMADO') return false;
  if (canMutateTurnosGlobally(user)) return true;
  if (normalizeRol(user) === 'MEDICO') {
    return medicoEsDuenoTurno(user, turno);
  }
  return false;
}
