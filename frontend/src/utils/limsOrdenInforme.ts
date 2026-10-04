/**
 * Orden de grupos en el informe PDF / carga de resultados LIMS.
 * Por defecto sigue ORDEN_PRESENTACION_PEDIDO (talón y UI); las orinas van
 * al final (orina completa última dentro de ese bloque).
 * El layout del formulario papel (`SOLICITUD_ANALISIS_PAPEL_ROWS`) es independiente.
 */
import type { GrupoResultadosOrden } from './limsResultadosPanel';

export const PANEL_HEMOGRAMA = 'PAN_HEMO';
export const PANEL_ORINA_COMPLETA = 'PAN_ORI';

export const PANELES_ORINA = new Set([
  'PAN_ORI',
  'PAN_IONO_U',
  'PAN_IONO_U24',
  'PAN_MALB_AZ',
  'PAN_MALB24',
  'PAN_CLEAR',
  'PAN_PROT24',
]);

const CODIGOS_ORINA_SUELTOS = new Set(['PROT_U_AZ']);
const MUESTRAS_ORINA = new Set(['ORINA', 'ORINA_24_H']);

/**
 * Orden de presentación clínica (talón / resultados / informe).
 * Debe coincidir con `ORDEN_PRESENTACION_PEDIDO` en
 * `laboratorio/catalogo_solicitud_papel.py`.
 */
export const ORDEN_PRESENTACION_PEDIDO: string[] = [
  'PAN_HEMO',
  'GLU',
  'UREA',
  'CREATI',
  'AU',
  'CA',
  'MG',
  'P',
  'PROT_T',
  'ALB',
  'FERR',
  'UIBC',
  'GOT',
  'GPT',
  'FAL',
  'BIL_T',
  'BIL_D',
  'BIL_I',
  'COL_TOT',
  'HDL',
  'TG',
  'LDL',
  'VLDL',
  'PCR_US',
  'AMIL',
  'LIP',
  'GGT',
  'LDH',
  'PAN_HEP',
  'PAN_LIP',
  'PAN_IONO',
  'CPK',
  'CPK_MB',
  'TROP_I',
  'TROP_US',
  'MIOG',
];

/** @deprecated Usar ORDEN_PRESENTACION_PEDIDO. */
export const ORDEN_FORMULARIO_PAPEL = ORDEN_PRESENTACION_PEDIDO;

const ORDEN_PRESENTACION_RANK = new Map(ORDEN_PRESENTACION_PEDIDO.map((c, i) => [c, i]));

export function grupoKeyPanel(panelId: number): string {
  return `panel-${panelId}`;
}

export function grupoKeyResultado(resultadoId: number): string {
  return `resultado-${resultadoId}`;
}

export function esGrupoOrina(grupo: GrupoResultadosOrden): boolean {
  if (grupo.codigo && PANELES_ORINA.has(grupo.codigo)) {
    return true;
  }
  if (grupo.resultados.length >= 1) {
    if (grupo.codigo && !PANELES_ORINA.has(grupo.codigo)) {
      return false;
    }
    const r = grupo.resultados[0];
    const codigo = (r.tipo_examen_codigo || '').toUpperCase();
    if (CODIGOS_ORINA_SUELTOS.has(codigo)) {
      return true;
    }
    const muestra = (r.tipo_examen_muestra_codigo || '').toUpperCase();
    if (MUESTRAS_ORINA.has(muestra)) {
      return true;
    }
  }
  return false;
}

function codigoGrupo(grupo: GrupoResultadosOrden): string {
  if (grupo.codigo) {
    return grupo.codigo.toUpperCase();
  }
  if (grupo.resultados.length === 1) {
    return (grupo.resultados[0].tipo_examen_codigo || '').toUpperCase();
  }
  return '';
}

/** True si el bloque es panel/perfil (lleva encabezado en el PDF). */
export function esPerfilGrupo(grupo: GrupoResultadosOrden): boolean {
  return Boolean(
    grupo.codigo &&
      (grupo.key.startsWith('panel-') ||
        grupo.key.startsWith('inferido-') ||
        grupo.resultados.length > 1)
  );
}

/**
 * Clave numérica comparable: 0…N presentación, luego fuera-de-lista, luego orinas
 * (orina completa con el rank más alto del bloque orina).
 */
export function prioridadGrupoDefault(grupo: GrupoResultadosOrden): number {
  const codigo = codigoGrupo(grupo);
  const presentacionLen = ORDEN_PRESENTACION_PEDIDO.length;

  if (esGrupoOrina(grupo)) {
    const baseOrina = presentacionLen + 1000;
    if (codigo === PANEL_ORINA_COMPLETA) {
      return baseOrina + 10_000;
    }
    return baseOrina + (ORDEN_PRESENTACION_RANK.get(codigo) ?? 5_000);
  }

  if (codigo && ORDEN_PRESENTACION_RANK.has(codigo)) {
    return ORDEN_PRESENTACION_RANK.get(codigo)!;
  }

  const base = presentacionLen + 100;
  if (grupo.codigo === PANEL_HEMOGRAMA) {
    return base;
  }
  if (
    grupo.key.startsWith('panel-') ||
    grupo.key.startsWith('inferido-') ||
    (Boolean(grupo.codigo) && grupo.resultados.length > 1)
  ) {
    return base + 100;
  }
  return base + 200;
}

export function ordenarGruposPorDefecto(grupos: GrupoResultadosOrden[]): GrupoResultadosOrden[] {
  return [...grupos].sort(
    (a, b) =>
      prioridadGrupoDefault(a) - prioridadGrupoDefault(b) ||
      a.titulo.localeCompare(b.titulo, 'es') ||
      a.key.localeCompare(b.key)
  );
}

export function buildOrdenGruposKeys(grupos: GrupoResultadosOrden[]): string[] {
  return grupos.map((g) => g.key);
}

export function applyOrdenGrupos(
  grupos: GrupoResultadosOrden[],
  ordenCustom?: string[] | null
): GrupoResultadosOrden[] {
  if (!ordenCustom?.length) {
    return ordenarGruposPorDefecto(grupos);
  }
  const byKey = new Map(grupos.map((g) => [g.key, g]));
  const ordered: GrupoResultadosOrden[] = [];
  const seen = new Set<string>();
  for (const key of ordenCustom) {
    const grupo = byKey.get(key);
    if (grupo && !seen.has(key)) {
      ordered.push(grupo);
      seen.add(key);
    }
  }
  const rest = grupos.filter((g) => !seen.has(g.key));
  if (rest.length) {
    ordered.push(...ordenarGruposPorDefecto(rest));
  }
  return ordered;
}

export function reorderOrdenGrupos(
  orden: string[],
  key: string,
  direction: 'up' | 'down'
): string[] {
  const idx = orden.indexOf(key);
  if (idx < 0) {
    return orden;
  }
  const swapWith = direction === 'up' ? idx - 1 : idx + 1;
  if (swapWith < 0 || swapWith >= orden.length) {
    return orden;
  }
  const next = [...orden];
  [next[idx], next[swapWith]] = [next[swapWith], next[idx]];
  return next;
}

export function resolveOrdenGrupos(
  grupos: GrupoResultadosOrden[],
  ordenGuardado?: string[] | null
): string[] {
  const keys = new Set(grupos.map((g) => g.key));
  const base = ordenGuardado?.filter((k) => keys.has(k)) ?? [];
  const seen = new Set(base);
  for (const g of ordenarGruposPorDefecto(grupos)) {
    if (!seen.has(g.key)) {
      base.push(g.key);
      seen.add(g.key);
    }
  }
  return base;
}
