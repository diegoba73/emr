/** Roles de aplicación — alineados con `usuarios.roles` (backend). */

export const ROLES_ESTUDIO_COMPLEMENTARIO = [
  'kinesiologo',
  'radiologo',
  'ecografista',
  'fonoaudiologo',
] as const;

export type RolEstudioComplementario = (typeof ROLES_ESTUDIO_COMPLEMENTARIO)[number];

export const ROLES_LECTURA_OPERATIVA = ['laboratorio', ...ROLES_ESTUDIO_COMPLEMENTARIO] as const;

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
