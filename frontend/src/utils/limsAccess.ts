import { User } from '../types';

export type NormalizedRol = string;

export function normalizeRol(user: User | null): NormalizedRol {
  return String(user?.rol || '').toLowerCase();
}

/** Módulo LIMS completo: admin, laboratorio, médico. */
export function canAccessLimsModule(user: User | null): boolean {
  if (!user) return false;
  if (user.is_superuser) return true;
  const r = normalizeRol(user);
  return r === 'admin' || r === 'laboratorio' || r === 'medico';
}

/** Secretaría/enfermería: solo pendientes y órdenes finalizadas (sin catálogos ni micro). */
export function canAccessLimsOperativaLimitada(user: User | null): boolean {
  if (!user) return false;
  if (user.is_superuser) return false;
  const r = normalizeRol(user);
  return r === 'secretaria' || r === 'enfermeria';
}

/** Cualquier acceso al área LIMS (completo o restringido). */
export function canAccessLimsAny(user: User | null): boolean {
  return canAccessLimsModule(user) || canAccessLimsOperativaLimitada(user);
}

/** Pendientes y órdenes LIMS en sidebar/rutas. */
export function canAccessLimsPendientes(user: User | null): boolean {
  return canAccessLimsAny(user);
}

export function canAccessLimsOrdenes(user: User | null): boolean {
  return canAccessLimsAny(user);
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

/** Operaciones de laboratorio sobre orden/muestra/resultados (admin + laboratorio). */
export function canOperateLims(user: User | null): boolean {
  if (!user) return false;
  if (user.is_superuser) return true;
  const r = normalizeRol(user);
  return r === 'admin' || r === 'laboratorio';
}

/** Enviar informe al paciente (admin y laboratorio). */
export function canEnviarInformeLims(user: User | null): boolean {
  return canOperateLims(user);
}

/** @deprecated Usar canEnviarInformeLims */
export function canFinalizarOrdenLims(user: User | null): boolean {
  return canEnviarInformeLims(user);
}

/** @deprecated Usar canFinalizarOrdenLims */
export function canValidarOrdenLims(user: User | null): boolean {
  return canFinalizarOrdenLims(user);
}

/** Descargar informe PDF LIMS (PDF-1-FE): operadores completos o roles limitados en órdenes finalizadas. */
export function canDownloadInformeLimsPdf(
  user: User | null,
  estado?: string | null
): boolean {
  if (canAccessLimsModule(user)) return true;
  if (isLimsOperativaLimitada(user)) {
    return String(estado || '').toUpperCase() === 'FINALIZADO';
  }
  return false;
}

/** Misma visibilidad que órdenes LIMS (admin, laboratorio, médico lectura). */
export function canAccessMicrobiologia(user: User | null): boolean {
  return canAccessLimsModule(user);
}

export function canOperateMicrobiologia(user: User | null): boolean {
  return canOperateLims(user);
}

/** Validar informe microbiológico final (solo admin). */
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

/** Catálogos LIMS generales (tipos de muestra): escritura admin y laboratorio. */
export function canEditLimsCatalogos(user: User | null): boolean {
  return canOperateLims(user);
}

/** Catálogos micro: escritura solo admin. */
export function canEditMicroCatalogos(user: User | null): boolean {
  if (!user) return false;
  if (user.is_superuser) return true;
  return normalizeRol(user) === 'admin';
}
