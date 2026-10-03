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

export const PANELES_EAB = new Set(['PAN_EAB_ART', 'PAN_EAB_VEN']);

/** Componentes del formulario que no deben ir sueltos si su panel ya está pedido. */
export const EXAMENES_CUBIERTOS_POR_PANEL: Record<string, string> = {
  INR: 'PAN_COAG',
  CL: 'PAN_IONO',
};

export function esCodigoCartuchoCardiaco(codigo: string | undefined): boolean {
  return Boolean(codigo && (CARTUCHO_CARDIACO_CODIGOS as readonly string[]).includes(codigo));
}

export function esPanelEab(codigo: string | undefined): boolean {
  return Boolean(codigo && PANELES_EAB.has(codigo));
}
