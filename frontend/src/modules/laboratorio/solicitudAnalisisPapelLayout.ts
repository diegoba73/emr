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

/** Filas de Lab. Clínico — material Sangre (columna izquierda | derecha).
 * Orden operativo de carga de pedidos (todos los sectores). Orina vive en su
 * material / grilla propia. El orden del talón / carga de resultados está en
 * `ORDEN_PRESENTACION_PEDIDO` (`limsOrdenInforme.ts` / backend).
 */
export const SOLICITUD_ANALISIS_PAPEL_ROWS: PapelFormRow[] = [
  { left: p('PAN_HEMO'), right: e('CPK') },
  { left: e('HBA1C'), right: e('CPK_MB') },
  { left: e('GLU'), right: e('MIOG') },
  { left: p('PAN_CTOG'), right: e('TROP_I') },
  { left: e('UREA'), right: e('TROP_US') },
  { left: e('CREATI'), right: e('PROBNP') },
  { left: e('AU'), right: e('DDIM') },
  { left: p('PAN_HEP'), right: e('LPA') },
  { left: p('PAN_LIP'), right: p('PAN_ELP') },
  { left: p('PAN_IONO'), right: e('PSA') },
  { left: e('CL'), right: e('TSH') },
  { left: e('CA_ION'), right: e('T3') },
  { left: e('MG'), right: e('T4') },
  { left: e('CA'), right: e('T4L') },
  { left: e('P'), right: e('B12') },
  { left: p('PAN_COAG'), right: e('VITD') },
  { left: e('INR'), right: p('PAN_FERR') },
  { left: e('PROT_T'), right: e('VDRL') },
  { left: e('ALB'), right: e('HBVAGS') },
  { left: e('VSG'), right: e('HCVG') },
  { left: e('PCR_US'), right: e('HIVAC') },
  { left: e('AMIL'), right: e('GRUPO') },
  { left: e('LIP'), right: p('PAN_EAB_ART') },
  { left: e('GGT'), right: p('PAN_EAB_VEN') },
  { left: e('LDH'), right: e('LACT') },
];

/** Códigos de orina del formulario papel (material Orina; no van en grilla Sangre). */
export const ORINA_SOLICITUD_PAPEL_CODIGOS = [
  'PAN_ORI',
  'PAN_CLEAR',
  'PAN_IONO_U',
  'PAN_IONO_U24',
  'PAN_PROT24',
  'PROT_U_AZ',
  'PAN_MALB24',
  'PAN_MALB_AZ',
] as const;

/** Cultivos / micro para sección de pedido (alineado a EstudioMicrobiologia). */
export const MICRO_PEDIDO_CODIGOS = [
  'UROCULTIVO',
  'HEMOCULTIVO',
  'COPROCULTIVO',
  'CULTIVO_HERIDA',
  'CULTIVO_RUTINA',
  'HISOPADO',
  'PUNCION',
] as const;

/** Siguen en el catálogo (órdenes ya pedidas) pero no se ofrecen en Lab. Clínico. */
export const EXAMENES_FUERA_DE_SOLICITUD = new Set([
  'HCGB',
  'SANOC',
  'ASTO',
  'ENA',
  'ENA_RO52',
  'ENA_RO60',
  'ENA_SSB',
  'ENA_RNP',
  'ENA_SM',
  // Códigos de pedido micro (legado seed); el grueso del catálogo se filtra por nombre.
  ...MICRO_PEDIDO_CODIGOS,
]);

const MICRO_NOMBRE_NEEDLES = [
  'cultivo',
  'antibiograma',
  'baar',
  'micolog',
  'micosis',
  'espermocult',
  'germenes comunes',
] as const;

function normalizarTextoCatalogo(value: string): string {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();
}

/**
 * TipoExamen del catálogo clínico que en realidad son pedido de microbiología
 * (urocultivo OMCULT, hemocultivos, ATB, etc.). Se piden solo vía Microbiología.
 */
export function esExamenMicrobiologiaCatalogo(examen: {
  codigo?: string | null;
  nombre?: string | null;
}): boolean {
  const codigo = (examen.codigo || '').trim().toUpperCase();
  if (codigo && (MICRO_PEDIDO_CODIGOS as readonly string[]).includes(codigo)) {
    return true;
  }
  // Códigos LabWin/import con CUL (OMCULT, COPROCUL, HEMACUL1, …).
  if (codigo.includes('CUL')) return true;
  const nombre = normalizarTextoCatalogo(examen.nombre || '');
  if (!nombre) return false;
  return MICRO_NOMBRE_NEEDLES.some((n) => nombre.includes(n));
}

/** No ofrecer en grilla / “Agregar examen clínico” de Lab. Clínico. */
export function esExamenExcluidoDeLabClinico(examen: {
  codigo?: string | null;
  nombre?: string | null;
}): boolean {
  const codigo = (examen.codigo || '').trim().toUpperCase();
  if (codigo && EXAMENES_FUERA_DE_SOLICITUD.has(codigo)) return true;
  return esExamenMicrobiologiaCatalogo(examen);
}

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

/** Códigos del formulario papel (sangre + orina frecuentes). */
export function papelCodigosSet(): Set<string> {
  const s = new Set<string>();
  for (const row of SOLICITUD_ANALISIS_PAPEL_ROWS) {
    if (row.left) s.add(row.left.codigo);
    if (row.right) s.add(row.right.codigo);
  }
  for (const codigo of ORINA_SOLICITUD_PAPEL_CODIGOS) {
    s.add(codigo);
  }
  return s;
}

