export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) { super(message); this.status = status; }
}

function messageFromBody(data: unknown, fallback: string): string {
  if (typeof data === 'string' && data.trim()) return data.trim();
  if (!data || typeof data !== 'object') return fallback;
  const body = data as Record<string, unknown>;
  if (typeof body.detail === 'string' && body.detail.trim()) return body.detail.trim();
  if (typeof body.error === 'string' && body.error.trim()) return body.error.trim();
  if (Array.isArray(body.detail)) {
    const parts = body.detail.filter((v): v is string => typeof v === 'string' && v.trim().length > 0);
    if (parts.length) return parts.join(' ');
  }
  if (Array.isArray(data)) {
    const parts = data.filter((v): v is string => typeof v === 'string' && v.trim().length > 0);
    if (parts.length) return parts.join(' ');
  }
  const fieldErrors = Object.values(body).flat().filter((v): v is string => typeof v === 'string' && v.trim().length > 0);
  if (fieldErrors.length) return fieldErrors.join(' ');
  return fallback;
}

export type ClientOptions = {
  timeoutMs?: number;
};

export function createClient(
  base: string,
  getToken: () => string | null,
  onUnauthorized: () => void,
  fetcher: typeof fetch = fetch,
  allowLocalHttp = false,
) {
  return async function request<T>(
    path: string,
    method = 'GET',
    body?: unknown,
    options?: ClientOptions,
  ): Promise<T> {
    const localHttp = allowLocalHttp && /^http:\/\/(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})(?::\d+)?\//.test(base);
    if ((!base.startsWith('https://') && !localHttp) || !path.startsWith('/') || path.startsWith('//')) {
      throw new ApiError('La conexión segura de la app todavía no está configurada.', 0);
    }
    const controller = new AbortController();
    const timeoutMs = options?.timeoutMs ?? 15000;
    const timeout = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const token = getToken();
      const response = await fetcher(`${base.replace(/\/$/, '')}${path}`, {
        method, redirect: 'error', signal: controller.signal,
        headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
      });
      const data = response.status === 204 ? null : await response.json().catch(() => null);
      if (!response.ok) {
        if (response.status === 401) onUnauthorized();
        const fallback =
          response.status === 401 ? 'La sesión venció. Iniciá sesión nuevamente.' :
          response.status === 403 ? 'No tenés permiso para realizar esta acción.' :
          response.status === 404 ? 'No se encontró lo solicitado.' :
          'No se pudo completar la operación. Intentá nuevamente.';
        throw new ApiError(messageFromBody(data, fallback), response.status);
      }
      return data as T;
    } catch (error) {
      if (error instanceof ApiError) throw error;
      throw new ApiError('No se pudo conectar. Verificá tu conexión e intentá nuevamente.', 0);
    } finally { clearTimeout(timeout); }
  };
}
