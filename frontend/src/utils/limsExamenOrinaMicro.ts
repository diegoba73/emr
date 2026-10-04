/**
 * Campos de tira + sedimento en urocultivo (misma muestra del cultivo).
 * Códigos alineados a ORI_* del catálogo de orina completa.
 */
export const CAMPOS_TIRA_ORINA = [
  { codigo: 'ORI_COLOR', label: 'Color' },
  { codigo: 'ORI_ASP', label: 'Aspecto' },
  { codigo: 'ORI_DENS', label: 'Densidad' },
  { codigo: 'ORI_PH', label: 'pH' },
  { codigo: 'ORI_GLU', label: 'Glucosa' },
  { codigo: 'ORI_BIL', label: 'Bilirrubina' },
  { codigo: 'ORI_NIT', label: 'Nitritos' },
  { codigo: 'ORI_CET', label: 'C. cetónicos' },
] as const;

export const CAMPOS_SEDIMENTO_ORINA = [
  { codigo: 'ORI_CEL', label: 'Células' },
  { codigo: 'ORI_LEU', label: 'Leucocitos' },
  { codigo: 'ORI_HEM', label: 'Hematíes' },
  { codigo: 'ORI_PIO', label: 'Piocitos' },
  { codigo: 'ORI_MUC', label: 'Mucus' },
  { codigo: 'ORI_CRIS', label: 'Cristales' },
  { codigo: 'ORI_CONC', label: 'Conclusión' },
] as const;

export type CodigoExamenOrinaMicro =
  | (typeof CAMPOS_TIRA_ORINA)[number]['codigo']
  | (typeof CAMPOS_SEDIMENTO_ORINA)[number]['codigo'];

export type ExamenOrinaMicro = Record<CodigoExamenOrinaMicro, string>;

/** Tira + sedimento cualitativos (no color/aspecto/densidad/pH/conclusión). */
export const VALOR_NO_CONTIENE = 'NO CONTIENE';
export const CODIGOS_DEFAULT_NO_CONTIENE = new Set<CodigoExamenOrinaMicro>([
  'ORI_GLU',
  'ORI_BIL',
  'ORI_NIT',
  'ORI_CET',
  'ORI_LEU',
  'ORI_HEM',
  'ORI_CEL',
  'ORI_PIO',
  'ORI_MUC',
  'ORI_CRIS',
]);

export function examenOrinaVacio(): ExamenOrinaMicro {
  const out = {} as ExamenOrinaMicro;
  for (const c of [...CAMPOS_TIRA_ORINA, ...CAMPOS_SEDIMENTO_ORINA]) {
    out[c.codigo] = CODIGOS_DEFAULT_NO_CONTIENE.has(c.codigo)
      ? VALOR_NO_CONTIENE
      : '';
  }
  return out;
}

export function normalizarExamenOrina(raw: unknown): ExamenOrinaMicro {
  const base = examenOrinaVacio();
  if (!raw || typeof raw !== 'object') return base;
  const obj = raw as Record<string, unknown>;
  for (const key of Object.keys(base) as CodigoExamenOrinaMicro[]) {
    const val = obj[key];
    if (val == null) continue;
    base[key] = String(val).trim();
  }
  return base;
}

export function estudioAdmiteExamenOrina(estudio: {
  admite_examen_orina?: boolean;
  tipo_estudio?: string | null;
  tipo_cultivo_nombre?: string | null;
}): boolean {
  if (typeof estudio.admite_examen_orina === 'boolean') {
    return estudio.admite_examen_orina;
  }
  const tipo = (estudio.tipo_estudio || '').toUpperCase();
  return tipo === 'UROCULTIVO';
}
