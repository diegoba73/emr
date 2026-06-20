import { apiService } from './api';
import { User } from '../types';

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface LoginResponse {
  user: User;
  message: string;
}

/**
 * Servicio de autenticación
 * Encapsula las llamadas de autenticación usando la instancia de api configurada
 */
class AuthService {
  /**
   * Inicia sesión con credenciales
   * @param credentials - Usuario y contraseña
   * @returns Usuario autenticado y mensaje de éxito
   */
  async login(credentials: LoginCredentials): Promise<LoginResponse> {
    try {
      const response = await apiService.login(credentials.username, credentials.password);
      return response;
    } catch (error: any) {
      // Si es un error de conexión, mantener el mensaje descriptivo
      if (error.isConnectionError) {
        throw error;
      }
      // Para otros errores, extraer el mensaje apropiado
      const errorMessage = error.response?.data?.detail || 
                          error.response?.data?.error ||
                          error.message || 
                          'Error al iniciar sesión';
      const authError = new Error(errorMessage);
      (authError as any).response = error.response;
      throw authError;
    }
  }

  /**
   * Cierra la sesión del usuario
   */
  async logout(): Promise<void> {
    try {
      await apiService.logout();
    } catch (error: any) {
      // Aún así limpiamos el estado local si falla
      console.error('Error al cerrar sesión:', error);
      throw error;
    }
  }

  /**
   * Obtiene el usuario actual autenticado
   * @returns Usuario actual o null si no está autenticado
   */
  async getCurrentUser(): Promise<User | null> {
    try {
      const user = await apiService.getCurrentUser();
      return user;
    } catch (error: any) {
      // Si es 401, el usuario no está autenticado
      if (error.response?.status === 401) {
        return null;
      }
      // Para otros errores, re-lanzar
      throw error;
    }
  }
}

export const authService = new AuthService();
export default authService;



