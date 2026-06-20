/**
 * Cliente API unificado - Instancia axios compartida para todo el frontend.
 * Garantiza configuración consistente de CSRF, credenciales y manejo de errores.
 */
import axios, { AxiosInstance } from 'axios';
import { getCSRFToken } from '../utils/csrf';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

// Interceptor: agregar CSRF token a peticiones no seguras
apiClient.interceptors.request.use(
  async (config) => {
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
      window.location.href = '/login';
    } else if (error?.code === 'ERR_NETWORK' || error?.message === 'Network Error') {
      console.warn('Error de red: el servidor backend no está disponible.');
    }
    // 403: permisos — no cerrar sesión; lo maneja la UI (toast / deshabilitar acciones).
    return Promise.reject(error);
  }
);

export { API_BASE_URL };
