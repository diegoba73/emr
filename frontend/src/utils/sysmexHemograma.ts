/**
 * Compatibilidad con código/tests que usan conversión Sysmex por código.
 * La lógica vive en entradaResultados.ts (configuración por catálogo TipoExamen).
 */
import type { LimsTipoExamen } from '../types/lims';
import {
  convertTicketEntry,
  entryFromStored,
  previewTicketInforme,
  formatInformeEntrada,
  usesTicketEntry,
  isFormulaPercent,
  computeFormulaProgress,
  formatFormulaProgressLabel,
  getEntradaRule,
  type TicketConversionResult,
  type FormatoInformeEntrada,
} from './entradaResultados';

export type SysmexDisplayKind = FormatoInformeEntrada;
export type SysmexConversionResult = TicketConversionResult;

export {
  formatInformeEntrada as formatSysmexInforme,
  computeFormulaProgress as computeFormulaLeucocitariaProgress,
  formatFormulaProgressLabel,
};

export const SYSMEX_HEMOGRAMA_UNIDADES: Record<string, string> = {
  LEU: '/mm³',
  PLAQ: '/mm³',
  HEMATIES: 'mill/mm³',
  HGB: 'g/dL',
  HTO: '%',
  RDW: '%',
  NEUT_CAY: '%',
  NEUT_SEG: '%',
  EOS: '%',
  BAS: '%',
  LINF: '%',
  MONO: '%',
};

export const FORMULA_LEUCOCITARIA_CODIGOS = [
  'NEUT_CAY',
  'NEUT_SEG',
  'EOS',
  'BAS',
  'LINF',
  'MONO',
] as const;

function teFromCodigo(codigo: string): LimsTipoExamen {
  return { id: 0, codigo, nombre: codigo, tipo_muestra_requerida: 0, modo_entrada: 'ESTANDAR' };
}

export function getSysmexUnidad(codigo: string | undefined | null): string {
  if (!codigo) return '';
  return SYSMEX_HEMOGRAMA_UNIDADES[codigo.trim().toUpperCase()] ?? '';
}

export function isSysmexHemogramaCodigo(codigo: string | undefined | null): boolean {
  return usesTicketEntry(codigo ? teFromCodigo(codigo) : null, codigo);
}

export function isSysmexFormulaCodigo(codigo: string | undefined | null): boolean {
  return isFormulaPercent(codigo ? teFromCodigo(codigo) : null, codigo);
}

export function convertSysmexEntry(codigo: string, rawEntry: string): TicketConversionResult | null {
  return convertTicketEntry(teFromCodigo(codigo), rawEntry, codigo);
}

export function sysmexEntryFromStored(
  codigo: string,
  valorNumerico: number | string | null | undefined
): string {
  return entryFromStored(teFromCodigo(codigo), valorNumerico, codigo);
}

export function previewSysmexInforme(codigo: string, rawEntry: string): string | null {
  return previewTicketInforme(teFromCodigo(codigo), rawEntry, codigo);
}

/** @deprecated Solo tests legacy que inspeccionan reglas por código */
export const SYSMEX_HEMOGRAMA_RULES = Object.fromEntries(
  FORMULA_LEUCOCITARIA_CODIGOS.map((c) => [c, getEntradaRule(teFromCodigo(c), c)])
);
