import axios from 'axios';

export function parseEstudiosApiError(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status;
    const data = error.response?.data as Record<string, unknown> | string | undefined;
    if (status === 403) {
      return 'No tenés permisos para esta acción.';
    }
    if (status === 404) {
      return 'No se encontró el estudio o no tenés acceso.';
    }
    if (status === 400) {
      if (typeof data === 'string') {
        return data;
      }
      if (data && typeof data === 'object') {
        if (typeof data.detail === 'string') {
          return data.detail;
        }
        const parts: string[] = [];
        for (const [key, val] of Object.entries(data)) {
          if (Array.isArray(val)) {
            parts.push(`${key}: ${val.join(', ')}`);
          } else if (typeof val === 'string') {
            parts.push(`${key}: ${val}`);
          }
        }
        if (parts.length) {
          return parts.join(' ');
        }
      }
      return 'La solicitud no es válida.';
    }
    if (status && status >= 500) {
      return 'Error del servidor. Intente nuevamente más tarde.';
    }
  }
  return fallback;
}
