/**
 * Catálogo de materiales de pedido (fallback FE + helpers de resolución).
 * SoT de producción: GET /lab/materiales-pedido/. El fallback cubre API vacía/fallida
 * para que Lab. Clínico y Microbiología (p. ej. hemocultivo) sigan resolviendo material.
 */
import type { MaterialPedidoLims } from '../types/lims';

/** Fallback alineado a laboratorio/materiales_pedido_catalogo.py (subset UI). */
export const MATERIALES_PEDIDO_FALLBACK: MaterialPedidoLims[] = [
  {
    codigo: 'SANGRE',
    nombre: 'Sangre',
    ui_preset: 'sangre',
    tipo_muestra_codigos: [
      'SUERO',
      'SANGRE_EDTA',
      'PLASMA_CITRATO',
      'PLASMA_EDTA',
      'SANGRE_ERITRO',
      'SANGRE_CITRATO_VSG',
      'SANGRE_HEPARINA',
      'SANGRE_HEPARINA_ART',
      'SANGRE_HEPARINA_VEN',
      'PLASMA_HEPARINA',
    ],
    grilla_codigos: [],
    cultivo_micro_codigo: 'HEMOCULTIVO',
    muestra_micro_codigo: 'SANGRE',
  },
  {
    codigo: 'ORINA',
    nombre: 'Orina',
    ui_preset: 'orina',
    tipo_muestra_codigos: ['ORINA', 'ORINA_24_H'],
    grilla_codigos: [],
    cultivo_micro_codigo: 'UROCULTIVO',
    muestra_micro_codigo: 'ORINA',
    frecuente: true,
  },
  {
    codigo: 'MATERIA_FECAL',
    nombre: 'Materia fecal',
    ui_preset: null,
    tipo_muestra_codigos: ['MATERIA_FECAL'],
    grilla_codigos: [],
    cultivo_micro_codigo: 'COPROCULTIVO',
    muestra_micro_codigo: 'MATERIA_FECAL',
    frecuente: true,
  },
  {
    codigo: 'ESPUTO',
    nombre: 'Esputo',
    tipo_muestra_codigos: ['ESPUTO'],
    grilla_codigos: [],
    cultivo_micro_codigo: 'ESPUTO',
    muestra_micro_codigo: 'ESPUTO',
    frecuente: true,
  },
  {
    codigo: 'HISOP_NAS',
    nombre: 'Hisopado nasal',
    tipo_muestra_codigos: ['HISOP_NAS'],
    grilla_codigos: [],
    cultivo_micro_codigo: 'NASOFARINGEO',
    muestra_micro_codigo: 'EXUDADO_NASAL',
    frecuente: true,
  },
  {
    codigo: 'HISOP_RECT',
    nombre: 'Hisopado rectal',
    tipo_muestra_codigos: ['HISOP_RECT'],
    grilla_codigos: [],
    cultivo_micro_codigo: 'HISOPADO_ANAL',
    muestra_micro_codigo: 'HISOPADO_VIGILANCIA',
    frecuente: true,
  },
  {
    codigo: 'HISOP_AMB',
    nombre: 'Hisopado ambiental',
    tipo_muestra_codigos: ['HISOP_AMB'],
    grilla_codigos: [],
    cultivo_micro_codigo: 'AMBIENTAL',
    muestra_micro_codigo: 'HISOPADO_VIGILANCIA',
    frecuente: true,
  },
];

/** API si trae filas; si no, fallback (misma fuente que el formulario de pedido). */
export function materialesPedidoEfectivos(
  apiList: MaterialPedidoLims[] | null | undefined
): MaterialPedidoLims[] {
  return apiList && apiList.length > 0 ? apiList : MATERIALES_PEDIDO_FALLBACK;
}

/**
 * Resuelve materiales elegidos en bloques contra el catálogo efectivo.
 * Evita el bug de códigos seleccionados en el form (fallback) que el diálogo
 * no encontraba porque solo miraba la lista API aún vacía.
 */
export function resolverMaterialesSeleccionados(
  codigos: string[],
  catalogo: MaterialPedidoLims[]
): MaterialPedidoLims[] {
  if (!codigos.length) return [];
  const byCode = new Map(catalogo.map((m) => [m.codigo, m]));
  return codigos
    .map((c) => byCode.get(c))
    .filter((m): m is MaterialPedidoLims => Boolean(m));
}

/** Código de material de pedido asociado a un cultivo micro (HEMOCULTIVO → SANGRE). */
export function materialCodigoParaCultivo(
  cultivoCodigo: string,
  materiales: Pick<MaterialPedidoLims, 'codigo' | 'cultivo_micro_codigo'>[]
): string {
  const up = (cultivoCodigo || '').trim().toUpperCase();
  if (!up) return '';
  const mat = materiales.find(
    (m) => (m.cultivo_micro_codigo || '').trim().toUpperCase() === up
  );
  return (mat?.codigo || '').toUpperCase();
}
