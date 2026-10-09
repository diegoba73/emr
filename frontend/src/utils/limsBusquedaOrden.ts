/**
 * Interpreta el campo «Número» de la bandeja de órdenes LIMS.
 *
 * - `130` → protocolo exacto del año en curso (`LAB-2026-00130`)
 * - `2025-00130` / `LAB-2025-00130` → número exacto de ese año
 * - vacío → sin filtro de protocolo
 *
 * La búsqueda por paciente/DNI va en un campo aparte (no pasa por acá).
 */

const DIGITS_PROTOCOLO = 5;

export type InterpreteNumeroOrden =
  | { tipo: 'vacio' }
  | { tipo: 'exacto'; numero: string };

/** @deprecated usar InterpreteNumeroOrden */
export type InterpreteBusquedaOrden = InterpreteNumeroOrden | { tipo: 'texto'; q: string };

function padSecuencia(raw: string): string {
  const digits = raw.replace(/\D/g, '');
  if (!digits) return raw;
  if (digits.length >= DIGITS_PROTOCOLO) return digits.slice(-DIGITS_PROTOCOLO);
  return digits.padStart(DIGITS_PROTOCOLO, '0');
}

export function anioCursoLocal(ref: Date = new Date()): number {
  return ref.getFullYear();
}

/** Normaliza el input del campo Número a protocolo LAB-YYYY-NNNNN exacto. */
export function interpretarNumeroOrden(
  raw: string,
  anioCurso: number = anioCursoLocal()
): InterpreteNumeroOrden {
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

  // Solo dígitos (hasta 5): protocolo exacto del año en curso
  if (/^\d{1,5}$/.test(compact)) {
    return {
      tipo: 'exacto',
      numero: `LAB-${anioCurso}-${padSecuencia(compact)}`,
    };
  }

  // Cualquier otro formato de número se intenta como protocolo del año
  // (p. ej. pegado con ceros o guiones raros) — si no matchea, vacío.
  const soloDigitos = compact.replace(/\D/g, '');
  if (soloDigitos && soloDigitos.length <= DIGITS_PROTOCOLO) {
    return {
      tipo: 'exacto',
      numero: `LAB-${anioCurso}-${padSecuencia(soloDigitos)}`,
    };
  }

  return { tipo: 'vacio' };
}

/**
 * Compatibilidad: el campo unificado antiguo.
 * Texto/DNI libre sigue como `texto`; números van a exacto del año.
 */
export function interpretarBusquedaOrden(
  raw: string,
  anioCurso: number = anioCursoLocal()
): InterpreteBusquedaOrden {
  const q = (raw || '').trim();
  if (!q) return { tipo: 'vacio' };

  const compact = q.toUpperCase().replace(/\s+/g, '');
  // DNI / texto: más de 5 dígitos puros, o contiene letras
  if (!/^\d{1,5}$/.test(compact) && !/^LAB-\d{4}-\d/i.test(compact) && !/^\d{4}-\d{1,5}$/.test(compact)) {
    if (/^\d{6,}$/.test(compact) || /[A-ZÁÉÍÓÚÑ]/i.test(q)) {
      return { tipo: 'texto', q };
    }
  }

  return interpretarNumeroOrden(raw, anioCurso);
}
