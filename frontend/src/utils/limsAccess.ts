import { User } from '../types';
import { isOperadorLimsRole, puedeValidarLimsRole } from './roles';

export type NormalizedRol = string;

export function normalizeRol(user: User | null): NormalizedRol {
  return String(user?.rol || '').toLowerCase();
}

/**
 * Módulo LIMS (sidebar «Laboratorio (LIMS)» y rutas /laboratorio/*).
 * Admin, laboratorio (técnico) y bioquímico.
 * Médicos/secretaría usan el portal clínico «Laboratorio» (/solicitudes).
 */
export function canAccessLimsModule(user: User | null): boolean {
  if (!user) return false;
  if (user.is_superuser) return true;
  const r = normalizeRol(user);
  return r === 'admin' || isOperadorLimsRole(r);
}

/**
 * @deprecated El área LIMS ya no admite roles operativos limitados.
 * Secretaría/enfermería consultan resultados validados en /solicitudes.
 */
export function canAccessLimsOperativaLimitada(_user: User | null): boolean {
  return false;
}

/** Acceso al área LIMS (alias de canAccessLimsModule). */
export function canAccessLimsAny(user: User | null): boolean {
  return canAccessLimsModule(user);
}

/** Pendientes y órdenes LIMS en sidebar/rutas. */
export function canAccessLimsPendientes(user: User | null): boolean {
  return canAccessLimsModule(user);
}

export function canAccessLimsOrdenes(user: User | null): boolean {
  return canAccessLimsModule(user);
}

/** Catálogos LIMS (exámenes, tipos de muestra): sin secretaría/enfermería. */
export function canAccessLimsCatalogos(user: User | null): boolean {
  return canAccessLimsModule(user);
}

/** Rol con bandeja restringida (no operador LIMS completo). */
export function isLimsOperativaLimitada(user: User | null): boolean {
  return canAccessLimsOperativaLimitada(user) && !canAccessLimsModule(user);
}

/** Detalle de orden visible para roles restringidos solo en PENDIENTE/FINALIZADO. */
export function canAccessLimsOrdenDetalle(
  user: User | null,
  estado: string | null | undefined
): boolean {
  if (!canAccessLimsAny(user)) return false;
  if (!isLimsOperativaLimitada(user)) return true;
  const e = String(estado || '').toUpperCase();
  return e === 'PENDIENTE' || e === 'FINALIZADO';
}

/** Consulta clínica de análisis (módulo Solicitudes / Análisis clínico). */
export function canAccessAnalisisClinicoLab(user: User | null): boolean {
  if (!user) return false;
  if (user.is_superuser) return true;
  const r = normalizeRol(user);
  return r === 'admin' || r === 'secretaria' || r === 'medico' || r === 'paciente';
}

/** Descargar informe PDF desde el portal clínico (médico/paciente). */
export function canDownloadInformeClinicoPdf(user: User | null): boolean {
  if (!user) return false;
  if (user.is_superuser) return true;
  const r = normalizeRol(user);
  return r === 'admin' || r === 'medico' || r === 'paciente';
}

/** Operaciones de laboratorio sobre orden/muestra/resultados (admin + operadores). */
export function canOperateLims(user: User | null): boolean {
  if (!user) return false;
  if (user.is_superuser) return true;
  const r = normalizeRol(user);
  return r === 'admin' || isOperadorLimsRole(r);
}

/** Enviar informe al paciente (admin y operadores LIMS). */
export function canEnviarInformeLims(user: User | null): boolean {
  return canOperateLims(user);
}

/** @deprecated Usar canEnviarInformeLims */
export function canFinalizarOrdenLims(user: User | null): boolean {
  return canValidarOrdenLims(user);
}

/** Validar y liberar informe (solo bioquímico y admin). */
export function canValidarOrdenLims(user: User | null): boolean {
  if (!user) return false;
  if (user.is_superuser) return true;
  return puedeValidarLimsRole(normalizeRol(user));
}

/** Descargar informe PDF LIMS (PDF-1-FE): solo operadores del módulo LIMS. */
export function canDownloadInformeLimsPdf(
  user: User | null,
  _estado?: string | null
): boolean {
  return canAccessLimsModule(user);
}

/** Misma visibilidad que el módulo LIMS (admin, laboratorio, bioquímico). */
export function canAccessMicrobiologia(user: User | null): boolean {
  return canAccessLimsModule(user);
}

export function canOperateMicrobiologia(user: User | null): boolean {
  return canOperateLims(user);
}

/** Validar informe microbiológico final (bioquímico / admin). */
export function canValidarInformeMicro(user: User | null): boolean {
  return canValidarOrdenLims(user);
}

/** Estados en los que no se admiten mutaciones técnicas (B3-frontend-validación-A). */
export const ESTADOS_MICRO_CERRADOS = ['CANCELADO', 'VALIDADO', 'INFORMADO'] as const;

export type EstadoMicroEstudioCerrado = (typeof ESTADOS_MICRO_CERRADOS)[number];

export function isMicroEstudioCerrado(estado: string | null | undefined): boolean {
  if (!estado) return false;
  return (ESTADOS_MICRO_CERRADOS as readonly string[]).includes(estado);
}

/** Operación técnica permitida: rol operador y estudio no cerrado. */
export function canOperateMicroEstudioTecnico(
  user: User | null,
  estadoEstudio: string | null | undefined
): boolean {
  return canOperateMicrobiologia(user) && !isMicroEstudioCerrado(estadoEstudio);
}

/** Marcar informado: operador con estudio en VALIDADO (transición de cierre permitida). */
export function canMarcarMicroEstudioInformado(
  user: User | null,
  estadoEstudio: string | null | undefined
): boolean {
  return canOperateMicrobiologia(user) && estadoEstudio === 'VALIDADO';
}

/** Catálogos LIMS generales (tipos de muestra): escritura admin y operadores. */
export function canEditLimsCatalogos(user: User | null): boolean {
  return canOperateLims(user);
}

/** Catálogos micro: escritura solo admin. */
export function canEditMicroCatalogos(user: User | null): boolean {
  if (!user) return false;
  if (user.is_superuser) return true;
  return normalizeRol(user) === 'admin';
}
