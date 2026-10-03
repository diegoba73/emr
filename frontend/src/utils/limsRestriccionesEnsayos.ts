/** Restricciones de frecuencia / cobertura de ensayos (obra social). */
import { normalizeRolValue } from './roles';

export const MENSAJE_PROBNP_FRECUENCIA =
  'La Obra Social no le permite realizar la determinación de proBNP debido a que tiene ya una realizada hace menos de 1 mes. De necesitarla de todas maneras, comuníquese con el Laboratorio.';

export const CODIGO_PROBNP = 'PROBNP';

/** Admin, laboratorio y bioquímico pueden agregar cualquier ensayo. */
export function puedeOmitirRestriccionFrecuenciaEnsayos(rol?: string | null): boolean {
  const r = normalizeRolValue(rol);
  return r === 'admin' || r === 'laboratorio' || r === 'bioquimico';
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

/** Primer mensaje de bloqueo entre varios códigos (examen o componentes de paquete). */
export function mensajeBloqueoCodigos(
  codigos: string[],
  restricciones: Record<string, { bloqueado?: boolean; mensaje?: string | null }>,
): string | null {
  for (const c of codigos) {
    const msg = mensajeBloqueoExamen(c, restricciones);
    if (msg) return msg;
  }
  return null;
}
