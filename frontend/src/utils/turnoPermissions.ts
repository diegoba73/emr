/**
 * Permisos de UI para turnos — reflejan C5.8.1 (backend es fuente de verdad).
 */
import { Turno, User } from '../types';
import { isEmrStaffOrAdmin } from './permissions';
import {
  isOperadorLimsRole,
  isProfesionalEstudioRole,
  ROLES_ESTUDIO_COMPLEMENTARIO,
} from './roles';
import { isTurnoEstudio } from './recursosEstudio';

export function normalizeRol(user?: User | null): string {
  return (user?.rol || '').toUpperCase();
}

/** True si el médico ya inició la atención clínica vinculada al turno. */
export function turnoTieneAtencionClinica(turno?: Turno | null): boolean {
  if (!turno) return false;
  return Boolean(turno.atencion?.id);
}

/** Paciente ya no muta turnos por agenda: solo reserva vía portal. */
export function pacientePuedeMutarTurno(_user?: User | null, _turno?: Turno | null): boolean {
  return false;
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

/** Técnico laboratorio o bioquímico (ambos operan LIMS, no agenda). */
export function isLaboratorioRole(user?: User | null): boolean {
  return isOperadorLimsRole(user?.rol);
}

/** Lectura de agenda en pantalla /turnos. Operadores LIMS no usan agenda. */
export function canViewTurnosAgenda(user?: User | null): boolean {
  if (!user) return false;
  if (isLaboratorioRole(user)) return false;
  if (isEmrStaffOrAdmin(user)) return true;
  const r = normalizeRol(user);
  return [
    'ADMIN',
    'SECRETARIA',
    'MEDICO',
    'PACIENTE',
    'ENFERMERIA',
    ...ROLES_ESTUDIO_COMPLEMENTARIO.map((rol) => rol.toUpperCase()),
  ].includes(r);
}

/** Alias para navegación / rutas. */
export const canAccessTurnosAgenda = canViewTurnosAgenda;

/** Crear turno por modal/API: solo secretaría/admin (paciente usa portal). */
export function canCreateTurno(user?: User | null): boolean {
  return canMutateTurnosGlobally(user);
}

export function canEditTurno(user?: User | null, _turno?: Turno | null): boolean {
  if (!user) return false;
  if (isAgendaReadOnlyRole(user)) return false;
  return canMutateTurnosGlobally(user) || isEmrStaffOrAdmin(user);
}

/** Enfermería y profesionales de estudio: ver agenda global sin crear/editar. */
export function isAgendaReadOnlyRole(user?: User | null): boolean {
  const r = normalizeRol(user);
  if (r === 'ENFERMERIA') return true;
  return isProfesionalEstudioRole(r.toLowerCase());
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

/** POST /api/turnos/{id}/confirmar/ — RESERVADO → CONFIRMADO (solo secretaría/admin). */
export function canConfirmarTurno(user?: User | null, turno?: Turno | null): boolean {
  if (!user || !turno || isAgendaReadOnlyRole(user)) return false;
  if (!canMutateTurnosGlobally(user)) return false;
  const st = (turno.estado || '').toUpperCase();
  return st === 'RESERVADO';
}

/** POST /api/turnos/{id}/cancelar/ — solo secretaría/admin. */
export function canCancelarTurnoAccion(user?: User | null, turno?: Turno | null): boolean {
  if (!user || !turno || isAgendaReadOnlyRole(user)) return false;
  const st = (turno.estado || '').toUpperCase();
  if (st === 'REALIZADO' || st === 'CANCELADO') return false;
  return canMutateTurnosGlobally(user);
}

/** C5.9.2: el estado no se edita por formulario; solo acciones POST. */
export function canPatchEstadoEnFormulario(_user?: User | null): boolean {
  return false;
}

/** Reprogramar / cambiar día: solo secretaría/admin. */
export function canReprogramarTurno(user?: User | null, turno?: Turno | null): boolean {
  if (!user || !turno || isAgendaReadOnlyRole(user)) return false;
  const st = (turno.estado || '').toUpperCase();
  if (st === 'CANCELADO' || st === 'REALIZADO') return false;
  return canMutateTurnosGlobally(user);
}

/** POST marcar-realizado — solo secretaría/admin (médico usa iniciar-atencion). */
export function canMarcarRealizadoTurno(user?: User | null, turno?: Turno | null): boolean {
  if (!user || !turno || isAgendaReadOnlyRole(user)) return false;
  const st = (turno.estado || '').toUpperCase();
  if (st === 'REALIZADO' || st === 'CANCELADO' || st === 'DISPONIBLE') return false;
  return canMutateTurnosGlobally(user) && (st === 'RESERVADO' || st === 'CONFIRMADO');
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
      (st === 'CONFIRMADO' || st === 'REALIZADO')
    );
  }
  return false;
}

/** POST marcar-no-asistio — solo secretaría/admin. */
export function canMarcarNoAsistioTurno(user?: User | null, turno?: Turno | null): boolean {
  if (!user || !turno || isAgendaReadOnlyRole(user)) return false;
  const st = (turno.estado || '').toUpperCase();
  if (st !== 'RESERVADO' && st !== 'CONFIRMADO') return false;
  return canMutateTurnosGlobally(user);
}
