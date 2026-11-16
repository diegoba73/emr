/**
 * Reglas de selección del formulario «Solicitud de análisis».
 * Códigos alineados a `laboratorio/catalogo_solicitud_papel.py`.
 */

/** Cartucho Finecare: Troponina I + CPK-MB + Mioglobina siempre juntas. */
export const CARTUCHO_CARDIACO_CODIGOS = ['TROP_I', 'CPK_MB', 'MIOG'] as const;

/** Al pedir EAB (art/ven) se incluyen estas prácticas del mismo ensayo. */
export const EAB_INCLUYE_CODIGOS = {
  paneles: ['PAN_IONO'] as const,
  examenes: ['LACT', 'CA_ION'] as const,
};

/**
 * Al pedir CAIE (calcio iónico estimado): incluir Ca total y proteínas
 * para Zeisler. CA_ION / K-ión medido no dispara esta regla.
 * Con EAB el iónico de equipo sigue siendo CA_ION (sin insumos Zeisler).
 */
export const CAIE_INCLUYE_CODIGOS = ['CA', 'PROT_T'] as const;

/**
 * Al pedir RAC suelto: incluir microalbuminuria y creatinuria (insumos del cálculo).
 * Alineado a `laboratorio.calculos_derivados.INSUMOS_POR_CODIGO_CALCULADO['RAC']`.
 */
export const RAC_INCLUYE_CODIGOS = ['MICROALB', 'CREA_U'] as const;

/**
 * Al pedir RAR suelto: incluir aldosterona y actividad de renina.
 * Alineado a `laboratorio.calculos_derivados.INSUMOS_POR_CODIGO_CALCULADO['RAR']`.
 */
export const RAR_INCLUYE_CODIGOS = ['ALDOS', 'ARPLA'] as const;

/**
 * Coagulograma sin hemograma: agregar plaquetas (recuento acompañante).
 * Alineado a `laboratorio.acompanamiento_pedido`.
 */
export const PANEL_COAGULOGRAMA = 'PAN_COAG';
export const PANEL_HEMOGRAMA = 'PAN_HEMO';
export const COAG_SIN_HEMO_INCLUYE_CODIGOS = ['PLAQ'] as const;

/**
 * Calculados que se ofrecen sueltos en «Agregar» aunque su panel ya esté en la
 * grilla (p. ej. RAC cubierto por PAN_MALB_AZ). Al seleccionarlos se agregan
 * los insumos vía las reglas de inclusión.
 */
export const EXAMENES_SOLICITABLES_AUNQUE_CUBIERTOS_POR_GRILLA = new Set([
  'RAC',
]);

export const PANELES_EAB = new Set(['PAN_EAB_ART', 'PAN_EAB_VEN']);

/** Componentes del formulario que no deben ir sueltos si su panel ya está pedido. */
export const EXAMENES_CUBIERTOS_POR_PANEL: Record<string, string> = {
  INR: 'PAN_COAG',
  CL: 'PAN_IONO',
  PLAQ: 'PAN_HEMO',
};

export function esCodigoCartuchoCardiaco(codigo: string | undefined): boolean {
  return Boolean(codigo && (CARTUCHO_CARDIACO_CODIGOS as readonly string[]).includes(codigo));
}

export function esPanelEab(codigo: string | undefined): boolean {
  return Boolean(codigo && PANELES_EAB.has(codigo));
}
