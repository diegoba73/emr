/**
 * Helpers de display para códigos LAB (la resolución canónica es el backend /api/lab/codigos/).
 */
export function isCodigoTuboLab(codigo: string): boolean {
  const c = (codigo || '').trim().toUpperCase();
  return /^LAB-\d{4}-\d{5}-\d{2}$/.test(c) || c.startsWith('MUE-');
}

export function isCodigoProtocoloLab(codigo: string): boolean {
  const c = (codigo || '').trim().toUpperCase();
  return /^LAB-\d{4}-\d{5}$/.test(c);
}

/** @deprecated Preferir API unificada; se mantiene para tests/legacy display. */
export function isCodigoMicrobiologia(codigo: string): boolean {
  const c = (codigo || '').trim().toUpperCase();
  return (
    isCodigoProtocoloLab(c) ||
    c.startsWith('MICB-') ||
    (c.startsWith('MIC-') && !c.startsWith('MICB-'))
  );
}
