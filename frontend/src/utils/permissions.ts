import type { User } from '../types';
import {
  isLecturaOperativaRole,
  isOperadorLimsRole,
  isProfesionalEstudioRole,
  isSecretariaEmrRole,
  isSecretariaInstitucionalRole,
  isSecretariaLabRole,
} from './roles';
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
  | 'secretaria_lab'
  | 'enfermeria'
  | 'laboratorio'
  | 'bioquimico'
  | 'kinesiologo'
  | 'radiologo'
  | 'ecografista'
  | 'fonoaudiologo'
  | 'paciente'
  | 'sin_rol';

export {
  isProfesionalEstudioRole,
  isLecturaOperativaRole,
  isOperadorLimsRole,
  isSecretariaEmrRole,
  isSecretariaInstitucionalRole,
  isSecretariaLabRole,
  isSecretariaEntregaInformeRole,
} from './roles';

/** Rol operador LIMS (puede tener `is_staff` para Django admin sin acceso EMR PHI). */
export function isLaboratorioRole(user: User | null | undefined): boolean {
  if (!user) return false;
  return isOperadorLimsRole(normalizeRol(user));
}

/**
 * Staff/admin con bypass EMR global. Excluye `rol=laboratorio` aunque `is_staff=true`.
 * Alineado con backend `emr_staff_or_admin_global`.
 */
export function isEmrStaffOrAdmin(user: User | null | undefined): boolean {
  if (!user) return false;
  if (user.is_superuser) return true;
  if (isLaboratorioRole(user)) return false;
  return Boolean(user.is_superuser || user.is_staff || normalizeRol(user) === 'admin');
}

/** Alias de `isEmrStaffOrAdmin` para permisos EMR (no usar para LIMS). */
export function isStaffOrAdmin(user: User | null | undefined): boolean {
  return isEmrStaffOrAdmin(user);
}

/** Lectura global de pacientes (admin/staff/secretaría/enfermería/operativos). */
function hasPacientesLecturaGlobal(user: User | null | undefined): boolean {
  if (!user) return false;
  if (isStaffOrAdmin(user)) return true;
  const rol = normalizeRol(user);
  return rol === 'medico' || isSecretariaEmrRole(rol) || rol === 'enfermeria' || isLecturaOperativaRole(rol);
}

/** Lista / módulo pacientes (médico, operativos y roles administrativos; no paciente). */
export function canAccessPacientes(user: User | null | undefined): boolean {
  if (!user) return false;
  if (hasPacientesLecturaGlobal(user)) return true;
  return normalizeRol(user) === 'medico';
}

/** Alta de paciente: secretaría, médico, operadores LIMS (lab/bio) y admin. */
export function canCreatePaciente(user: User | null | undefined): boolean {
  if (!user) return false;
  if (user.is_superuser || normalizeRol(user) === 'admin') return true;
  const rol = normalizeRol(user);
  if (isOperadorLimsRole(rol)) return true;
  if (isLecturaOperativaRole(rol)) return false;
  return isSecretariaEmrRole(rol) || rol === 'medico';
}

/** Listado / gestión de médicos: admin, secretaría y operadores LIMS. */
export function canAccessMedicos(user: User | null | undefined): boolean {
  if (!user) return false;
  if (user.is_superuser || normalizeRol(user) === 'admin') return true;
  const rol = normalizeRol(user);
  if (isOperadorLimsRole(rol)) return true;
  if (user.is_staff && !isLaboratorioRole(user)) return true;
  return isSecretariaEmrRole(rol);
}

/** Alta/edición de ficha médico (sin DELETE para lab/bio; API lo restringe). */
export function canCreateMedico(user: User | null | undefined): boolean {
  return canAccessMedicos(user);
}

/** Vista 360 / detalle de paciente (médico/admin o paciente sobre su ficha). */
export function canAccessPaciente360(user: User | null | undefined): boolean {
  if (!user) return false;
  if (hasPacientesLecturaGlobal(user)) return true;
  if (isStaffOrAdmin(user)) return true;
  const rol = normalizeRol(user);
  return rol === 'medico' || rol === 'paciente';
}

/** Solicitudes genéricas EMR (PERM-01): laboratorio/bioquímico/secretaria_lab usan LIMS. */
export function canAccessSolicitudes(user: User | null | undefined): boolean {
  if (!user) return false;
  // Portal clínico /solicitudes: no para operadores LIMS ni secretaría lab (menú LIMS).
  if (isLaboratorioRole(user) || isSecretariaLabRole(normalizeRol(user))) return false;
  if (user.is_superuser || normalizeRol(user) === 'admin') return true;
  const rol = normalizeRol(user);
  // Secretaría institucional: portal clínico para ver/entregar informes liberados.
  return isSecretariaInstitucionalRole(rol) || rol === 'enfermeria' || rol === 'medico' || rol === 'paciente';
}

/** Archivos médicos: lectura para admin, médico, secretaría institucional, enfermería y paciente. */
export function canAccessArchivosMedicos(user: User | null | undefined): boolean {
  if (!user) return false;
  if (user.is_superuser || normalizeRol(user) === 'admin') return true;
  const rol = normalizeRol(user);
  return rol === 'medico' || isSecretariaInstitucionalRole(rol) || rol === 'enfermeria' || rol === 'paciente';
}

/** Crear/editar archivo médico (CanWriteArchivoMedico). Paciente: solo lectura. */
export function canWriteArchivoMedico(user: User | null | undefined): boolean {
  if (!user) return false;
  if (user.is_superuser || normalizeRol(user) === 'admin') return true;
  return normalizeRol(user) === 'medico';
}

/** Actualización demográfica de pacientes: secretaría, médico y admin. */
export function canUpdatePacienteDemographics(user: User | null | undefined): boolean {
  if (!user) return false;
  if (user.is_superuser || normalizeRol(user) === 'admin') return true;
  const rol = normalizeRol(user);
  return isSecretariaEmrRole(rol) || rol === 'medico';
}

/** Eliminación física de pacientes: solo admin/superuser (duplicados sin historia). */

/** Descarga de archivo (misma política de módulo; objeto validado en backend). */
export function canDownloadArchivoMedico(user: User | null | undefined): boolean {
  return canAccessArchivosMedicos(user);
}

/** Auditoría (IsAuditAdmin): superuser, staff o rol admin; laboratorio excluido. */
export function canAccessAuditoria(user: User | null | undefined): boolean {
  if (!user) return false;
  if (user.is_superuser) return true;
  if (isLaboratorioRole(user)) return false;
  if (user.is_superuser || user.is_staff) return true;
  return normalizeRol(user) === 'admin';
}

/** Médico con ámbito solo ambulatorio (sin guardia ni internación). */
export function isMedicoSoloAmbulatorio(user: User | null | undefined): boolean {
  if (!user) return false;
  if (normalizeRol(user) !== 'medico') return false;
  return user.medico?.ambito_atencion === 'AMBULATORIO';
}

/**
 * Módulo /atenciones (QA-ROLE-01): admin/staff, médico, enfermería (lectura), paciente (lectura propia).
 * Secretaría, laboratorio y sin rol: bloqueados (secretaría opera Guardia por separado).
 */
export function canAccessAtenciones(user: User | null | undefined): boolean {
  if (!user) return false;
  if (isStaffOrAdmin(user)) return true;
  const rol = normalizeRol(user);
  return rol === 'medico' || rol === 'enfermeria' || rol === 'paciente';
}

/**
 * Guardia: médico (no solo ambulatorio), enfermería (lectura), ambas secretarías
 * y admin/staff. Secretaría no abre el módulo /atenciones genérico.
 */
export function canAccessGuardia(user: User | null | undefined): boolean {
  if (!user) return false;
  if (isMedicoSoloAmbulatorio(user)) return false;
  if (isStaffOrAdmin(user)) return true;
  const rol = normalizeRol(user);
  return rol === 'medico' || rol === 'enfermeria' || isSecretariaEmrRole(rol);
}

/**
 * Mutaciones clínicas en atenciones/guardia: admin/staff, médico y ambas secretarías
 * (objeto y alcance validados en backend).
 */
export function canOperateAtenciones(user: User | null | undefined): boolean {
  if (!user) return false;
  if (isStaffOrAdmin(user)) return true;
  const rol = normalizeRol(user);
  return rol === 'medico' || isSecretariaEmrRole(rol);
}

/** Catálogos clínicos (CIE-10, estudios, etc.): lectura admin/médico (sin secretaría/enfermería/LIMS). */
export function canAccessCatalogosClinicos(user: User | null | undefined): boolean {
  if (!user) return false;
  if (user.is_superuser) return true;
  if (isLaboratorioRole(user)) return false;
  if (isStaffOrAdmin(user)) return true;
  return normalizeRol(user) === 'medico';
}

/** Edición de catálogos clínicos (secretaría: solo lectura). */
export function canEditCatalogosClinicos(user: User | null | undefined): boolean {
  if (!user) return false;
  if (user.is_superuser) return true;
  if (isLaboratorioRole(user)) return false;
  if (isStaffOrAdmin(user)) return true;
  return normalizeRol(user) === 'medico';
}

/** Catálogo quirúrgico jerárquico: escritura solo admin/superuser. */
export function canEditCirugiaCatalogo(user: User | null | undefined): boolean {
  if (!user) return false;
  if (user.is_superuser) return true;
  return normalizeRol(user) === 'admin';
}

/** Dashboard BI / indicadores de calidad — solo bioquímico. */
export function canAccessBiDashboard(user: User | null | undefined): boolean {
  if (!user) return false;
  return normalizeRol(user) === 'bioquimico';
}

/** Panel de internación: médico (completo), enfermería, kinesiólogo, admin y ambas secretarías. */
export function canAccessInternacion(user: User | null | undefined): boolean {
  if (!user) return false;
  if (user.is_superuser || normalizeRol(user) === 'admin') return true;
  if (isLaboratorioRole(user)) return false;
  if (isMedicoSoloAmbulatorio(user)) return false;
  const rol = normalizeRol(user);
  return rol === 'medico' || rol === 'enfermeria' || isSecretariaEmrRole(rol) || rol === 'kinesiologo';
}

/** Infraestructura de camas/sectores: sin secretaría. */
export function canManageInternacionInfra(user: User | null | undefined): boolean {
  if (!user) return false;
  if (user.is_superuser || normalizeRol(user) === 'admin') return true;
  if (isLaboratorioRole(user)) return false;
  if (isMedicoSoloAmbulatorio(user)) return false;
  const rol = normalizeRol(user);
  return rol === 'medico' || rol === 'enfermeria';
}

/** Ingreso, edición y evoluciones de internación: médico, enfermería y admin. */
export function canOperateInternacionClinica(user: User | null | undefined): boolean {
  return canManageInternacionInfra(user);
}

/** Ingresar paciente a cama: médico, enfermería y admin. */
export function canAdmitirInternacion(user: User | null | undefined): boolean {
  return canOperateInternacionClinica(user);
}

/** Alta de internación: solo médico y admin. */
export function canDarAltaInternacion(user: User | null | undefined): boolean {
  if (!user) return false;
  if (user.is_superuser || normalizeRol(user) === 'admin') return true;
  if (isLaboratorioRole(user)) return false;
  if (isMedicoSoloAmbulatorio(user)) return false;
  return normalizeRol(user) === 'medico';
}

/** Hojas médicas de internación (indicaciones, medicación, ingreso, SOAP). */
export function canWriteHcMedico(user: User | null | undefined): boolean {
  if (!user) return false;
  if (user.is_superuser || normalizeRol(user) === 'admin') return true;
  if (isMedicoSoloAmbulatorio(user)) return false;
  return normalizeRol(user) === 'medico';
}

/** Controles, balance y notas de enfermería. */
export function canWriteHcEnfermeria(user: User | null | undefined): boolean {
  if (!user) return false;
  if (user.is_superuser || normalizeRol(user) === 'admin') return true;
  return normalizeRol(user) === 'enfermeria';
}

/** Hoja de kinesiología. */
export function canWriteHcKinesiologia(user: User | null | undefined): boolean {
  if (!user) return false;
  if (user.is_superuser || normalizeRol(user) === 'admin') return true;
  return normalizeRol(user) === 'kinesiologo';
}

/** Pestaña inicial del modal Gestionar Paciente (0=datos, 1=HC, 2=revista). */
export function getDefaultInternacionModalTab(user: User | null | undefined): number {
  if (canWriteHcEnfermeria(user) || canWriteHcKinesiologia(user)) {
    return 2;
  }
  return 0;
}

/** Portal del paciente — acceso base. */
export function canAccessPortal(user: User | null | undefined): boolean {
  return normalizeRol(user ?? null) === 'paciente';
}

export function canAccessPortalTurnos(user: User | null | undefined): boolean {
  return canAccessPortal(user);
}

export function canAccessPortalResultados(user: User | null | undefined): boolean {
  return canAccessPortal(user);
}

export function canAccessPortalDocumentos(user: User | null | undefined): boolean {
  return canAccessPortal(user);
}

export function canAccessPortalHistoria(user: User | null | undefined): boolean {
  return canAccessPortal(user);
}

export { isPacienteRole } from './navLabels';


/** Estadísticas LIMS (volúmenes / %): admin, bioquímico, secretaría lab. */
export function canAccessEstadisticasLims(user: User | null | undefined): boolean {
  if (!user) return false;
  if (user.is_superuser) return true;
  const rol = normalizeRol(user);
  return rol === 'admin' || rol === 'bioquimico' || isSecretariaLabRole(rol);
}

export function canManageHorarios(user: User | null | undefined): boolean {
  if (!user) return false;
  if (user.is_superuser) return true;
  const rol = normalizeRol(user);
  return rol === 'admin' || isSecretariaInstitucionalRole(rol);
}

/** Tablero de recepción del día (secretaria, médico, admin, enfermería). */

/**
 * @deprecated La cola del médico se unificó en `/recepcion`.
 * Se mantiene por compatibilidad de imports/tests; siempre false.
 */

/** CRUD puestos/reglas de recepción. */
