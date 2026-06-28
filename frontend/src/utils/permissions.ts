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

/** Rol operador LIMS (puede tener `is_staff` para Django admin sin acceso EMR PHI). */
export function isLaboratorioRole(user: User | null | undefined): boolean {
  if (!user) return false;
  return normalizeRol(user) === 'laboratorio';
}

/**
 * Staff/admin con bypass EMR global. Excluye `rol=laboratorio` aunque `is_staff=true`.
 * Alineado con backend `emr_staff_or_admin_global`.
 */
export function isEmrStaffOrAdmin(user: User | null | undefined): boolean {
  if (!user || isLaboratorioRole(user)) return false;
  return Boolean(user.is_superuser || user.is_staff || normalizeRol(user) === 'admin');
}

/** Alias de `isEmrStaffOrAdmin` para permisos EMR (no usar para LIMS). */
export function isStaffOrAdmin(user: User | null | undefined): boolean {
  return isEmrStaffOrAdmin(user);
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

/** Auditoría (IsAuditAdmin): superuser, staff o rol admin; laboratorio excluido. */
export function canAccessAuditoria(user: User | null | undefined): boolean {
  if (!user || isLaboratorioRole(user)) return false;
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
