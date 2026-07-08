/**
 * Conversión de valores según configuración del catálogo TipoExamen (modo de entrada).
 */

import type { LimsTipoExamen } from '../types/lims';

export type FormatoInformeEntrada = 'decimal1' | 'integer' | 'absolute_int' | 'absolute_millions';

export type ModoEntradaResultado = 'ESTANDAR' | 'TICKET_ENTERO' | 'FORMULA_PORCENTAJE';

/** Defaults legacy hemograma Sysmex (fallback si modo_entrada = ESTANDAR). */
const LEGACY_ENTRADA_BY_CODIGO: Record<
  string,
  { modo: ModoEntradaResultado; ticketDecimals: number; clinicalMultiplier: number; display: FormatoInformeEntrada }
> = {
  LEU: { modo: 'TICKET_ENTERO', ticketDecimals: 1, clinicalMultiplier: 1000, display: 'absolute_int' },
  PLAQ: { modo: 'TICKET_ENTERO', ticketDecimals: 0, clinicalMultiplier: 1000, display: 'absolute_int' },
  HEMATIES: { modo: 'TICKET_ENTERO', ticketDecimals: 2, clinicalMultiplier: 1, display: 'absolute_millions' },
  HGB: { modo: 'TICKET_ENTERO', ticketDecimals: 1, clinicalMultiplier: 1, display: 'decimal1' },
  HTO: { modo: 'TICKET_ENTERO', ticketDecimals: 1, clinicalMultiplier: 1, display: 'decimal1' },
  RDW: { modo: 'TICKET_ENTERO', ticketDecimals: 1, clinicalMultiplier: 1, display: 'decimal1' },
  NEUT_CAY: { modo: 'FORMULA_PORCENTAJE', ticketDecimals: 0, clinicalMultiplier: 1, display: 'integer' },
  NEUT_SEG: { modo: 'FORMULA_PORCENTAJE', ticketDecimals: 0, clinicalMultiplier: 1, display: 'integer' },
  EOS: { modo: 'FORMULA_PORCENTAJE', ticketDecimals: 0, clinicalMultiplier: 1, display: 'integer' },
  BAS: { modo: 'FORMULA_PORCENTAJE', ticketDecimals: 0, clinicalMultiplier: 1, display: 'integer' },
  LINF: { modo: 'FORMULA_PORCENTAJE', ticketDecimals: 0, clinicalMultiplier: 1, display: 'integer' },
  MONO: { modo: 'FORMULA_PORCENTAJE', ticketDecimals: 0, clinicalMultiplier: 1, display: 'integer' },
};

export interface EntradaRule {
  ticketDecimals: number;
  clinicalMultiplier: number;
  display: FormatoInformeEntrada;
  modo: ModoEntradaResultado;
}

export interface TicketConversionResult {
  entry: number;
  ticketValue: number;
  valorNumerico: number;
  valorInforme: string;
}

export interface FormulaProgress {
  sum: number;
  remaining: number;
  hasValues: boolean;
  isComplete: boolean;
  isOver: boolean;
}

export const MODO_ENTRADA_LABELS: Record<ModoEntradaResultado, string> = {
  ESTANDAR: 'Estándar',
  TICKET_ENTERO: 'Ticket analizador',
  FORMULA_PORCENTAJE: 'Fórmula % (suma 100)',
};

export const FORMATO_INFORME_LABELS: Record<FormatoInformeEntrada, string> = {
  decimal1: 'Un decimal (7.3)',
  integer: 'Entero directo (70)',
  absolute_int: 'Entero absoluto (9300)',
  absolute_millions: 'Millones (2.370.000)',
};

function legacyRule(codigo?: string | null): EntradaRule | null {
  if (!codigo) return null;
  const row = LEGACY_ENTRADA_BY_CODIGO[codigo.trim().toUpperCase()];
  if (!row) return null;
  return {
    ticketDecimals: row.ticketDecimals,
    clinicalMultiplier: row.clinicalMultiplier,
    display: row.display,
    modo: row.modo,
  };
}

export function getEntradaRule(te?: LimsTipoExamen | null, codigoFallback?: string | null): EntradaRule | null {
  const modo = te?.modo_entrada ?? 'ESTANDAR';
  if (modo === 'ESTANDAR') {
    return legacyRule(te?.codigo ?? codigoFallback);
  }
  const fmt = (te?.formato_informe_entrada ?? '').trim() as FormatoInformeEntrada;
  if (!fmt) {
    return legacyRule(te?.codigo ?? codigoFallback);
  }
  return {
    ticketDecimals: te?.ticket_decimales ?? 0,
    clinicalMultiplier: Number(te?.multiplicador_clinico ?? 1),
    display: fmt,
    modo,
  };
}

export function usesTicketEntry(te?: LimsTipoExamen | null, codigoFallback?: string | null): boolean {
  const modo = te?.modo_entrada ?? 'ESTANDAR';
  if (modo === 'TICKET_ENTERO' || modo === 'FORMULA_PORCENTAJE') return true;
  return legacyRule(te?.codigo ?? codigoFallback) != null;
}

export function isFormulaPercent(te?: LimsTipoExamen | null, codigoFallback?: string | null): boolean {
  const modo = te?.modo_entrada ?? 'ESTANDAR';
  if (modo === 'FORMULA_PORCENTAJE') return true;
  const rule = legacyRule(te?.codigo ?? codigoFallback);
  return rule?.modo === 'FORMULA_PORCENTAJE' && modo === 'ESTANDAR';
}

function parsePositiveInteger(raw: string): number | null {
  const t = raw.trim();
  if (!t || !/^\d+$/.test(t)) return null;
  const n = Number(t);
  if (!Number.isSafeInteger(n) || n < 0) return null;
  return n;
}

function ticketValueFromEntry(entry: number, ticketDecimals: number): number {
  return entry / 10 ** ticketDecimals;
}

function formatDecimal1(value: number): string {
  const rounded = Math.round(value * 10) / 10;
  return rounded.toFixed(1);
}

function formatAbsoluteInt(value: number): string {
  return String(Math.round(value));
}

function formatAbsoluteMillions(ticketValue: number): string {
  const absolute = Math.round(ticketValue * 1_000_000);
  return absolute.toLocaleString('es-AR', { maximumFractionDigits: 0 });
}

export function formatInformeEntrada(ticketValue: number, display: FormatoInformeEntrada): string {
  switch (display) {
    case 'decimal1':
      return formatDecimal1(ticketValue);
    case 'absolute_int':
      return formatAbsoluteInt(ticketValue * 1000);
    case 'absolute_millions':
      return formatAbsoluteMillions(ticketValue);
    case 'integer':
      return String(Math.round(ticketValue));
    default:
      return String(ticketValue);
  }
}

export function convertTicketEntry(
  te: LimsTipoExamen | null | undefined,
  rawEntry: string,
  codigoFallback?: string | null
): TicketConversionResult | null {
  const rule = getEntradaRule(te, codigoFallback);
  if (!rule) return null;
  const entry = parsePositiveInteger(rawEntry);
  if (entry === null) return null;

  const ticketValue = ticketValueFromEntry(entry, rule.ticketDecimals);
  const valorNumerico = ticketValue * rule.clinicalMultiplier;
  const valorInforme = formatInformeEntrada(ticketValue, rule.display);

  return { entry, ticketValue, valorNumerico, valorInforme };
}

export function entryFromStored(
  te: LimsTipoExamen | null | undefined,
  valorNumerico: number | string | null | undefined,
  codigoFallback?: string | null
): string {
  const rule = getEntradaRule(te, codigoFallback);
  if (!rule || valorNumerico === null || valorNumerico === undefined || valorNumerico === '') {
    return '';
  }
  const numeric = Number(valorNumerico);
  if (Number.isNaN(numeric)) return '';

  const ticketValue = numeric / rule.clinicalMultiplier;
  const entry = Math.round(ticketValue * 10 ** rule.ticketDecimals);
  return entry > 0 ? String(entry) : '';
}

export function previewTicketInforme(
  te: LimsTipoExamen | null | undefined,
  rawEntry: string,
  codigoFallback?: string | null
): string | null {
  const conv = convertTicketEntry(te, rawEntry, codigoFallback);
  return conv?.valorInforme ?? null;
}

export function computeFormulaProgress(
  entries: Array<{ te?: LimsTipoExamen | null; codigo?: string | null; valor_sysmex?: string | null }>
): FormulaProgress {
  let sum = 0;
  let hasValues = false;
  for (const item of entries) {
    if (!isFormulaPercent(item.te, item.codigo)) continue;
    const raw = (item.valor_sysmex ?? '').trim();
    if (!raw) continue;
    const n = Number(raw);
    if (Number.isNaN(n) || n < 0) continue;
    hasValues = true;
    sum += n;
  }
  const remaining = 100 - sum;
  return {
    sum,
    remaining,
    hasValues,
    isComplete: hasValues && remaining === 0,
    isOver: sum > 100,
  };
}

export function formatFormulaProgressLabel(progress: FormulaProgress): string {
  if (!progress.hasValues) return 'Faltan 100%';
  if (progress.isComplete) return '100% completo';
  if (progress.isOver) return `+${Math.abs(progress.remaining)}% de más`;
  return `Faltan ${progress.remaining}%`;
}

export function modoEntradaResumen(te?: LimsTipoExamen | null): string {
  if (!te) return '—';
  const modo = te.modo_entrada ?? 'ESTANDAR';
  if (modo === 'ESTANDAR') return MODO_ENTRADA_LABELS.ESTANDAR;
  const fmt = te.formato_informe_entrada
    ? FORMATO_INFORME_LABELS[te.formato_informe_entrada as FormatoInformeEntrada]
    : '';
  const dec = te.ticket_decimales ? ` · ${te.ticket_decimales} dec.` : '';
  return `${MODO_ENTRADA_LABELS[modo]}${dec}${fmt ? ` · ${fmt}` : ''}`;
}
