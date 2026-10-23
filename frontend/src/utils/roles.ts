/** Roles de aplicación — alineados con `usuarios.roles` (backend). */

export const ROLES_ESTUDIO_COMPLEMENTARIO = [
  'kinesiologo',
  'radiologo',
  'ecografista',
  'fonoaudiologo',
] as const;

export type RolEstudioComplementario = (typeof ROLES_ESTUDIO_COMPLEMENTARIO)[number];

/** Técnico y bioquímico: misma operación LIMS; solo el bioquímico valida. */
export const ROLES_LIMS_OPERADOR = ['laboratorio', 'bioquimico'] as const;

export type RolLimsOperador = (typeof ROLES_LIMS_OPERADOR)[number];

export const ROLES_LECTURA_OPERATIVA = [...ROLES_LIMS_OPERADOR, ...ROLES_ESTUDIO_COMPLEMENTARIO] as const;

export function normalizeRolValue(rol?: string | null): string {
  return (rol || '').toLowerCase();
}

export function isProfesionalEstudioRole(rol?: string | null): boolean {
  return ROLES_ESTUDIO_COMPLEMENTARIO.includes(
    normalizeRolValue(rol) as RolEstudioComplementario
  );
}

export function isLecturaOperativaRole(rol?: string | null): boolean {
  const r = normalizeRolValue(rol);
  return (ROLES_LECTURA_OPERATIVA as readonly string[]).includes(r);
}

export function isOperadorLimsRole(rol?: string | null): boolean {
  const r = normalizeRolValue(rol);
  return (ROLES_LIMS_OPERADOR as readonly string[]).includes(r);
}

export function puedeValidarLimsRole(rol?: string | null): boolean {
  const r = normalizeRolValue(rol);
  return r === 'admin' || r === 'bioquimico';
}

/** Secretaría institucional: agenda EMR, recepción, guardia, estudios, archivos. */
export const ROLES_SECRETARIA_INSTITUCIONAL = ['secretaria'] as const;

export type RolSecretariaInstitucional = (typeof ROLES_SECRETARIA_INSTITUCIONAL)[number];

/** Secretaría de laboratorio: menú LIMS + Estadísticas; permisos = EMR secretaría + LIMS write. */
export const ROLES_SECRETARIA_LAB = ['secretaria_lab'] as const;

export type RolSecretariaLab = (typeof ROLES_SECRETARIA_LAB)[number];

/** Ambas secretarías: pacientes/médicos/profesionales y capacidades compartidas. */
export const ROLES_SECRETARIA_EMR = [
  ...ROLES_SECRETARIA_INSTITUCIONAL,
  ...ROLES_SECRETARIA_LAB,
] as const;

export type RolSecretariaEmr = (typeof ROLES_SECRETARIA_EMR)[number];

/** Escritura LIMS (sin validar): operadores + secretaría lab + admin vía callers. */
export const ROLES_LIMS_WRITE = ['admin', 'laboratorio', 'bioquimico', 'secretaria_lab'] as const;

/** Ambas secretarías: ver/bajar/enviar informes liberados (FINALIZADO / VALIDADO). */
export const ROLES_SECRETARIA_ENTREGA_INFORME = [...ROLES_SECRETARIA_EMR] as const;

export function isSecretariaInstitucionalRole(rol?: string | null): boolean {
  return (ROLES_SECRETARIA_INSTITUCIONAL as readonly string[]).includes(normalizeRolValue(rol));
}

export function isSecretariaEmrRole(rol?: string | null): boolean {
  return (ROLES_SECRETARIA_EMR as readonly string[]).includes(normalizeRolValue(rol));
}

export function isSecretariaLabRole(rol?: string | null): boolean {
  return (ROLES_SECRETARIA_LAB as readonly string[]).includes(normalizeRolValue(rol));
}

export function isSecretariaEntregaInformeRole(rol?: string | null): boolean {
  return (ROLES_SECRETARIA_ENTREGA_INFORME as readonly string[]).includes(normalizeRolValue(rol));
}

export function puedeEscribirLimsRole(rol?: string | null): boolean {
  return (ROLES_LIMS_WRITE as readonly string[]).includes(normalizeRolValue(rol));
}

