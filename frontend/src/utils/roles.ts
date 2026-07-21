/** Roles de aplicación — alineados con `usuarios.roles` (backend). */

export const ROLES_ESTUDIO_COMPLEMENTARIO = [
  'kinesiologo',
  'radiologo',
  'ecografista',
  'fonoaudiologo',
] as const;

export type RolEstudioComplementario = (typeof ROLES_ESTUDIO_COMPLEMENTARIO)[number];

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
