/** Restricciones de frecuencia / cobertura de ensayos (obra social). */
import { normalizeRolValue } from './roles';

export const MENSAJE_PROBNP_FRECUENCIA =
  'La Obra Social no le permite realizar la determinación de proBNP debido a que tiene ya una realizada hace menos de 1 mes. De necesitarla de todas maneras, comuníquese con el Laboratorio.';

export const CODIGO_PROBNP = 'PROBNP';

/** Texto fijo del diálogo de aviso al médico al enviar el pedido. */
export const TEXTO_LAB_PUEDE_QUITAR_ENSAYOS =
  'El laboratorio puede quitar estos ensayos de la orden si la obra social no los habilita o el paciente no los abona en forma particular.';

export type RestriccionEnsayoMapEntry = {
  bloqueado?: boolean;
  aviso?: boolean;
  mensaje?: string | null;
};

export type AvisoFrecuenciaItem = {
  codigo: string;
  nombre: string;
  mensaje: string;
};

/** Admin, laboratorio y bioquímico pueden agregar cualquier ensayo. */
export function puedeOmitirRestriccionFrecuenciaEnsayos(rol?: string | null): boolean {
  const r = normalizeRolValue(rol);
  return r === 'admin' || r === 'laboratorio' || r === 'bioquimico';
}

export function mensajeBloqueoExamen(
  codigo: string | undefined,
  restricciones: Record<string, RestriccionEnsayoMapEntry>,
): string | null {
  if (!codigo) return null;
  const rest = restricciones[codigo];
  if (!rest?.bloqueado) return null;
  return rest.mensaje || (codigo === CODIGO_PROBNP ? MENSAJE_PROBNP_FRECUENCIA : null);
}

/** Primer mensaje de bloqueo entre varios códigos (examen o componentes de paquete). */
export function mensajeBloqueoCodigos(
  codigos: string[],
  restricciones: Record<string, RestriccionEnsayoMapEntry>,
): string | null {
  for (const c of codigos) {
    const msg = mensajeBloqueoExamen(c, restricciones);
    if (msg) return msg;
  }
  return null;
}

/** Aviso soft (no bloquea): hay mensaje de política OS/frecuencia. */
export function mensajeAvisoExamen(
  codigo: string | undefined,
  restricciones: Record<string, RestriccionEnsayoMapEntry>,
): string | null {
  if (!codigo) return null;
  const rest = restricciones[(codigo || '').trim().toUpperCase()];
  if (!rest?.mensaje) return null;
  if (rest.bloqueado) return rest.mensaje;
  if (rest.aviso === false) return null;
  // aviso true o mensaje presente con bloqueado false
  return rest.mensaje;
}

/**
 * Junta avisos únicos por código a partir de ítems seleccionados
 * (exámenes sueltos y/o paneles con componentes).
 */
export function collectAvisosFrecuencia(
  items: Array<{
    codigo?: string | null;
    nombre?: string | null;
    componentes?: Array<{ codigo?: string | null; nombre?: string | null }> | null;
  }>,
  restricciones: Record<string, RestriccionEnsayoMapEntry>,
): AvisoFrecuenciaItem[] {
  const byCodigo = new Map<string, AvisoFrecuenciaItem>();

  const push = (codigoRaw: string | null | undefined, nombreRaw: string | null | undefined) => {
    const codigo = (codigoRaw || '').trim().toUpperCase();
    if (!codigo) return;
    const msg = mensajeAvisoExamen(codigo, restricciones);
    if (!msg) return;
    if (byCodigo.has(codigo)) return;
    byCodigo.set(codigo, {
      codigo,
      nombre: (nombreRaw || codigo).trim() || codigo,
      mensaje: msg,
    });
  };

  for (const item of items) {
    push(item.codigo, item.nombre);
    for (const c of item.componentes || []) {
      push(c.codigo, c.nombre);
    }
  }

  // Si ya está el panel de ionograma, no repetir Na/K/Cl con el mismo aviso.
  if (byCodigo.has('PAN_IONO')) {
    for (const c of ['NA', 'K', 'CL']) {
      byCodigo.delete(c);
    }
  }

  return Array.from(byCodigo.values()).sort((a, b) => a.codigo.localeCompare(b.codigo));
}

export function formatAvisosFrecuenciaConfirmacion(avisos: AvisoFrecuenciaItem[]): string {
  const lineas = avisos.map((a) => `• ${a.nombre} (${a.codigo}): ${a.mensaje}`);
  return [
    'Estos ensayos pueden no cumplir la política de la obra social:',
    '',
    ...lineas,
    '',
    TEXTO_LAB_PUEDE_QUITAR_ENSAYOS,
    '',
    '¿Enviar el pedido de todas formas?',
  ].join('\n');
}
