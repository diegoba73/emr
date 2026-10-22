/**
 * Criterio de material «Sangre» en el pedido (alineado a
 * laboratorio/muestra_sangre_pedido.py).
 *
 * Incluye sangre/suero/plasma con cualquier aditivo o variante de código;
 * excluye otros materiales (orina, LCR, médula, seminal, …).
 */
export function esTipoMuestraSangrePedido(
  codigo?: string | null,
  _nombre?: string | null
): boolean {
  const c = (codigo || '').trim().toUpperCase();
  if (!c) return false;
  if (c === 'PLASMA_SEMINAL' || c.startsWith('PLASMA_SEMINAL')) return false;
  if (c.startsWith('MEDULA')) return false;
  if (c.startsWith('SANGRE')) return true;
  if (c.startsWith('SUERO')) return true;
  if (c.startsWith('PLASMA')) return true;
  return false;
}
