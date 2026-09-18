/** Usa el mismo servidor y protocolo que la API, tanto en local como en producción. */
export function administracionUrl(
  suffix = '',
  apiBase = process.env.REACT_APP_API_URL || 'http://localhost:8000/api',
): string {
  const base = new URL(`${apiBase.replace(/\/$/, '')}/`, window.location.origin);
  return new URL(`administracion/${suffix}`, base).href;
}
