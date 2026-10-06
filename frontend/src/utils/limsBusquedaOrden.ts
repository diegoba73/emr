/**
 * Interpreta el campo de búsqueda de la bandeja de órdenes LIMS.
 *
 * - `30` → secuencia del año en curso (LAB-2026-… que contenga 30)
 * - `2026-00030` / `LAB-2026-00030` → número exacto
 * - texto/DNI → búsqueda libre
 */

const DIGITS_PROTOCOLO = 5;

export type InterpreteBusquedaOrden =
  | { tipo: 'vacio' }
  | { tipo: 'exacto'; numero: string }
  | { tipo: 'secuencia_anio'; anio: number; secuencia: string }
  | { tipo: 'texto'; q: string };

function padSecuencia(raw: string): string {
  const digits = raw.replace(/\D/g, '');
  if (!digits) return raw;
  if (digits.length >= DIGITS_PROTOCOLO) return digits.slice(-DIGITS_PROTOCOLO);
  return digits.padStart(DIGITS_PROTOCOLO, '0');
}

export function anioCursoLocal(ref: Date = new Date()): number {
  return ref.getFullYear();
}

export function interpretarBusquedaOrden(
  raw: string,
  anioCurso: number = anioCursoLocal()
): InterpreteBusquedaOrden {
  const q = (raw || '').trim();
  if (!q) return { tipo: 'vacio' };

  const compact = q.toUpperCase().replace(/\s+/g, '');

  // LAB-2026-00030 o LAB-2026-00030-01 (tubo → protocolo)
  const labFull = /^LAB-(\d{4})-(\d{1,5})(?:-\d{2})?$/i.exec(compact);
  if (labFull) {
    return {
      tipo: 'exacto',
      numero: `LAB-${labFull[1]}-${padSecuencia(labFull[2])}`,
    };
  }

  // 2026-00030 / 2026-30
  const anioSeq = /^(\d{4})-(\d{1,5})$/.exec(compact);
  if (anioSeq) {
    return {
      tipo: 'exacto',
      numero: `LAB-${anioSeq[1]}-${padSecuencia(anioSeq[2])}`,
    };
  }

  // Solo dígitos (hasta 5): secuencia del año en curso
  if (/^\d{1,5}$/.test(compact)) {
    return { tipo: 'secuencia_anio', anio: anioCurso, secuencia: compact };
  }

  return { tipo: 'texto', q };
}
