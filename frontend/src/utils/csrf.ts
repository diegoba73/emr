/**
 * Utilidad para manejar tokens CSRF
 */

export const getCSRFToken = (): string => {
  const cookies = document.cookie.split(';');
  for (const cookie of cookies) {
    const [name, value] = cookie.trim().split('=');
    if (name === 'csrftoken') {
      return value;
    }
  }
  return '';
};

export const fetchWithCSRF = async (url: string, options: RequestInit = {}): Promise<Response> => {
  try {
    // Obtener token CSRF desde el endpoint público
    const baseUrl = url.split('/api/')[0] + '/api';
    const csrfUrl = `${baseUrl}/auth/csrf-token/`;
    
    let csrfToken = getCSRFToken();
    
    // Si no hay token en cookies, intentar obtenerlo del endpoint
    if (!csrfToken) {
      try {
        const csrfResponse = await fetch(csrfUrl, {
          method: 'GET',
          credentials: 'include',
        });
        
        if (csrfResponse.ok) {
          const data = await csrfResponse.json();
          csrfToken = data.csrftoken || getCSRFToken();
        }
      } catch {
        // Si es un error de conexión al obtener CSRF, no fallar todavía
        // El error se detectará cuando se intente hacer la petición principal
      }
    }
    
    // Configurar headers con CSRF
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...(csrfToken && { 'X-CSRFToken': csrfToken }),
      ...options.headers,
    };
    
    
    // Hacer la petición con CSRF
    const response = await fetch(url, {
      ...options,
      headers,
      credentials: 'include',
    });

    return response;
  } catch (error: any) {
    
    // Detectar errores de conexión y proporcionar mensaje más claro
    if (error.message === 'Failed to fetch' || 
        error.message?.includes('ERR_CONNECTION_RESET') ||
        error.message?.includes('NetworkError') ||
        error.name === 'TypeError') {
      const connectionError = new Error(
        'No se pudo conectar con el servidor. Verifica que el backend esté corriendo en http://localhost:8000'
      ) as any;
      connectionError.isConnectionError = true;
      connectionError.originalError = error;
      throw connectionError;
    }
    
    throw error;
  }
};
