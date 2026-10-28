/**
 * Parseo de valores con operador (<, >, ≤, ≥).
 * Política: el informe conserva el texto; el número de trabajo es el límite.
 */

export type OperadorValor = '<' | '>' | '<=' | '>=';

export interface ValorConOperador {
  operador: OperadorValor | null;
  numero: number | null;
  texto: string;
}

const RE = /^\s*(<=|>=|≤|≥|<|>)\s*([+-]?\d+(?:[.,]\d+)?)\s*$/;

function normalizeOp(raw: string): OperadorValor {
  if (raw === '≤' || raw === '<=') return '<=';
  if (raw === '≥' || raw === '>=') return '>=';
  if (raw === '>') return '>';
  return '<';
}

export function parseValorConOperador(raw: string | number | null | undefined): ValorConOperador {
  if (raw == null || raw === '') return { operador: null, numero: null, texto: '' };
  if (typeof raw === 'number') {
    return Number.isFinite(raw)
      ? { operador: null, numero: raw, texto: String(raw) }
      : { operador: null, numero: null, texto: String(raw) };
  }
  const texto = String(raw).trim();
  if (!texto) return { operador: null, numero: null, texto: '' };

  const m = texto.match(RE);
  if (m) {
    const n = Number(m[2].replace(',', '.'));
    return {
      operador: normalizeOp(m[1]),
      numero: Number.isFinite(n) ? n : null,
      texto,
    };
  }

  const n = Number(texto.replace(',', '.'));
  if (Number.isFinite(n) && texto !== '') {
    // Evitar Number("") === 0; ya cubierto. Evitar Number("Positivo") NaN.
    return { operador: null, numero: n, texto };
  }
  return { operador: null, numero: null, texto };
}

/** Número para cálculos / gráficas (límite si hay operador). */
export function numeroParaCalculo(raw: string | number | null | undefined): number | null {
  return parseValorConOperador(raw).numero;
}
