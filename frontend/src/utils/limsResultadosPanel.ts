/**
 * Agrupa resultados de una orden LIMS por panel solicitado y exámenes sueltos.
 * Si la orden no trae paneles (p. ej. import LabWin), infiere perfiles por códigos.
 */
import {
  applyOrdenGrupos,
  grupoKeyPanel,
  grupoKeyResultado,
} from './limsOrdenInforme';
import type { ResultadoExamenLims, SolicitudExamenLims } from '../types/lims';

export interface GrupoResultadosOrden {
  key: string;
  titulo: string;
  codigo?: string;
  resultados: ResultadoExamenLims[];
}

/** Perfiles clínicos conocidos (códigos LIMS) para agrupar sin paneles_resumen. */
export const PERFILES_POR_CODIGO: ReadonlyArray<{
  codigo: string;
  nombre: string;
  examenes: readonly string[];
}> = [
  {
    codigo: 'PAN_HEMO',
    nombre: 'Hemograma',
    examenes: [
      'HEMATIES', 'HTO', 'HGB', 'VCM', 'CHCM', 'RDW', 'LEUCO', 'NEUT_CAY',
      'NEUT_SEG', 'EOS', 'BAS', 'LINF', 'MONO', 'PLAQ',
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
    examenes: ['COL_TOT', 'HDL', 'LDL', 'COL_NO_LDL', 'TG'],
  },
  {
    codigo: 'PAN_HEP',
    nombre: 'Hepatograma',
    examenes: ['GOT', 'GPT', 'FAL', 'BIL_T', 'BIL_D'],
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
      'ORI_COLOR', 'ORI_ASP', 'ORI_DENS', 'ORI_PH', 'ORI_BIL', 'ORI_NIT',
      'ORI_CET', 'ORI_CEL', 'ORI_LEU', 'ORI_HEM', 'ORI_PIO', 'ORI_MUC',
      'ORI_CRIS', 'ORI_CONC',
    ],
  },
];

function sortByPanelOrder(
  resultados: ResultadoExamenLims[],
  orderedIds: number[] | undefined
): ResultadoExamenLims[] {
  if (!orderedIds?.length) {
    return resultados;
  }
  const rank = new Map(orderedIds.map((id, index) => [id, index]));
  return [...resultados].sort(
    (a, b) =>
      (rank.get(a.tipo_examen) ?? 10_000) - (rank.get(b.tipo_examen) ?? 10_000)
  );
}

function sortByCodigoOrder(
  resultados: ResultadoExamenLims[],
  orderedCodigos: readonly string[]
): ResultadoExamenLims[] {
  const rank = new Map(orderedCodigos.map((c, i) => [c.toUpperCase(), i]));
  return [...resultados].sort((a, b) => {
    const ca = (a.tipo_examen_codigo || '').toUpperCase();
    const cb = (b.tipo_examen_codigo || '').toUpperCase();
    return (rank.get(ca) ?? 10_000) - (rank.get(cb) ?? 10_000);
  });
}

function inferirGruposPorCodigo(
  restantes: ResultadoExamenLims[],
  codigosPanelYaUsados: Set<string>
): { grupos: GrupoResultadosOrden[]; sobrantes: ResultadoExamenLims[] } {
  let pool = [...restantes];
  const grupos: GrupoResultadosOrden[] = [];

  for (const perfil of PERFILES_POR_CODIGO) {
    if (codigosPanelYaUsados.has(perfil.codigo)) continue;
    const set = new Set(perfil.examenes.map((c) => c.toUpperCase()));
    const match = pool.filter((r) => set.has((r.tipo_examen_codigo || '').toUpperCase()));
    // Al menos 2 analitos del perfil (o todos si el perfil es chico).
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

  return { grupos, sobrantes: pool };
}

export function groupResultadosPorPanel(
  orden: Pick<SolicitudExamenLims, 'paneles_resumen' | 'tipos_examen' | 'orden_grupos_informe'>,
  resultados: ResultadoExamenLims[]
): GrupoResultadosOrden[] {
  const paneles = orden.paneles_resumen ?? [];
  const assignedResultIds = new Set<number>();
  const grupos: GrupoResultadosOrden[] = [];
  const codigosPanelUsados = new Set<string>();

  for (const panel of paneles) {
    const idsPanel = new Set(panel.tipos_examen_ids);
    const rows = sortByPanelOrder(
      resultados.filter((r) => idsPanel.has(r.tipo_examen)),
      panel.tipos_examen_ids
    );
    rows.forEach((r) => assignedResultIds.add(r.id));
    if (panel.codigo) codigosPanelUsados.add(panel.codigo);
    if (rows.length > 0) {
      grupos.push({
        key: grupoKeyPanel(panel.id),
        titulo: panel.nombre,
        codigo: panel.codigo,
        resultados: rows,
      });
    }
  }

  const sinPanel = resultados.filter((r) => !assignedResultIds.has(r.id));
  const { grupos: inferidos, sobrantes } = inferirGruposPorCodigo(sinPanel, codigosPanelUsados);
  grupos.push(...inferidos);

  for (const r of sobrantes) {
    grupos.push({
      key: grupoKeyResultado(r.id),
      titulo: r.tipo_examen_nombre || `Examen #${r.tipo_examen}`,
      resultados: [r],
    });
  }

  if (grupos.length === 0) {
    return grupos;
  }

  return applyOrdenGrupos(grupos, orden.orden_grupos_informe);
}
