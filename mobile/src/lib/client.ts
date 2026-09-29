export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) { super(message); this.status = status; }
}
export function createClient(base: string, getToken: () => string | null, onUnauthorized: () => void, fetcher: typeof fetch = fetch, allowLocalHttp = false) {
  return async function request<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
    const localHttp = allowLocalHttp && /^http:\/\/(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})(?::\d+)?\//.test(base);
    if ((!base.startsWith('https://') && !localHttp) || !path.startsWith('/') || path.startsWith('//')) {
      throw new ApiError('La conexión segura de la app todavía no está configurada.', 0);
    }
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
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
        let message = response.status === 401 ? 'La sesión venció. Iniciá sesión nuevamente.' :
          response.status === 403 ? 'No tenés permiso para realizar esta acción.' :
          response.status === 404 ? 'El turno no está disponible para tu usuario.' :
          'No se pudo completar la operación. Intentá nuevamente.';
        if (response.status === 400 && data) {
          if (typeof data.detail === 'string') message = data.detail;
          else if (Array.isArray(data)) message = data.filter(v => typeof v === 'string').join(' ');
          else if (typeof data === 'object') message = Object.values(data).flat().filter(v => typeof v === 'string').join(' ') || message;
        }
        throw new ApiError(message, response.status);
      }
      return data as T;
    } catch (error) {
      if (error instanceof ApiError) throw error;
      throw new ApiError('No se pudo conectar. Verificá tu conexión y actualizá tus turnos antes de volver a intentar.', 0);
    } finally { clearTimeout(timeout); }
  };
}
