/** Helper: operadores LIMS (laboratorio/bioquímico) no aplican tope PROBNP. */
import { isOperadorLimsRole } from './roles';

export const MENSAJE_PROBNP_FRECUENCIA =
  'La Obra Social no le permite realizar la determinación de proBNP debido a que tiene ya una realizada hace menos de 1 mes, de querer de todas maneras realizar el ensayo consulte con el Laboratorio';

export const CODIGO_PROBNP = 'PROBNP';

export function puedeOmitirRestriccionFrecuenciaEnsayos(rol?: string | null): boolean {
  return isOperadorLimsRole(rol);
}

export function mensajeBloqueoExamen(
  codigo: string | undefined,
  restricciones: Record<string, { bloqueado?: boolean; mensaje?: string | null }>,
): string | null {
  if (!codigo) return null;
  const rest = restricciones[codigo];
  if (!rest?.bloqueado) return null;
  return rest.mensaje || (codigo === CODIGO_PROBNP ? MENSAJE_PROBNP_FRECUENCIA : null);
}
