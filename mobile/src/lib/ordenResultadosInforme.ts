/**
 * Orden de grupos en el informe móvil (= PDF / web).
 * Copia acotada de frontend limsOrdenInforme + limsResultadosPanel.
 */
import type { ResultadoMovil } from './types';

export const PANEL_ORINA_COMPLETA = 'PAN_ORI';

const PANELES_ORINA = new Set([
  'PAN_ORI',
  'PAN_IONO_U',
  'PAN_IONO_U24',
  'PAN_MALB_AZ',
  'PAN_MALB24',
  'PAN_CLEAR',
]);

const CODIGOS_ORINA_SUELTOS = new Set(['PROT_U_24', 'PROT_U_AZ']);
const MUESTRAS_ORINA = new Set(['ORINA', 'ORINA_24_H']);

/** Fila a fila (izq → der) del formulario papel «Solicitud de análisis». */
export const ORDEN_FORMULARIO_PAPEL: string[] = [
  'PAN_HEMO', 'CPK', 'HBA1C', 'CPK_MB', 'GLU', 'TROP_I', 'UREA', 'MIOG', 'CREATI', 'TROP_US',
  'AU', 'PROBNP', 'CA', 'DDIM', 'MG', 'PAN_ORI', 'P', 'PAN_CLEAR', 'PAN_FERR', 'PAN_IONO_U24',
  'PAN_IONO', 'PAN_IONO_U', 'CL', 'PROT_U_24', 'CA_ION', 'PROT_U_AZ', 'PAN_LIP', 'PAN_MALB24',
  'PAN_HEP', 'PAN_MALB_AZ', 'PROT_T', 'PAN_ELP', 'ALB', 'LPA', 'PAN_COAG', 'PSA', 'INR', 'TSH',
  'VSG', 'T3', 'PCR_US', 'T4', 'AMIL', 'T4L', 'LIP', 'B12', 'GGT', 'VITD', 'LDH', 'PAN_EAB_ART',
  'HBVAGS', 'PAN_EAB_VEN', 'HCVG', 'LACT', 'HIVAC', 'HCGB', 'SANOC', 'ASTO', 'GRUPO',
];

const ORDEN_PAPEL_RANK = new Map(ORDEN_FORMULARIO_PAPEL.map((c, i) => [c, i]));

const PERFILES_POR_CODIGO: ReadonlyArray<{
  codigo: string;
  nombre: string;
  examenes: readonly string[];
}> = [
  {
    codigo: 'PAN_HEMO',
    nombre: 'Hemograma',
    examenes: [
      'HEMATIES', 'HTO', 'HGB', 'RDW', 'VCM', 'HCM', 'CHCM', 'PLAQ', 'LEUCO',
      'NEUT_CAY', 'NEUT_SEG', 'EOS', 'BAS', 'LINF', 'MONO',
    ],
  },
  {
    codigo: 'PAN_EAB_ART',
    nombre: 'EAB arterial',
    examenes: ['PH_ART', 'PO2_ART', 'PCO2_ART', 'SAT_O2_ART', 'HCO3_ART', 'BE_ART'],
  },
  {
    codigo: 'PAN_EAB_VEN',
    nombre: 'EAB venoso',
    examenes: ['PH_VEN', 'PO2_VEN', 'PCO2_VEN', 'SAT_O2_VEN', 'HCO3_VEN', 'BE_VEN'],
  },
  {
    codigo: 'PAN_IONO',
    nombre: 'Ionograma plasmático',
    examenes: ['NA', 'K', 'CL'],
  },
  {
    codigo: 'PAN_LIP',
    nombre: 'Perfil lipídico',
    examenes: [
      'COL_TOT', 'LDL', 'VLDL', 'HDL', 'TG', 'COL_NO_LDL', 'COL_RESID', 'RATIO_CT_HDL',
    ],
  },
  {
    codigo: 'PAN_HEP',
    nombre: 'Hepatograma',
    examenes: ['GOT', 'GPT', 'FAL', 'BIL_T', 'BIL_D', 'BIL_I'],
  },
  {
    codigo: 'PAN_COAG',
    nombre: 'Coagulograma básico',
    examenes: ['TP', 'PP', 'INR', 'KPTT'],
  },
  {
    codigo: 'PAN_ORI',
    nombre: 'Orina completa',
    examenes: [
      'ORI_COLOR', 'ORI_ASP', 'ORI_DENS', 'ORI_PH', 'ORI_GLU', 'ORI_BIL',
      'ORI_NIT', 'ORI_CET', 'ORI_CEL', 'ORI_LEU', 'ORI_HEM', 'ORI_PIO',
      'ORI_MUC', 'ORI_CRIS', 'ORI_CONC',
    ],
  },
];

export interface PanelResumenMovil {
  id: number;
  codigo?: string | null;
  nombre: string;
  tipos_examen_ids: number[];
}

export interface GrupoResultadosMovil {
  key: string;
  titulo: string;
  codigo?: string;
  resultados: ResultadoMovil[];
}

function sortByPanelOrder(resultados: ResultadoMovil[], orderedIds?: number[]): ResultadoMovil[] {
  if (!orderedIds?.length) return resultados;
  const rank = new Map(orderedIds.map((id, index) => [id, index]));
  return [...resultados].sort(
    (a, b) => (rank.get(a.tipo_examen) ?? 10_000) - (rank.get(b.tipo_examen) ?? 10_000)
  );
}

function sortByCodigoOrder(resultados: ResultadoMovil[], orderedCodigos: readonly string[]): ResultadoMovil[] {
  const rank = new Map(orderedCodigos.map((c, i) => [c.toUpperCase(), i]));
  return [...resultados].sort((a, b) => {
    const ca = (a.tipo_examen_codigo || '').toUpperCase();
    const cb = (b.tipo_examen_codigo || '').toUpperCase();
    return (rank.get(ca) ?? 10_000) - (rank.get(cb) ?? 10_000);
  });
}

function esGrupoOrina(grupo: GrupoResultadosMovil): boolean {
  if (grupo.codigo && PANELES_ORINA.has(grupo.codigo)) return true;
  if (grupo.resultados.length >= 1) {
    if (grupo.codigo && !PANELES_ORINA.has(grupo.codigo)) return false;
    const r = grupo.resultados[0];
    const codigo = (r.tipo_examen_codigo || '').toUpperCase();
    if (CODIGOS_ORINA_SUELTOS.has(codigo)) return true;
    const muestra = (r.tipo_examen_muestra_codigo || '').toUpperCase();
    if (MUESTRAS_ORINA.has(muestra)) return true;
  }
  return false;
}

function codigoGrupo(grupo: GrupoResultadosMovil): string {
  if (grupo.codigo) return grupo.codigo.toUpperCase();
  if (grupo.resultados.length === 1) {
    return (grupo.resultados[0].tipo_examen_codigo || '').toUpperCase();
  }
  return '';
}

function prioridadGrupoDefault(grupo: GrupoResultadosMovil): number {
  const codigo = codigoGrupo(grupo);
  const papelLen = ORDEN_FORMULARIO_PAPEL.length;
  if (esGrupoOrina(grupo)) {
    const baseOrina = papelLen + 1000;
    if (codigo === PANEL_ORINA_COMPLETA) return baseOrina + 10_000;
    return baseOrina + (ORDEN_PAPEL_RANK.get(codigo) ?? 5_000);
  }
  if (codigo && ORDEN_PAPEL_RANK.has(codigo)) {
    return ORDEN_PAPEL_RANK.get(codigo)!;
  }
  const base = papelLen + 100;
  if (grupo.codigo === 'PAN_HEMO') return base;
  if (grupo.key.startsWith('panel-') || grupo.key.startsWith('inferido-') || grupo.resultados.length > 1) {
    return base + 100;
  }
  return base + 200;
}

function ordenarGruposPorDefecto(grupos: GrupoResultadosMovil[]): GrupoResultadosMovil[] {
  return [...grupos].sort(
    (a, b) =>
      prioridadGrupoDefault(a) - prioridadGrupoDefault(b) ||
      a.titulo.localeCompare(b.titulo, 'es') ||
      a.key.localeCompare(b.key)
  );
}

function applyOrdenGrupos(
  grupos: GrupoResultadosMovil[],
  ordenCustom?: string[] | null
): GrupoResultadosMovil[] {
  if (!ordenCustom?.length) return ordenarGruposPorDefecto(grupos);
  const byKey = new Map(grupos.map((g) => [g.key, g]));
  const ordered: GrupoResultadosMovil[] = [];
  const seen = new Set<string>();
  for (const key of ordenCustom) {
    const grupo = byKey.get(key);
    if (grupo && !seen.has(key)) {
      ordered.push(grupo);
      seen.add(key);
    }
  }
  const rest = grupos.filter((g) => !seen.has(g.key));
  if (rest.length) ordered.push(...ordenarGruposPorDefecto(rest));
  return ordered;
}

export function groupResultadosInformeMovil(
  orden: {
    paneles_resumen?: PanelResumenMovil[];
    orden_grupos_informe?: string[];
  },
  resultados: ResultadoMovil[]
): GrupoResultadosMovil[] {
  const paneles = orden.paneles_resumen ?? [];
  const assigned = new Set<number>();
  const grupos: GrupoResultadosMovil[] = [];
  const codigosUsados = new Set<string>();

  for (const panel of paneles) {
    const idsPanel = new Set(panel.tipos_examen_ids);
    const rows = sortByPanelOrder(
      resultados.filter((r) => idsPanel.has(r.tipo_examen)),
      panel.tipos_examen_ids
    );
    rows.forEach((r) => assigned.add(r.id));
    if (panel.codigo) codigosUsados.add(panel.codigo);
    if (rows.length > 0) {
      grupos.push({
        key: `panel-${panel.id}`,
        titulo: panel.nombre,
        codigo: panel.codigo ?? undefined,
        resultados: rows,
      });
    }
  }

  let pool = resultados.filter((r) => !assigned.has(r.id));
  for (const perfil of PERFILES_POR_CODIGO) {
    if (codigosUsados.has(perfil.codigo)) continue;
    const set = new Set(perfil.examenes.map((c) => c.toUpperCase()));
    const match = pool.filter((r) => set.has((r.tipo_examen_codigo || '').toUpperCase()));
    const umbral = Math.min(2, perfil.examenes.length);
    if (match.length < umbral) continue;
    const matchIds = new Set(match.map((r) => r.id));
    grupos.push({
      key: `inferido-${perfil.codigo}`,
      titulo: perfil.nombre,
      codigo: perfil.codigo,
      resultados: sortByCodigoOrder(match, perfil.examenes),
    });
    pool = pool.filter((r) => !matchIds.has(r.id));
  }

  for (const r of pool) {
    grupos.push({
      key: `resultado-${r.id}`,
      titulo: r.tipo_examen_nombre || `Examen #${r.tipo_examen}`,
      resultados: [r],
    });
  }

  if (!grupos.length) return grupos;
  return applyOrdenGrupos(grupos, orden.orden_grupos_informe);
}
