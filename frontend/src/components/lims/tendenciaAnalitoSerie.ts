import { numeroParaCalculo } from '../../utils/valorOperador';

/** Punto unificado (histórico o valor actual) para gráfica/tabla de tendencia. */
export interface PuntoTendenciaAnalito {
  fecha: string | null;
  valor: string;
  valorNumerico: number | null;
  unidad: string | null;
  solicitudId: number | null;
  solicitudNumero: string | null;
  esActual: boolean;
}

/** Número para eje Y; acepta ``<0.1`` usando el límite. */
export function parseValorNumerico(raw: string | number | null | undefined): number | null {
  return numeroParaCalculo(raw);
}

function fechaMs(fecha: string | null): number {
  if (!fecha) return Number.POSITIVE_INFINITY;
  const t = Date.parse(fecha);
  return Number.isFinite(t) ? t : Number.POSITIVE_INFINITY;
}

/** Une previos (API, más recientes primero) + actual; orden cronológico ascendente. */
export function armarSerieTendencia(args: {
  previos: Array<{
    valor: string;
    valor_numerico?: string | number | null;
    unidad?: string | null;
    fecha: string | null;
    solicitud_id: number;
    solicitud_numero: string | null;
  }>;
  actual?: {
    valor: string;
    valor_numerico?: string | number | null;
    unidad?: string | null;
    fecha?: string | null;
    solicitudId?: number | null;
    solicitudNumero?: string | null;
  } | null;
}): PuntoTendenciaAnalito[] {
  const puntos: PuntoTendenciaAnalito[] = args.previos.map((p) => ({
    fecha: p.fecha,
    valor: p.valor,
    valorNumerico: parseValorNumerico(p.valor_numerico ?? p.valor),
    unidad: p.unidad ?? null,
    solicitudId: p.solicitud_id,
    solicitudNumero: p.solicitud_numero,
    esActual: false,
  }));

  if (args.actual && (args.actual.valor || '').trim()) {
    puntos.push({
      fecha: args.actual.fecha ?? null,
      valor: args.actual.valor,
      valorNumerico: parseValorNumerico(args.actual.valor_numerico ?? args.actual.valor),
      unidad: args.actual.unidad ?? null,
      solicitudId: args.actual.solicitudId ?? null,
      solicitudNumero: args.actual.solicitudNumero ?? null,
      esActual: true,
    });
  }

  return puntos.sort((a, b) => {
    const da = fechaMs(a.fecha);
    const db = fechaMs(b.fecha);
    if (da !== db) return da - db;
    if (a.esActual !== b.esActual) return a.esActual ? 1 : -1;
    return (a.solicitudId ?? 0) - (b.solicitudId ?? 0);
  });
}

export function puntosNumericos(serie: PuntoTendenciaAnalito[]): PuntoTendenciaAnalito[] {
  return serie.filter((p) => p.valorNumerico != null);
}
