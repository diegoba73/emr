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
 * Secretaría/enfermería consultan resultados en /solicitudes.
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

/** Detalle de orden visible para roles restringidos: PENDIENTE / FINALIZADO / CANCELADO. */
export function canAccessLimsOrdenDetalle(
  user: User | null,
  estado: string | null | undefined
): boolean {
  if (!canAccessLimsAny(user)) return false;
  if (!isLimsOperativaLimitada(user)) return true;
  const e = String(estado || '').toUpperCase();
  return e === 'PENDIENTE' || e === 'FINALIZADO' || e === 'CANCELADO';
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
 * Filtros avanzados / listados de estudio (cohorte por exámenes + Excel).
 * Lab/bioquímico/admin y médico.
 */
export function canAccessFiltrosAvanzados(user: User | null): boolean {
  if (!user) return false;
  if (user.is_superuser) return true;
  const r = normalizeRol(user);
  return r === 'admin' || r === 'medico' || isOperadorLimsRole(r);
}

/**
 * Puede abrir el detalle de una orden (módulo LIMS o portal clínico /solicitudes).
 * No habilita el listado operativo ni mutaciones de laboratorio.
 */
export function canOpenDetalleOrdenLab(user: User | null): boolean {
  return canAccessLimsModule(user) || canAccessAnalisisClinicoLab(user);
}

/** Ruta de detalle según rol: operadores LIMS vs lectura clínica. */
export function pathDetalleOrdenLab(user: User | null, ordenId: number): string {
  if (canAccessLimsModule(user)) {
    return `/laboratorio/ordenes/${ordenId}`;
  }
  return `/solicitudes/${ordenId}`;
}

/** Detalle de estudio de microbiología (misma ruta para operadores y lectura clínica). */
export function pathDetalleEstudioMicro(estudioId: number): string {
  return `/laboratorio/microbiologia/estudios/${estudioId}`;
}

/**
 * Compatibilidad con pantallas anteriores: secretaría tiene lectura clínica completa.
 */
export function isSecretariaEntregaLab(_user: User | null): boolean {
  return false;
}

/**
 * Ver valores de resultados en portal clínico.
 * Secretaría y enfermería pueden consultar los valores.
 */
export function canSeeResultadosClinicos(
  user: User | null,
  _estado?: string | null
): boolean {
  if (!user) return false;
  if (isSecretariaEntregaLab(user)) return false;
  if (canAccessLimsModule(user)) return true;
  return canAccessAnalisisClinicoLab(user);
}

/** Roles que pueden PDF/enviar informe parcial (no paciente ni enfermería). */
function rolInformeParcial(user: User | null): boolean {
  if (!user) return false;
  if (user.is_superuser) return true;
  const r = normalizeRol(user);
  return (
    r === 'admin' ||
    r === 'medico' ||
    r === 'secretaria' ||
    isOperadorLimsRole(r)
  );
}

/** Descargar PDF clínico: FINALIZADO (lectura clínica) o INFORMADO_PARCIAL (roles parcial). */
export function canDownloadInformeClinicoPdf(
  user: User | null,
  estado?: string | null
): boolean {
  if (!user) return false;
  if (user.is_superuser) return true;
  const e = estado == null || estado === undefined ? null : String(estado).toUpperCase();
  if (e === 'INFORMADO_PARCIAL') {
    return rolInformeParcial(user);
  }
  const r = normalizeRol(user);
  const roleOk =
    r === 'admin' ||
    r === 'medico' ||
    r === 'paciente' ||
    r === 'secretaria' ||
    r === 'enfermeria';
  if (!roleOk) return false;
  if (e == null) return true;
  return e === 'FINALIZADO';
}

/** Operaciones de laboratorio sobre orden/muestra/resultados (admin + operadores). */
export function canOperateLims(user: User | null): boolean {
  if (!user) return false;
  if (user.is_superuser) return true;
  const r = normalizeRol(user);
  return r === 'admin' || isOperadorLimsRole(r);
}

/** Enviar informe: FINALIZADO (LIMS+secretaría) o INFORMADO_PARCIAL (roles parcial). */
export function canEnviarInformeLims(
  user: User | null,
  estado?: string | null
): boolean {
  if (!user) return false;
  if (user.is_superuser) return true;
  const e = estado == null || estado === undefined ? null : String(estado).toUpperCase();
  if (e === 'INFORMADO_PARCIAL') {
    return rolInformeParcial(user);
  }
  const r = normalizeRol(user);
  const roleOk = r === 'admin' || r === 'secretaria' || isOperadorLimsRole(r);
  if (!roleOk) return false;
  if (e == null) return true;
  return e === 'FINALIZADO';
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

/** Descargar PDF LIMS: FINALIZADO o INFORMADO_PARCIAL. */
export function canDownloadInformeLimsPdf(
  user: User | null,
  estado?: string | null
): boolean {
  if (!canAccessLimsModule(user)) return false;
  if (estado == null || estado === undefined) return false;
  const e = String(estado).toUpperCase();
  return e === 'FINALIZADO' || e === 'INFORMADO_PARCIAL';
}

/** Operación LIMS de microbiología (admin, laboratorio, bioquímico). */
export function canAccessMicrobiologia(user: User | null): boolean {
  return canAccessLimsModule(user);
}

/**
 * Listado «Microbiología» en sidebar/ruta de estudios:
 * operadores LIMS (todos los estados) + médico (solo liberados; filtra el API).
 * No habilita catálogos ni operaciones técnicas.
 */
export function canAccessMicrobiologiaListado(user: User | null): boolean {
  if (!user) return false;
  if (canAccessMicrobiologia(user)) return true;
  return normalizeRol(user) === 'medico';
}

/**
 * Lectura de pedidos/estudios de microbiología:
 * - LIMS (operadores/admin): todos
 * - Médico / secretaría / enfermería: lectura clínica (detalle / portal)
 * No habilita catálogos ni operaciones técnicas.
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

/**
 * Pedido clínico de microbiología (alta de estudio por paciente+cultivo).
 * Operadores LIMS y médico. No habilita siembras/lecturas/catálogos.
 */
export function canCreatePedidoMicrobiologia(user: User | null): boolean {
  if (!user) return false;
  if (canOperateMicrobiologia(user)) return true;
  return normalizeRol(user) === 'medico';
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
 * Bio/admin: siempre. Roles parcial: VALIDADO o PRELIMINAR EMITIDO.
 * Enfermería: solo VALIDADO.
 */
export function canSeeInformeMicro(
  user: User | null,
  estadoInforme: string | null | undefined,
  tipoInforme?: string | null
): boolean {
  if (!user) return false;
  if (isSecretariaEntregaLab(user)) return false;
  if (canOperateInformeMicro(user)) return true;
  if (!canAccessMicrobiologiaLectura(user)) return false;
  const e = String(estadoInforme || '').toUpperCase();
  const t = String(tipoInforme || '').toUpperCase();
  if (e === 'VALIDADO') return true;
  if (e === 'EMITIDO' && t === 'PRELIMINAR') {
    return rolInformeParcial(user);
  }
  return false;
}

/**
 * Descargar PDF micro.
 * Definitivo: VALIDADO/INFORMADO (clínico) o EMITIDO+ (bio).
 * Preliminar: cualquier estudio no cancelado si el rol es de parcial
 * (el backend elige PRELIMINAR EMITIDO si no hay FINAL).
 */
export function canDownloadInformeMicroPdf(
  user: User | null,
  estadoEstudio?: string | null,
  opts?: { tienePreliminarEmitido?: boolean; tieneFinalValidado?: boolean }
): boolean {
  if (!canAccessMicrobiologiaLectura(user)) return false;
  const e = estadoEstudio == null ? null : String(estadoEstudio).toUpperCase();
  if (e === 'CANCELADO') return false;

  if (opts?.tieneFinalValidado) {
    if (canOperateInformeMicro(user)) return true;
    return e === 'VALIDADO' || e === 'INFORMADO' || e == null;
  }
  if (opts?.tienePreliminarEmitido && rolInformeParcial(user)) {
    return true;
  }

  if (canOperateInformeMicro(user)) {
    if (e == null) return true;
    return (
      e === 'EMITIDO' ||
      e === 'LISTO_PARA_VALIDAR' ||
      e === 'VALIDADO' ||
      e === 'INFORMADO' ||
      e === 'RECIBIDO' ||
      e === 'SEMBRADO' ||
      e === 'LECTURA_PRELIMINAR' ||
      e === 'IDENTIFICACION' ||
      e === 'ANTIBIOGRAMA'
    );
  }
  if (e == null) return false;
  return e === 'VALIDADO' || e === 'INFORMADO';
}

/** Enviar informe micro: FINAL VALIDADO (LIMS+secretaría) o preliminar (roles parcial). */
export function canEnviarInformeMicro(
  user: User | null,
  estadoEstudio?: string | null,
  opts?: { tienePreliminarEmitido?: boolean; tieneFinalValidado?: boolean }
): boolean {
  if (!user) return false;
  if (user.is_superuser) return true;
  const e = estadoEstudio == null ? null : String(estadoEstudio).toUpperCase();
  if (opts?.tieneFinalValidado || e === 'VALIDADO' || e === 'INFORMADO') {
    const r = normalizeRol(user);
    return r === 'admin' || r === 'secretaria' || isOperadorLimsRole(r);
  }
  if (opts?.tienePreliminarEmitido) {
    return rolInformeParcial(user);
  }
  return false;
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

/** Reabrir (desvalidar) estudio micro: bioquímico/admin en VALIDADO o INFORMADO. */
export function estudioMicroPuedeDesvalidar(estado: string | null | undefined): boolean {
  if (!estado) return false;
  const e = String(estado).toUpperCase();
  return e === 'VALIDADO' || e === 'INFORMADO';
}

/** Catálogos LIMS generales (tipos de muestra): escritura admin y operadores. */
export function canEditLimsCatalogos(user: User | null): boolean {
  return canOperateLims(user);
}

/** Catálogos micro (medios, microorganismos, antibióticos): admin y operadores LIMS. */
export function canEditMicroCatalogos(user: User | null): boolean {
  return canOperateLims(user);
}

/** Inventario de laboratorio (admin, laboratorio, bioquímico). */
export function canAccessInventarioLab(user: User | null): boolean {
  return canAccessLimsModule(user);
}

/** Control de calidad Westgard (admin, laboratorio, bioquímico). */
export function canAccessQcLab(user: User | null): boolean {
  return canAccessLimsModule(user);
}
