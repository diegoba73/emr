/**
 * Examen microscópico directo del cultivo.
 * Apartado general con técnicas: fresco / Gram / KOH / parasitológico.
 */

export type TecnicaExamenDirecto = 'fresco' | 'gram' | 'koh' | 'parasito';

export type CampoExamenDirecto = { codigo: string; label: string };

export type SeccionExamenDirecto = {
  tecnica: TecnicaExamenDirecto;
  tituloUi: string;
  campos: readonly CampoExamenDirecto[];
};

export const CAMPOS_FRESCO_GENITAL: readonly CampoExamenDirecto[] = [
  { codigo: 'EXF_CEL', label: 'Células' },
  { codigo: 'EXF_HEM', label: 'Hematíes' },
  { codigo: 'EXF_LEU', label: 'Leucocitos' },
  { codigo: 'EXF_TRICH', label: 'Trichomonas Spp.' },
];

export const CAMPOS_FRESCO_LIQUIDO: readonly CampoExamenDirecto[] = [
  { codigo: 'EXF_ASP', label: 'Aspecto' },
  { codigo: 'EXF_CEL', label: 'Células' },
  { codigo: 'EXF_HEM', label: 'Hematíes' },
  { codigo: 'EXF_LEU', label: 'Leucocitos' },
];

export const CAMPOS_GRAM: readonly CampoExamenDirecto[] = [
  { codigo: 'EXF_GRAM', label: 'Tinción de Gram' },
];

export const CAMPOS_KOH: readonly CampoExamenDirecto[] = [
  { codigo: 'EXF_MICOL', label: 'Examen micológico (KOH)' },
];

export const CAMPOS_PARASITO: readonly CampoExamenDirecto[] = [
  { codigo: 'EXF_PAR_MACRO', label: 'Examen macroscópico' },
  { codigo: 'EXF_PAR_MICRO', label: 'Examen microscópico' },
  { codigo: 'EXF_PAR_PROTO', label: 'Protozoarios' },
  { codigo: 'EXF_PAR_HELM', label: 'Helmintos (huevos / larvas)' },
];

const TITULO_TECNICA: Record<TecnicaExamenDirecto, string> = {
  fresco: 'Examen en fresco',
  gram: 'Tinción de Gram',
  koh: 'Examen micológico (KOH)',
  parasito: 'Examen parasitológico',
};

function sec(
  tecnica: TecnicaExamenDirecto,
  campos: readonly CampoExamenDirecto[]
): SeccionExamenDirecto {
  return { tecnica, tituloUi: TITULO_TECNICA[tecnica], campos };
}

const CULTIVO_A_SECCIONES: Record<string, readonly SeccionExamenDirecto[]> = {
  VAGINAL: [sec('fresco', CAMPOS_FRESCO_GENITAL), sec('koh', CAMPOS_KOH)],
  URETRAL: [sec('fresco', CAMPOS_FRESCO_GENITAL), sec('koh', CAMPOS_KOH)],
  COPROCULTIVO: [sec('parasito', CAMPOS_PARASITO)],
  HONGOS_ESCAMAS: [sec('koh', CAMPOS_KOH)],
  HONGOS_PELOS: [sec('koh', CAMPOS_KOH)],
  HONGOS_UNAS: [sec('koh', CAMPOS_KOH)],
  LCR: [sec('fresco', CAMPOS_FRESCO_LIQUIDO), sec('gram', CAMPOS_GRAM)],
  LIQUIDO_PLEURAL: [sec('fresco', CAMPOS_FRESCO_LIQUIDO), sec('gram', CAMPOS_GRAM)],
  LIQUIDO_ASCITICO: [sec('fresco', CAMPOS_FRESCO_LIQUIDO), sec('gram', CAMPOS_GRAM)],
  LIQUIDO_PERITONEAL: [sec('fresco', CAMPOS_FRESCO_LIQUIDO), sec('gram', CAMPOS_GRAM)],
  LIQUIDO_SINOVIAL: [sec('fresco', CAMPOS_FRESCO_LIQUIDO), sec('gram', CAMPOS_GRAM)],
  ESPUTO: [sec('gram', CAMPOS_GRAM)],
  ASPIRADO_TRAQUEAL_BRONQUIAL: [sec('gram', CAMPOS_GRAM)],
  HERIDA_ABSCESO: [sec('gram', CAMPOS_GRAM)],
  PIEL_PARTES_BLANDAS: [sec('gram', CAMPOS_GRAM)],
  NASOFARINGEO: [sec('gram', CAMPOS_GRAM)],
  HEMOCULTIVO: [sec('gram', CAMPOS_GRAM)],
};

const _allCamposMap = new Map<string, string>();
for (const secs of Object.values(CULTIVO_A_SECCIONES)) {
  for (const s of secs) {
    for (const c of s.campos) {
      if (!_allCamposMap.has(c.codigo)) _allCamposMap.set(c.codigo, c.label);
    }
  }
}

export const CAMPOS_EXAMEN_FRESCO = Array.from(_allCamposMap.entries()).map(([codigo, label]) => ({
  codigo,
  label,
}));

export type ExamenFrescoMicro = Record<string, string>;

export const TITULO_APARTADO_UI = 'Examen microscópico directo';

export function seccionesExamenDirecto(estudio: {
  tipo_estudio?: string | null;
}): readonly SeccionExamenDirecto[] {
  const tipo = (estudio.tipo_estudio || '').toUpperCase();
  return CULTIVO_A_SECCIONES[tipo] ?? [];
}

export function camposExamenFrescoPara(estudio: {
  tipo_estudio?: string | null;
}): readonly CampoExamenDirecto[] {
  const out: CampoExamenDirecto[] = [];
  const seen = new Set<string>();
  for (const s of seccionesExamenDirecto(estudio)) {
    for (const c of s.campos) {
      if (seen.has(c.codigo)) continue;
      seen.add(c.codigo);
      out.push(c);
    }
  }
  return out;
}

export function tituloUiExamenFresco(_estudio?: { tipo_estudio?: string | null }): string {
  return TITULO_APARTADO_UI;
}

export function examenFrescoVacio(): ExamenFrescoMicro {
  const out: ExamenFrescoMicro = {};
  for (const c of CAMPOS_EXAMEN_FRESCO) {
    out[c.codigo] = '';
  }
  return out;
}

export function normalizarExamenFresco(raw: unknown): ExamenFrescoMicro {
  const base = examenFrescoVacio();
  if (!raw || typeof raw !== 'object') return base;
  const obj = raw as Record<string, unknown>;
  for (const key of Object.keys(base)) {
    const val = obj[key];
    if (val == null) continue;
    base[key] = String(val).trim();
  }
  return base;
}

export function estudioAdmiteExamenFresco(estudio: {
  admite_examen_fresco?: boolean;
  tipo_estudio?: string | null;
}): boolean {
  if (typeof estudio.admite_examen_fresco === 'boolean') {
    return estudio.admite_examen_fresco;
  }
  return seccionesExamenDirecto(estudio).length > 0;
}
