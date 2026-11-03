/** Sedes CEHTA / ICPL — espejo de `usuarios.sedes` (backend). */

export const SEDE_CEHTA = 'CEHTA' as const;
export const SEDE_ICPL = 'ICPL' as const;
export const SEDES = [SEDE_CEHTA, SEDE_ICPL] as const;
export type SedeCodigo = (typeof SEDES)[number];

export const SEDE_CAPACIDADES: Record<
  SedeCodigo,
  { guardia: boolean; internacion: boolean; recepcion: boolean; agenda: boolean }
> = {
  CEHTA: { guardia: false, internacion: false, recepcion: true, agenda: true },
  ICPL: { guardia: true, internacion: true, recepcion: true, agenda: true },
};

export function normalizeSedes(raw?: string[] | null): SedeCodigo[] {
  if (!raw?.length) return [];
  const out: SedeCodigo[] = [];
  for (const item of raw) {
    const s = String(item || '').trim().toUpperCase();
    if ((SEDES as readonly string[]).includes(s) && !out.includes(s as SedeCodigo)) {
      out.push(s as SedeCodigo);
    }
  }
  return out;
}

/** Sedes que restringen. `null` = sin filtro (admin o sedes vacías). */
export function userSedesEfectivas(user: {
  is_superuser?: boolean;
  rol?: string | null;
  sedes?: string[] | null;
} | null): SedeCodigo[] | null {
  if (!user) return null;
  if (user.is_superuser) return null;
  const rol = String(user.rol || '').toLowerCase();
  if (rol === 'admin') return null;
  const sedes = normalizeSedes(user.sedes);
  if (!sedes.length) return null;
  return sedes;
}

export function userHasCapacidad(
  user: { is_superuser?: boolean; rol?: string | null; sedes?: string[] | null } | null,
  capacidad: 'guardia' | 'internacion' | 'recepcion' | 'agenda'
): boolean {
  const sedes = userSedesEfectivas(user);
  if (sedes === null) return true;
  return sedes.some((s) => Boolean(SEDE_CAPACIDADES[s]?.[capacidad]));
}
