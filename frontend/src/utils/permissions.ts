import type { User } from '../types';
import {
  canAccessLimsModule,
  canAccessMicrobiologia,
  canOperateLims,
  canOperateMicrobiologia,
  canValidarOrdenLims,
  canValidarInformeMicro,
  normalizeRol,
} from './limsAccess';

export { normalizeRol };
export {
  canAccessLimsModule as canAccessLims,
  canOperateLims,
  canValidarOrdenLims as canValidateLims,
  canAccessMicrobiologia,
  canOperateMicrobiologia,
  canValidarInformeMicro as canValidateMicrobiologia,
};

export type NormalizedAppRole =
  | 'admin'
  | 'medico'
  | 'secretaria'
  | 'enfermeria'
  | 'laboratorio'
  | 'paciente'
  | 'sin_rol';

/** Superuser, Django staff o rol admin (alineado con backend). */
export function isStaffOrAdmin(user: User | null | undefined): boolean {
  if (!user) return false;
  return Boolean(user.is_superuser || user.is_staff || normalizeRol(user) === 'admin');
}

/** Lectura global de pacientes (admin/staff/secretaría/enfermería). */
function hasPacientesLecturaGlobal(user: User | null | undefined): boolean {
  if (!user) return false;
  if (isStaffOrAdmin(user)) return true;
  const rol = normalizeRol(user);
  return rol === 'secretaria' || rol === 'enfermeria';
}

/** Lista / módulo pacientes (no laboratorio ni sin rol). */
export function canAccessPacientes(user: User | null | undefined): boolean {
  if (!user) return false;
  if (hasPacientesLecturaGlobal(user)) return true;
  const rol = normalizeRol(user);
  return rol === 'medico' || rol === 'paciente';
}

/** Alta de paciente: roles con permiso de creación en backend. */
export function canCreatePaciente(user: User | null | undefined): boolean {
  if (!user) return false;
  if (hasPacientesLecturaGlobal(user)) return true;
  return normalizeRol(user) === 'medico';
}

/** Vista 360 / detalle de paciente (validación final en backend). */
export function canAccessPaciente360(user: User | null | undefined): boolean {
  return canAccessPacientes(user);
}

/** Solicitudes genéricas EMR (PERM-01): no enfermería/laboratorio/sin rol. */
export function canAccessSolicitudes(user: User | null | undefined): boolean {
  if (!user) return false;
  if (user.is_superuser || normalizeRol(user) === 'admin') return true;
  const rol = normalizeRol(user);
  return rol === 'secretaria' || rol === 'medico' || rol === 'paciente';
}

/** Archivos médicos: admin/médico/paciente (secretaría/enfermería/laboratorio bloqueados). */
export function canAccessArchivosMedicos(user: User | null | undefined): boolean {
  if (!user) return false;
  if (user.is_superuser || normalizeRol(user) === 'admin') return true;
  const rol = normalizeRol(user);
  return rol === 'medico' || rol === 'paciente';
}

/** Crear/editar archivo médico (CanWriteArchivoMedico). */
export function canWriteArchivoMedico(user: User | null | undefined): boolean {
  if (!user) return false;
  if (user.is_superuser || normalizeRol(user) === 'admin') return true;
  const rol = normalizeRol(user);
  return rol === 'medico' || rol === 'paciente';
}

/** Descarga de archivo (misma política de módulo; objeto validado en backend). */
export function canDownloadArchivoMedico(user: User | null | undefined): boolean {
  return canAccessArchivosMedicos(user);
}

/** Auditoría (IsAuditAdmin): superuser, staff o rol admin. */
export function canAccessAuditoria(user: User | null | undefined): boolean {
  if (!user) return false;
  if (user.is_superuser || user.is_staff) return true;
  return normalizeRol(user) === 'admin';
}

/**
 * Módulo /atenciones (QA-ROLE-01): admin/staff, médico, enfermería (lectura), paciente (lectura propia).
 * Secretaría, laboratorio y sin rol: bloqueados.
 */
export function canAccessAtenciones(user: User | null | undefined): boolean {
  if (!user) return false;
  if (isStaffOrAdmin(user)) return true;
  const rol = normalizeRol(user);
  return rol === 'medico' || rol === 'enfermeria' || rol === 'paciente';
}

/** Mutaciones clínicas en atenciones: admin/staff y médico (objeto validado en backend). */
export function canOperateAtenciones(user: User | null | undefined): boolean {
  if (!user) return false;
  if (isStaffOrAdmin(user)) return true;
  return normalizeRol(user) === 'medico';
}
