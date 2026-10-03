/**
 * Filtros de búsqueda UI para control de calidad (client-side).
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

export type CorridaBusqueda = {
  producto_nombre?: string | null;
  material_nombre?: string | null;
  lote_codigo?: string | null;
  nivel?: string | null;
  estado?: string | null;
  equipo_codigo?: string | null;
};

/** Producto/material, lote, nivel, estado o equipo. */
export function filterCorridasBusqueda<T extends CorridaBusqueda>(rows: T[], q: string): T[] {
  if (!normalizeSearch(q)) return rows;
  return rows.filter((r) =>
    matchesSearch(
      q,
      r.producto_nombre,
      r.material_nombre,
      r.lote_codigo,
      r.nivel,
      r.estado,
      r.equipo_codigo
    )
  );
}

export type ProductoQcBusqueda = {
  codigo: string;
  nombre: string;
  marca?: string | null;
  equipo_codigo?: string | null;
};

/** Código, nombre, marca o equipo. */
export function filterProductosQcBusqueda<T extends ProductoQcBusqueda>(rows: T[], q: string): T[] {
  if (!normalizeSearch(q)) return rows;
  return rows.filter((r) =>
    matchesSearch(q, r.codigo, r.nombre, r.marca, r.equipo_codigo)
  );
}

export type LoteProductoBusqueda = {
  codigo_lote: string;
  producto_nombre?: string | null;
  producto_codigo?: string | null;
  equipo_codigo?: string | null;
};

/** Lote, producto o equipo. */
export function filterLotesProductoBusqueda<T extends LoteProductoBusqueda>(
  rows: T[],
  q: string
): T[] {
  if (!normalizeSearch(q)) return rows;
  return rows.filter((r) =>
    matchesSearch(q, r.codigo_lote, r.producto_nombre, r.producto_codigo, r.equipo_codigo)
  );
}

export type MaterialQcBusqueda = {
  nombre: string;
  marca?: string | null;
  producto?: string | null;
  tipo_examen_codigo?: string | null;
  tipo_examen_nombre?: string | null;
  nivel?: string | null;
  equipo_codigo?: string | null;
};

/** Nombre, marca, producto, ensayo, nivel o equipo. */
export function filterMaterialesQcBusqueda<T extends MaterialQcBusqueda>(rows: T[], q: string): T[] {
  if (!normalizeSearch(q)) return rows;
  return rows.filter((r) =>
    matchesSearch(
      q,
      r.nombre,
      r.marca,
      r.producto,
      r.tipo_examen_codigo,
      r.tipo_examen_nombre,
      r.nivel,
      r.equipo_codigo
    )
  );
}

export type LoteControlBusqueda = {
  codigo_lote: string;
  material_nombre?: string | null;
};

/** Código de lote, material o texto extra (ensayo/nivel). */
export function filterLotesControlBusqueda<T extends LoteControlBusqueda>(
  rows: T[],
  q: string,
  extra?: (row: T) => Array<string | null | undefined>
): T[] {
  if (!normalizeSearch(q)) return rows;
  return rows.filter((r) =>
    matchesSearch(q, r.codigo_lote, r.material_nombre, ...(extra ? extra(r) : []))
  );
}

export type EquipoBusqueda = {
  codigo: string;
  nombre: string;
  marca_modelo?: string | null;
};

/** Código, nombre o marca/modelo. */
export function filterEquiposBusqueda<T extends EquipoBusqueda>(rows: T[], q: string): T[] {
  if (!normalizeSearch(q)) return rows;
  return rows.filter((r) => matchesSearch(q, r.codigo, r.nombre, r.marca_modelo));
}

export type CalibracionBusqueda = {
  calibrador_nombre?: string | null;
  marca?: string | null;
  codigo_lote?: string | null;
  observaciones?: string | null;
  equipo_codigo?: string | null;
  tipo_examen_codigo?: string | null;
};

/** Equipo, calibrador, lote o ensayo. */
export function filterCalibracionesBusqueda<T extends CalibracionBusqueda>(
  rows: T[],
  q: string
): T[] {
  if (!normalizeSearch(q)) return rows;
  return rows.filter((r) =>
    matchesSearch(
      q,
      r.equipo_codigo,
      r.calibrador_nombre,
      r.marca,
      r.codigo_lote,
      r.observaciones,
      r.tipo_examen_codigo
    )
  );
}

export type EquipoHoyBusqueda = {
  codigo: string;
  nombre: string;
  resumen?: string | null;
  lote_codigo?: string | null;
  ensayos?: Array<{ codigo?: string | null; nombre?: string | null }>;
  ensayos_hoy?: Array<{ codigo?: string | null }>;
};

/** Equipo, lote o ensayo del tablero de hoy. */
export function filterEquiposHoyBusqueda<T extends EquipoHoyBusqueda>(rows: T[], q: string): T[] {
  if (!normalizeSearch(q)) return rows;
  return rows.filter((eq) => {
    const ensayos = [
      ...(eq.ensayos || []).flatMap((e) => [e.codigo, e.nombre]),
      ...(eq.ensayos_hoy || []).map((e) => e.codigo),
    ];
    return matchesSearch(q, eq.codigo, eq.nombre, eq.resumen, eq.lote_codigo, ...ensayos);
  });
}
