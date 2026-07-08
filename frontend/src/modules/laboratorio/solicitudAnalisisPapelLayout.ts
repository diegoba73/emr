/**
 * Layout del formulario en papel «Solicitud de análisis» (dos columnas).
 * Los códigos coinciden con `laboratorio/catalogo_solicitud_papel.py`.
 */

export type PapelItemKind = 'panel' | 'examen';

export interface PapelItemRef {
  kind: PapelItemKind;
  codigo: string;
}

export interface PapelFormRow {
  left?: PapelItemRef | null;
  right?: PapelItemRef | null;
}

const p = (codigo: string): PapelItemRef => ({ kind: 'panel', codigo });
const e = (codigo: string): PapelItemRef => ({ kind: 'examen', codigo });

/** Filas alineadas al PDF institucional (columna izquierda | derecha). */
export const SOLICITUD_ANALISIS_PAPEL_ROWS: PapelFormRow[] = [
  { left: p('PAN_HEMO'), right: e('CPK') },
  { left: e('HBA1C'), right: e('CPK_MB') },
  { left: e('GLU'), right: e('TROP_I') },
  { left: e('UREA'), right: e('MIOG') },
  { left: e('CREA'), right: e('TROP_US') },
  { left: e('AU'), right: e('PROBNP') },
  { left: e('CA'), right: e('DDIM') },
  { left: e('MG'), right: p('PAN_ORI') },
  { left: e('P'), right: p('PAN_CLEAR') },
  { left: p('PAN_FERR'), right: p('PAN_IONO_U24') },
  { left: p('PAN_IONO'), right: p('PAN_IONO_U') },
  { left: e('CA_ION'), right: e('PROT_U_24') },
  { left: p('PAN_LIP'), right: e('PROT_U_AZ') },
  { left: p('PAN_HEP'), right: p('PAN_MALB24') },
  { left: e('PROT_T'), right: p('PAN_MALB_AZ') },
  { left: e('ALB'), right: p('PAN_ELP') },
  { left: p('PAN_COAG'), right: e('LPA') },
  { left: e('VSG'), right: e('PSA') },
  { left: e('PCR_US'), right: e('TSH') },
  { left: e('AMIL'), right: e('T3') },
  { left: e('LIP'), right: e('T4') },
  { left: e('GGT'), right: e('T4L') },
  { left: e('LDH'), right: e('B12') },
  { left: null, right: e('VITD') },
  { left: null, right: e('EAB_ART') },
  { left: null, right: e('EAB_VEN') },
  { left: null, right: e('LACT') },
];

export interface CatalogMaps {
  panelesByCodigo: Map<string, { id: number; nombre: string }>;
  examenesByCodigo: Map<string, { id: number; nombre: string }>;
}

export function buildCatalogMaps(
  paneles: Array<{ id: number; codigo: string; nombre: string; activo?: boolean }>,
  examenes: Array<{ id: number; codigo: string; nombre: string; activo?: boolean }>
): CatalogMaps {
  const panelesByCodigo = new Map<string, { id: number; nombre: string }>();
  const examenesByCodigo = new Map<string, { id: number; nombre: string }>();
  for (const pan of paneles) {
    if (pan.activo === false) continue;
    panelesByCodigo.set(pan.codigo, { id: pan.id, nombre: pan.nombre });
  }
  for (const ex of examenes) {
    if (ex.activo === false) continue;
    examenesByCodigo.set(ex.codigo, { id: ex.id, nombre: ex.nombre });
  }
  return { panelesByCodigo, examenesByCodigo };
}

export function resolvePapelItemLabel(
  item: PapelItemRef,
  maps: CatalogMaps
): string | null {
  const map = item.kind === 'panel' ? maps.panelesByCodigo : maps.examenesByCodigo;
  return map.get(item.codigo)?.nombre ?? null;
}

export function resolvePapelItemId(item: PapelItemRef, maps: CatalogMaps): number | null {
  const map = item.kind === 'panel' ? maps.panelesByCodigo : maps.examenesByCodigo;
  return map.get(item.codigo)?.id ?? null;
}

export function selectionFromIds(
  panelesIds: Iterable<number>,
  examenesIds: Iterable<number>,
  maps: CatalogMaps
): { panelesIds: number[]; examenesIds: number[] } {
  const panSet = new Set(panelesIds);
  const exSet = new Set(examenesIds);
  return {
    panelesIds: Array.from(panSet),
    examenesIds: Array.from(exSet),
  };
}

export function countPapelSelection(
  panelesIds: Set<number>,
  examenesIds: Set<number>
): number {
  return panelesIds.size + examenesIds.size;
}
