/** Tubo aún no recepcionado que bloquea LISTO_PARA_VALIDAR. */
export type TuboPendienteRecepcion = {
  id: number;
  codigo_barra?: string | null;
  tipo_contenedor_codigo?: string | null;
  tipo_contenedor_nombre?: string | null;
  tipo_muestra_codigo?: string | null;
  tipo_muestra_nombre?: string | null;
  estado?: string | null;
};

export function labelTuboPendienteRecepcion(t: TuboPendienteRecepcion): string {
  const codigo = (t.codigo_barra || '').trim();
  const tubo =
    (t.tipo_contenedor_codigo || '').trim() ||
    (t.tipo_contenedor_nombre || '').trim();
  const material =
    (t.tipo_muestra_nombre || '').trim() ||
    (t.tipo_muestra_codigo || '').trim();
  const estado = (t.estado || '').trim();
  const partes: string[] = [];
  if (codigo) partes.push(codigo);
  else if (tubo) partes.push(tubo);
  else partes.push(`tubo #${t.id}`);
  const extras: string[] = [];
  if (tubo && codigo) extras.push(tubo);
  if (material) extras.push(material);
  if (estado === 'PENDIENTE_TOMA') extras.push('pendiente de toma');
  if (estado === 'TOMADA') extras.push('tomada, sin recepcionar');
  if (extras.length) return `${partes[0]} (${extras.join(' · ')})`;
  return partes[0];
}

export function formatListaTubosPendientesRecepcion(
  tubos: TuboPendienteRecepcion[] | null | undefined
): string {
  const list = tubos || [];
  if (!list.length) return '';
  return list.map(labelTuboPendienteRecepcion).join(', ');
}
