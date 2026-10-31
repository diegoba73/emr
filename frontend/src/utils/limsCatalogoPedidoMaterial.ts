/**
 * Opciones del buscador «Agregar examen clínico» por material de pedido.
 * Incluye paneles activos cuyos componentes pertenecen al material.
 */
import type {
  LimsPanelExamen,
  LimsTipoExamen,
  MaterialPedidoLims,
} from '../types/lims';
import { esExamenExcluidoDeLabClinico } from '../modules/laboratorio/solicitudAnalisisPapelLayout';
import { esTipoMuestraSangrePedido } from './limsMuestraSangre';

export type CatalogAddItem = {
  kind: 'examen' | 'panel';
  id: number;
  codigo: string;
  nombre: string;
};

export type OrinaModalidad = 'azar' | '24h' | null;

const ORINA_AZAR_CODIGOS = new Set(['PAN_IONO_U', 'PROT_U_AZ', 'PAN_MALB_AZ']);
const ORINA_24H_CODIGOS = new Set([
  'PAN_CLEAR',
  'PAN_IONO_U24',
  'PAN_PROT24',
  'PAN_MALB24',
  'PAN_CA_U24',
  'PAN_MG_U24',
  'PAN_P_U24',
  'PAN_AU_U24',
  'PAN_UREA_U24',
  'PAN_CREA_U24',
]);

export function materialEsSangre(mat: MaterialPedidoLims): boolean {
  return mat.ui_preset === 'sangre' || mat.codigo === 'SANGRE';
}

/** True si el examen pertenece al material de pedido (Sangre = familia sangre/suero/plasma). */
export function examenPerteneceAMaterial(
  examen: LimsTipoExamen,
  mat: MaterialPedidoLims
): boolean {
  const m = (examen.tipo_muestra_codigo || '').toUpperCase();
  if (materialEsSangre(mat)) {
    return esTipoMuestraSangrePedido(m, examen.tipo_muestra_nombre);
  }
  const muestraSet = new Set(mat.tipo_muestra_codigos.map((c) => c.toUpperCase()));
  return muestraSet.has(m);
}

export function modalidadDeCodigoOrina(codigo: string): OrinaModalidad {
  if (ORINA_AZAR_CODIGOS.has(codigo)) return 'azar';
  if (ORINA_24H_CODIGOS.has(codigo)) return '24h';
  return null;
}

function examenesByIdMap(
  examenes: LimsTipoExamen[]
): Map<number, LimsTipoExamen> {
  const m = new Map<number, LimsTipoExamen>();
  for (const e of examenes) m.set(e.id, e);
  return m;
}

/** Componentes activos del panel resolviendo ids contra el catálogo de exámenes. */
export function componentesPanelActivos(
  panel: LimsPanelExamen,
  examenesById: Map<number, LimsTipoExamen>
): LimsTipoExamen[] {
  const ids = panel.tipos_examen || [];
  const out: LimsTipoExamen[] = [];
  for (const id of ids) {
    const e = examenesById.get(id);
    if (!e || e.activo === false) continue;
    out.push(e);
  }
  return out;
}

/**
 * El panel pertenece al material si tiene al menos un componente clínico
 * (no micro / excluido) de ese material.
 */
export function panelPerteneceAMaterial(
  panel: LimsPanelExamen,
  mat: MaterialPedidoLims,
  examenes: LimsTipoExamen[] | Map<number, LimsTipoExamen>
): boolean {
  if (panel.activo === false) return false;
  const byId = Array.isArray(examenes) ? examenesByIdMap(examenes) : examenes;
  const comps = componentesPanelActivos(panel, byId).filter(
    (e) => !esExamenExcluidoDeLabClinico(e)
  );
  if (comps.length === 0) return false;
  return comps.some((e) => examenPerteneceAMaterial(e, mat));
}

function examenPasaFiltroOrina(
  examen: LimsTipoExamen,
  materialKey: string,
  orinaModalidad: OrinaModalidad
): boolean {
  if (materialKey !== 'ORINA' || !orinaModalidad) return true;
  const m = (examen.tipo_muestra_codigo || '').toUpperCase();
  if (orinaModalidad === 'azar' && m === 'ORINA_24_H') return false;
  if (orinaModalidad === '24h' && m === 'ORINA') return false;
  const modCodigo = modalidadDeCodigoOrina(examen.codigo);
  if (orinaModalidad === 'azar' && modCodigo === '24h') return false;
  if (orinaModalidad === '24h' && modCodigo === 'azar') return false;
  return true;
}

/**
 * Panel visible en orina según modalidad: código del panel o al menos un
 * componente compatible con esa modalidad.
 */
export function panelPasaFiltroOrina(
  panel: LimsPanelExamen,
  materialKey: string,
  orinaModalidad: OrinaModalidad,
  examenes: LimsTipoExamen[] | Map<number, LimsTipoExamen>
): boolean {
  if (materialKey !== 'ORINA' || !orinaModalidad) return true;
  const panMod = modalidadDeCodigoOrina(panel.codigo);
  if (panMod && panMod !== orinaModalidad) return false;
  const byId = Array.isArray(examenes) ? examenesByIdMap(examenes) : examenes;
  const comps = componentesPanelActivos(panel, byId).filter(
    (e) => !esExamenExcluidoDeLabClinico(e)
  );
  return comps.some((e) => examenPasaFiltroOrina(e, materialKey, orinaModalidad));
}

/**
 * Códigos que no deben ofrecerse en «Agregar» porque ya están en la grilla
 * frecuente: el propio código de grilla, componentes de paneles de grilla
 * (p. ej. AU_U24 si está PAN_AU_U24) y productos IACA con panel_equivalente
 * en grilla (p. ej. URI24 → PAN_AU_U24).
 */
export function codigosCubiertosPorGrilla(
  gridCodigos: Set<string>,
  paneles: LimsPanelExamen[],
  examenes: LimsTipoExamen[],
  examenesById?: Map<number, LimsTipoExamen>
): Set<string> {
  const byId = examenesById ?? examenesByIdMap(examenes);
  const cubiertos = new Set(gridCodigos);
  for (const p of paneles) {
    if (!gridCodigos.has(p.codigo)) continue;
    for (const e of componentesPanelActivos(p, byId)) {
      cubiertos.add(e.codigo);
    }
  }
  for (const e of examenes) {
    const panEq = (e.panel_equivalente || '').trim().toUpperCase();
    if (panEq && gridCodigos.has(panEq)) {
      cubiertos.add(e.codigo);
    }
  }
  return cubiertos;
}

export function agregarCatalogOptionsForMaterial(opts: {
  mat: MaterialPedidoLims;
  examenes: LimsTipoExamen[];
  paneles: LimsPanelExamen[];
  gridCodigos: Set<string>;
  selectedExamenesIds: Set<number>;
  selectedPanelesIds: Set<number>;
  orinaModalidad: OrinaModalidad;
}): CatalogAddItem[] {
  const {
    mat,
    examenes,
    paneles,
    gridCodigos,
    selectedExamenesIds,
    selectedPanelesIds,
    orinaModalidad,
  } = opts;
  const materialKey = mat.codigo;
  const byId = examenesByIdMap(examenes);
  const ocultosPorGrilla = codigosCubiertosPorGrilla(
    gridCodigos,
    paneles,
    examenes,
    byId
  );
  const items: CatalogAddItem[] = [];

  for (const e of examenes) {
    if (e.activo === false) continue;
    if (esExamenExcluidoDeLabClinico(e)) continue;
    if (ocultosPorGrilla.has(e.codigo)) continue;
    if (selectedExamenesIds.has(e.id)) continue;
    if (!examenPerteneceAMaterial(e, mat)) continue;
    if (!examenPasaFiltroOrina(e, materialKey, orinaModalidad)) continue;
    items.push({ kind: 'examen', id: e.id, codigo: e.codigo, nombre: e.nombre });
  }

  for (const p of paneles) {
    if (p.activo === false) continue;
    if (gridCodigos.has(p.codigo)) continue;
    if (selectedPanelesIds.has(p.id)) continue;
    if (!panelPerteneceAMaterial(p, mat, byId)) continue;
    if (!panelPasaFiltroOrina(p, materialKey, orinaModalidad, byId)) continue;
    items.push({ kind: 'panel', id: p.id, codigo: p.codigo, nombre: p.nombre });
  }

  items.sort((a, b) => a.codigo.localeCompare(b.codigo));
  return items;
}

export function chipsAgregadosCatalogForMaterial(opts: {
  mat: MaterialPedidoLims;
  examenes: LimsTipoExamen[];
  paneles: LimsPanelExamen[];
  gridCodigos: Set<string>;
  selectedExamenesIds: Set<number>;
  selectedPanelesIds: Set<number>;
}): CatalogAddItem[] {
  const {
    mat,
    examenes,
    paneles,
    gridCodigos,
    selectedExamenesIds,
    selectedPanelesIds,
  } = opts;
  const byId = examenesByIdMap(examenes);
  const items: CatalogAddItem[] = [];

  for (const e of examenes) {
    if (!selectedExamenesIds.has(e.id)) continue;
    if (gridCodigos.has(e.codigo)) continue;
    if (!examenPerteneceAMaterial(e, mat)) continue;
    items.push({ kind: 'examen', id: e.id, codigo: e.codigo, nombre: e.nombre });
  }

  for (const p of paneles) {
    if (!selectedPanelesIds.has(p.id)) continue;
    if (gridCodigos.has(p.codigo)) continue;
    if (!panelPerteneceAMaterial(p, mat, byId)) continue;
    items.push({ kind: 'panel', id: p.id, codigo: p.codigo, nombre: p.nombre });
  }

  items.sort((a, b) => a.codigo.localeCompare(b.codigo));
  return items;
}
