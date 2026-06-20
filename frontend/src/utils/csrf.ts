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
    console.log('🔐 Obteniendo token CSRF desde:', csrfUrl);
    
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
          console.log('✅ Token CSRF obtenido del endpoint');
        } else {
          console.warn('⚠️ No se pudo obtener token CSRF del endpoint, continuando sin él');
        }
      } catch (error: any) {
        // Si es un error de conexión al obtener CSRF, no fallar todavía
        // El error se detectará cuando se intente hacer la petición principal
        console.warn('⚠️ Error obteniendo token CSRF (servidor puede no estar disponible):', error.message);
      }
    } else {
      console.log('✅ Token CSRF ya disponible en cookies');
    }
    
    // Configurar headers con CSRF
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...(csrfToken && { 'X-CSRFToken': csrfToken }),
      ...options.headers,
    };
    
    console.log('📤 Haciendo petición a:', url);
    console.log('📤 Headers:', Object.keys(headers));
    
    // Hacer la petición con CSRF
    const response = await fetch(url, {
      ...options,
      headers,
      credentials: 'include',
    });
    
    console.log('📥 Respuesta recibida:', response.status, response.statusText);
    
    if (!response.ok) {
      // Clonar: leer .text() del cuerpo agota el stream; el caller debe poder hacer .json()
      const errBody = await response.clone().text();
      console.error('❌ Error en respuesta:', response.status, errBody);
    }

    return response;
  } catch (error: any) {
    console.error('❌❌❌ Error en fetchWithCSRF ❌❌❌');
    console.error('❌ URL:', url);
    console.error('❌ Error message:', error.message);
    console.error('❌ Error stack:', error.stack);
    
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
