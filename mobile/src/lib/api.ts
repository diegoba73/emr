import { ClientOptions, createClient } from './client';
let token: string | null = null;
let unauthorized = () => {};
export const setToken = (value: string | null) => { token = value; };
export const onUnauthorized = (handler: () => void) => { unauthorized = handler; };
let base = '';
let revision = 0;
export const setInstitution = (url: string) => { revision++; token = null; base = url; };
export async function api<T>(
  path: string,
  method = 'GET',
  body?: unknown,
  options?: ClientOptions,
): Promise<T> {
  const current = revision;
  const capturedToken = token;
  const client = createClient(base, () => capturedToken, () => {
    if (current === revision && capturedToken === token) unauthorized();
  }, fetch, __DEV__ && process.env.EXPO_PUBLIC_ALLOW_LOCAL_HTTP === 'true');
  const result = await client<T>(path, method, body, options);
  if (current !== revision) throw new Error('La institución cambió. Volvé a consultar.');
  return result;
}
export async function allPages<T>(path: string): Promise<T[]> {
  const pageRevision = revision;
  const rows: T[] = [];
  let next: string | null = path;
  while (next) {
    if (pageRevision !== revision) throw new Error('La institución cambió. Volvé a consultar.');
    const data: { results: T[]; next?: string } | T[] = await api(next);
    if (Array.isArray(data)) { rows.push(...data); break; }
    rows.push(...data.results);
    // Conservar siempre el origen móvil configurado; nunca enviar credenciales a URLs del paginador.
    next = data.next ? `${path.split('?')[0]}?${new URL(data.next, 'https://local.invalid').searchParams}` : null;
  }
  return rows;
}
