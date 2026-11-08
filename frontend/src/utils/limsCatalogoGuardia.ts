/**
 * Catálogo permitido en pedidos LIMS con origen GUARDIA.
 * Alineado a laboratorio/restricciones_guardia_catalogo.py (validación por código).
 */

export const PANELES_GUARDIA_PERMITIDOS = new Set([
  'PAN_HEMO',
  'PAN_IONO',
  'PAN_HEP',
  'PAN_EAB_ART',
  'PAN_EAB_VEN',
]);

export const EXAMENES_GUARDIA_PERMITIDOS = new Set([
  'GLU',
  'UREA',
  'CREATI',
  'TROP_US',
  'TROP_I',
  'CPK_MB',
  'CPK',
  'MIOG',
]);

export const MENSAJE_CATALOGO_GUARDIA =
  'En guardia solo se pueden pedir: hemograma, ionograma plasmático, glucemia, uremia, creatininemia, hepatograma, enzimas cardíacas (troponina I ultrasensible, troponina I, CPK-MB, CPK, mioglobina) y EAB arterial/venoso.';

function normCodigo(codigo: string | null | undefined): string {
  return (codigo || '').trim().toUpperCase();
}

export function esOrigenCatalogoGuardia(
  origen: string | null | undefined
): boolean {
  return normCodigo(origen) === 'GUARDIA';
}

/** Panel pedible en guardia (código canónico). */
export function panelPermitidoEnGuardia(
  codigo: string | null | undefined
): boolean {
  return PANELES_GUARDIA_PERMITIDOS.has(normCodigo(codigo));
}

/**
 * Examen suelto pedible en guardia: allowlist directa, panel equivalente
 * permitido, o componente de panel permitido (si se conoce el código del panel).
 */
export function examenPermitidoEnGuardia(
  codigo: string | null | undefined,
  opts?: { panelEquivalente?: string | null }
): boolean {
  const c = normCodigo(codigo);
  if (!c) return false;
  if (EXAMENES_GUARDIA_PERMITIDOS.has(c)) return true;
  if (PANELES_GUARDIA_PERMITIDOS.has(c)) return true;
  const pe = normCodigo(opts?.panelEquivalente);
  if (pe && PANELES_GUARDIA_PERMITIDOS.has(pe)) return true;
  return false;
}

export function filtrarPanelesGuardia<T extends { codigo?: string | null }>(
  paneles: T[]
): T[] {
  return paneles.filter((p) => panelPermitidoEnGuardia(p.codigo));
}

export function filtrarExamenesGuardia<
  T extends { codigo?: string | null; panel_equivalente?: string | null },
>(examenes: T[]): T[] {
  return examenes.filter((e) =>
    examenPermitidoEnGuardia(e.codigo, { panelEquivalente: e.panel_equivalente })
  );
}
