/**
 * Cliente API unificado - Instancia axios compartida para todo el frontend.
 * Garantiza configuración consistente de CSRF, credenciales y manejo de errores.
 */
import axios, { AxiosInstance } from 'axios';
import { getCSRFToken } from '../utils/csrf';
import { resolveApiBaseUrl } from './apiBaseUrl';

const API_BASE_URL = resolveApiBaseUrl();

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

// Si el SPA se abrió por IP LAN, re-apuntar el API a esa misma IP (sin Internet).
apiClient.interceptors.request.use((config) => {
  const live = resolveApiBaseUrl();
  if (live && config.baseURL !== live) {
    config.baseURL = live;
  }
  return config;
});

// Interceptor: agregar CSRF token a peticiones no seguras
apiClient.interceptors.request.use(
  async (config) => {
    // FormData: dejar que el runtime ponga multipart + boundary (no application/json).
    if (typeof FormData !== 'undefined' && config.data instanceof FormData) {
      if (config.headers && typeof config.headers === 'object') {
        delete (config.headers as Record<string, unknown>)['Content-Type'];
        delete (config.headers as Record<string, unknown>)['content-type'];
      }
    }
    const method = (config.method || '').toLowerCase();
    if (['post', 'put', 'patch', 'delete'].includes(method)) {
      let csrfToken = getCSRFToken();
      if (!csrfToken) {
        try {
          await fetch(`${API_BASE_URL}/`, { method: 'GET', credentials: 'include' });
          csrfToken = getCSRFToken();
        } catch (error) {
          console.warn('No se pudo obtener el token CSRF:', error);
        }
      }
      if (csrfToken) {
        config.headers['X-CSRFToken'] = csrfToken;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Interceptor: manejo de errores de autenticación y red
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    if (status === 401) {
      const path = window.location?.pathname || '';
      const publicPaths = [
        '/login',
        '/register',
        '/pantalla-sala',
        '/kiosco-recepcion',
        '/espera',
        '/demo',
      ];
      if (!publicPaths.some((p) => path.startsWith(p))) {
        window.location.href = '/login';
      }
    } else if (error?.code === 'ERR_NETWORK' || error?.message === 'Network Error') {
      console.warn('Error de red: el servidor backend no está disponible.');
    }
    // 403: permisos — no cerrar sesión; lo maneja la UI (toast / deshabilitar acciones).
    return Promise.reject(error);
  }
);

export { API_BASE_URL };
