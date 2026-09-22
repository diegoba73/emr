/**
 * Vista informativa de reactivos por equipo (Ticket C).
 * Solo presentación: no altera stock, consumos ni QC.
 */

export type InsumoVista = {
  tipo: 'REACTIVO' | 'TUBO' | 'MEDIO' | 'OTRO' | string;
  codigo: string;
  nombre: string;
  ref_comercial?: string | null;
  equipo_codigo?: string | null;
  stock_actual: number;
  unidad: string;
};

export function esReactivo(p: Pick<InsumoVista, 'tipo'>): boolean {
  return p.tipo === 'REACTIVO';
}

export function labelTipoInsumoVista(tipo: string): string {
  if (tipo === 'REACTIVO') return 'Reactivo';
  if (tipo === 'TUBO') return 'Tubo / contenedor';
  if (tipo === 'MEDIO') return 'Medio de cultivo';
  return 'Otro';
}

/** REF comercial del fabricante; vacío = pendiente / legacy. */
export function refComercialDisplay(ref: string | null | undefined): {
  text: string;
  pendiente: boolean;
} {
  const trimmed = (ref || '').trim();
  if (!trimmed) return { text: 'Sin REF', pendiente: true };
  return { text: trimmed, pendiente: false };
}

/**
 * Existencia registrada (lotes). Stock 0 = catalogado sin existencia usable.
 * No implica “disponible para uso” solo por estar en catálogo.
 */
export function existenciaDisplay(
  stockActual: number,
  unidad: string
): {
  text: string;
  sinExistencia: boolean;
  cantidad: number;
} {
  const cantidad = Number(stockActual) || 0;
  if (cantidad <= 0) {
    return { text: `Sin existencia (0 ${unidad || 'u'})`, sinExistencia: true, cantidad: 0 };
  }
  return {
    text: `${cantidad} ${unidad || 'u'}`,
    sinExistencia: false,
    cantidad,
  };
}

export function estadoCatalogoDisplay(): string {
  return 'Catalogado';
}

export function filterReactivosPorEquipo<T extends InsumoVista>(
  productos: T[],
  equipoCodigo: string
): T[] {
  const reactivos = productos.filter(esReactivo);
  const codigo = equipoCodigo.trim();
  if (!codigo) return reactivos;
  return reactivos.filter((r) => (r.equipo_codigo || '') === codigo);
}

export type ResumenReactivosEquipo = {
  total: number;
  conRef: number;
  sinRef: number;
  conExistencia: number;
  sinExistencia: number;
};

export function resumenReactivosVista(reactivos: InsumoVista[]): ResumenReactivosEquipo {
  let conRef = 0;
  let sinRef = 0;
  let conExistencia = 0;
  let sinExistencia = 0;
  for (const r of reactivos) {
    if (refComercialDisplay(r.ref_comercial).pendiente) sinRef += 1;
    else conRef += 1;
    if (existenciaDisplay(r.stock_actual, r.unidad).sinExistencia) sinExistencia += 1;
    else conExistencia += 1;
  }
  return {
    total: reactivos.length,
    conRef,
    sinRef,
    conExistencia,
    sinExistencia,
  };
}
