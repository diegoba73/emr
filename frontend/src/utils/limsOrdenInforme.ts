/**
 * Orden de grupos en el informe PDF (paneles y exámenes sueltos).
 */
import type { GrupoResultadosOrden } from './limsResultadosPanel';

export const PANEL_HEMOGRAMA = 'PAN_HEMO';

export const PANELES_ORINA = new Set([
  'PAN_ORI',
  'PAN_IONO_U',
  'PAN_IONO_U24',
  'PAN_MALB_AZ',
  'PAN_MALB24',
]);

const CODIGOS_ORINA_SUELTOS = new Set(['PROT_U_24', 'PROT_U_AZ']);

export function grupoKeyPanel(panelId: number): string {
  return `panel-${panelId}`;
}

export function grupoKeyResultado(resultadoId: number): string {
  return `resultado-${resultadoId}`;
}

function esOrinaGrupo(grupo: GrupoResultadosOrden): boolean {
  if (grupo.codigo && PANELES_ORINA.has(grupo.codigo)) {
    return true;
  }
  if (grupo.key.startsWith('resultado-') && grupo.resultados.length === 1) {
    const codigo = (grupo.resultados[0].tipo_examen_codigo || '').toUpperCase();
    if (CODIGOS_ORINA_SUELTOS.has(codigo)) {
      return true;
    }
    const muestra = (grupo.resultados[0].tipo_examen_muestra_codigo || '').toUpperCase();
    if (muestra === 'ORINA') {
      return true;
    }
  }
  return false;
}

export function prioridadGrupoDefault(grupo: GrupoResultadosOrden): number {
  if (grupo.codigo === PANEL_HEMOGRAMA) {
    return 0;
  }
  if (esOrinaGrupo(grupo)) {
    return 3;
  }
  if (grupo.key.startsWith('panel-')) {
    return 1;
  }
  return 2;
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
