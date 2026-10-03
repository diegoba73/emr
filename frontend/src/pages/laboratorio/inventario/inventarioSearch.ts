/**
 * Filtros de búsqueda UI para inventario (client-side, sin API).
 * Un campo por sección; coincide si el texto aparece en alguno de los campos útiles.
 */

export function normalizeSearch(q: string): string {
  return q.trim().toLowerCase();
}

export function matchesSearch(q: string, ...parts: Array<string | number | null | undefined>): boolean {
  const needle = normalizeSearch(q);
  if (!needle) return true;
  const hay = parts
    .map((p) => (p == null ? '' : String(p)))
    .join(' ')
    .toLowerCase();
  return hay.includes(needle);
}

export type ReactivoBusqueda = {
  codigo: string;
  nombre: string;
  ref_comercial?: string | null;
  equipo_codigo?: string | null;
  proveedor?: string | null;
};

/** Código interno, REF, nombre, equipo, proveedor. */
export function filterReactivosBusqueda<T extends ReactivoBusqueda>(rows: T[], q: string): T[] {
  if (!normalizeSearch(q)) return rows;
  return rows.filter((r) =>
    matchesSearch(q, r.codigo, r.ref_comercial, r.nombre, r.equipo_codigo, r.proveedor)
  );
}

export type InsumoBusqueda = {
  codigo: string;
  nombre: string;
  tipo: string;
  proveedor?: string | null;
};

/** Código, nombre, tipo, proveedor. */
export function filterInsumosBusqueda<T extends InsumoBusqueda>(rows: T[], q: string): T[] {
  if (!normalizeSearch(q)) return rows;
  return rows.filter((r) => matchesSearch(q, r.codigo, r.nombre, r.tipo, r.proveedor));
}

export type LoteBusqueda = {
  codigo_lote: string;
  insumo_codigo?: string | null;
  insumo_nombre?: string | null;
};

/** Producto (código/nombre) o código de lote. */
export function filterLotesBusqueda<T extends LoteBusqueda>(rows: T[], q: string): T[] {
  if (!normalizeSearch(q)) return rows;
  return rows.filter((r) =>
    matchesSearch(q, r.codigo_lote, r.insumo_codigo, r.insumo_nombre)
  );
}

export type ConsumoBusqueda = {
  tipo_examen_codigo?: string | null;
  tipo_examen_nombre?: string | null;
  insumo_codigo?: string | null;
  insumo_nombre?: string | null;
  rol?: string | null;
};

/** Ensayo o reactivo vinculado. */
export function filterConsumosBusqueda<T extends ConsumoBusqueda>(rows: T[], q: string): T[] {
  if (!normalizeSearch(q)) return rows;
  return rows.filter((r) =>
    matchesSearch(
      q,
      r.tipo_examen_codigo,
      r.tipo_examen_nombre,
      r.insumo_codigo,
      r.insumo_nombre,
      r.rol
    )
  );
}

export type MovimientoBusqueda = {
  tipo?: string | null;
  insumo_codigo?: string | null;
  lote_codigo?: string | null;
  motivo?: string | null;
};

/** Producto, lote, tipo o motivo. */
export function filterMovimientosBusqueda<T extends MovimientoBusqueda>(rows: T[], q: string): T[] {
  if (!normalizeSearch(q)) return rows;
  return rows.filter((r) =>
    matchesSearch(q, r.tipo, r.insumo_codigo, r.lote_codigo, r.motivo)
  );
}

export type PedidoBusqueda = {
  codigo: string;
  nombre: string;
  proveedor?: string | null;
};

/** Código, nombre o proveedor. */
export function filterPedidosBusqueda<T extends PedidoBusqueda>(rows: T[], q: string): T[] {
  if (!normalizeSearch(q)) return rows;
  return rows.filter((r) => matchesSearch(q, r.codigo, r.nombre, r.proveedor));
}
