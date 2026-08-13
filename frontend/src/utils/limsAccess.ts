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
  return (
    r === 'admin' ||
    r === 'secretaria' ||
    r === 'medico' ||
    r === 'paciente' ||
    r === 'enfermeria'
  );
}

/**
 * Ver valores de resultados en portal clínico.
 * Lab/bioquímico/admin (módulo LIMS): siempre.
 * Resto: solo orden FINALIZADO (validada).
 */
export function canSeeResultadosClinicos(
  user: User | null,
  estado: string | null | undefined
): boolean {
  if (!user) return false;
  if (canAccessLimsModule(user)) return true;
  if (!canAccessAnalisisClinicoLab(user)) return false;
  return String(estado || '').toUpperCase() === 'FINALIZADO';
}

/** Descargar informe PDF desde el portal clínico (solo orden validada / FINALIZADO). */
export function canDownloadInformeClinicoPdf(
  user: User | null,
  estado?: string | null
): boolean {
  if (!user) return false;
  if (user.is_superuser) return true;
  const r = normalizeRol(user);
  const roleOk =
    r === 'admin' ||
    r === 'medico' ||
    r === 'paciente' ||
    r === 'secretaria' ||
    r === 'enfermeria';
  if (!roleOk) return false;
  if (estado == null || estado === undefined) return true;
  return String(estado).toUpperCase() === 'FINALIZADO';
}

/** Operaciones de laboratorio sobre orden/muestra/resultados (admin + operadores). */
export function canOperateLims(user: User | null): boolean {
  if (!user) return false;
  if (user.is_superuser) return true;
  const r = normalizeRol(user);
  return r === 'admin' || isOperadorLimsRole(r);
}

/** Enviar informe al paciente/médico: operadores LIMS y secretaría, solo FINALIZADO. */
export function canEnviarInformeLims(
  user: User | null,
  estado?: string | null
): boolean {
  if (!user) return false;
  if (user.is_superuser) return true;
  const r = normalizeRol(user);
  const roleOk = r === 'admin' || r === 'secretaria' || isOperadorLimsRole(r);
  if (!roleOk) return false;
  if (estado == null || estado === undefined) return true;
  return String(estado).toUpperCase() === 'FINALIZADO';
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

/** Descargar informe PDF LIMS: solo tras validación (FINALIZADO). */
export function canDownloadInformeLimsPdf(
  user: User | null,
  estado?: string | null
): boolean {
  if (!canAccessLimsModule(user)) return false;
  if (estado == null || estado === undefined) return false;
  return String(estado).toUpperCase() === 'FINALIZADO';
}

/** Misma visibilidad que el módulo LIMS (admin, laboratorio, bioquímico). */
export function canAccessMicrobiologia(user: User | null): boolean {
  return canAccessLimsModule(user);
}

/**
 * Lectura de pedidos/estudios de microbiología:
 * - LIMS (operadores/admin): todos
 * - Médico: los propios / de pacientes vinculados (filtra el API)
 * No habilita el menú LIMS completo ni operaciones técnicas.
 */
export function canAccessMicrobiologiaLectura(user: User | null): boolean {
  if (!user) return false;
  if (user.is_superuser) return true;
  const r = normalizeRol(user);
  return (
    r === 'admin' ||
    r === 'medico' ||
    r === 'secretaria' ||
    r === 'enfermeria' ||
    isOperadorLimsRole(r)
  );
}

export function canOperateMicrobiologia(user: User | null): boolean {
  return canOperateLims(user);
}

/** Validar informe microbiológico final (bioquímico / admin). */
export function canValidarInformeMicro(user: User | null): boolean {
  return canValidarOrdenLims(user);
}

/**
 * Crear / completar (emitir) / anular informes de microbiología.
 * Solo bioquímico y admin — el técnico no opera esta pestaña.
 */
export function canOperateInformeMicro(user: User | null): boolean {
  return canValidarOrdenLims(user);
}

/**
 * Ver contenido de un informe micro.
 * Bio/admin: siempre. Resto (lab, médico): solo VALIDADO.
 */
export function canSeeInformeMicro(
  user: User | null,
  estadoInforme: string | null | undefined
): boolean {
  if (!user) return false;
  if (canOperateInformeMicro(user)) return true;
  if (!canAccessMicrobiologiaLectura(user)) return false;
  return String(estadoInforme || '').toUpperCase() === 'VALIDADO';
}

/**
 * Descargar PDF de informe micro.
 * Bio/admin: EMITIDO o VALIDADO (revisión previa).
 * Lab / médico: solo cuando el estudio/informe está VALIDADO (o INFORMADO).
 */
export function canDownloadInformeMicroPdf(
  user: User | null,
  estadoEstudio?: string | null
): boolean {
  if (!canAccessMicrobiologiaLectura(user)) return false;
  if (canOperateInformeMicro(user)) {
    if (estadoEstudio == null || estadoEstudio === undefined) return true;
    const e = String(estadoEstudio).toUpperCase();
    return (
      e === 'EMITIDO' ||
      e === 'LISTO_PARA_VALIDAR' ||
      e === 'VALIDADO' ||
      e === 'INFORMADO'
    );
  }
  if (estadoEstudio == null || estadoEstudio === undefined) return false;
  const e = String(estadoEstudio).toUpperCase();
  return e === 'VALIDADO' || e === 'INFORMADO';
}

/** Enviar informe micro por email/WhatsApp (operadores LIMS y secretaría, solo tras VALIDADO). */
export function canEnviarInformeMicro(
  user: User | null,
  estadoEstudio?: string | null
): boolean {
  if (!user) return false;
  if (user.is_superuser) return true;
  const r = normalizeRol(user);
  const roleOk = r === 'admin' || r === 'secretaria' || isOperadorLimsRole(r);
  if (!roleOk) return false;
  if (estadoEstudio == null || estadoEstudio === undefined) return true;
  const e = String(estadoEstudio).toUpperCase();
  return e === 'VALIDADO' || e === 'INFORMADO';
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

/** Inventario de laboratorio (admin, laboratorio, bioquímico). */
export function canAccessInventarioLab(user: User | null): boolean {
  return canAccessLimsModule(user);
}

/** Control de calidad Westgard (admin, laboratorio, bioquímico). */
export function canAccessQcLab(user: User | null): boolean {
  return canAccessLimsModule(user);
}
