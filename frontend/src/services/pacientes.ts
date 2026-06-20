import { apiService } from './api';
import { Paciente } from '../types';
import { AxiosResponse } from 'axios';
import { api } from './apiService';

export interface PacienteFormData {
  nombre: string;
  apellido: string;
  dni: string;
  fecha_nacimiento?: string;
  sexo?: 'M' | 'F';
  telefono?: string;
  email?: string;
  direccion?: string;
  obra_social?: string;
  numero_afiliado?: string;
  observaciones?: string;
}

export interface PacientesResponse {
  count: number;
  next?: string | null;
  previous?: string | null;
  results: Paciente[];
}

/**
 * Servicio de gestión de pacientes
 * Encapsula las llamadas a la API de pacientes
 */
class PacientesService {
  /**
   * Obtiene todos los pacientes con paginación
   * @param page - Número de página (opcional)
   * @returns Lista de pacientes con información de paginación
   */
  async getAll(page?: number): Promise<PacientesResponse> {
    try {
      const response = await apiService.getPacientes();
      // Convertir ApiResponse a PacientesResponse
      return {
        count: response.count || response.results.length,
        next: response.next || null,
        previous: response.previous || null,
        results: response.results,
      };
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || error.message || 'Error al obtener pacientes');
    }
  }

  /**
   * Busca pacientes por query (DNI, apellido, nombre)
   * @param query - Término de búsqueda
   * @returns Lista de pacientes que coinciden con la búsqueda
   */
  async search(query: string): Promise<Paciente[]> {
    try {
      const pacientes = await apiService.buscarPacientes(query);
      return pacientes;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || error.message || 'Error al buscar pacientes');
    }
  }

  /**
   * Obtiene un paciente por ID
   * @param id - ID del paciente
   * @returns Datos del paciente
   */
  async getById(id: number): Promise<Paciente> {
    try {
      const paciente = await apiService.getPaciente(id);
      return paciente;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || error.message || 'Error al obtener paciente');
    }
  }

  /**
   * Crea un nuevo paciente
   * @param data - Datos del paciente
   * @returns Paciente creado
   */
  async create(data: PacienteFormData): Promise<Paciente> {
    try {
      const paciente = await apiService.createPaciente(data);
      return paciente;
    } catch (error: any) {
      // Re-lanzar el error para que el componente pueda manejarlo
      const errorMessage = error.response?.data?.detail || error.message || 'Error al crear paciente';
      
      // Si es un error de DNI duplicado, lanzar un error específico
      if (error.response?.status === 400 && errorMessage.toLowerCase().includes('dni')) {
        throw new Error('DNI_DUPLICADO');
      }
      
      throw new Error(errorMessage);
    }
  }

  /**
   * Actualiza un paciente existente
   * @param id - ID del paciente
   * @param data - Datos actualizados del paciente
   * @returns Paciente actualizado
   */
  async update(id: number, data: PacienteFormData): Promise<Paciente> {
    try {
      const paciente = await apiService.updatePaciente(id, data);
      return paciente;
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || 'Error al actualizar paciente';
      
      // Si es un error de DNI duplicado, lanzar un error específico
      if (error.response?.status === 400 && errorMessage.toLowerCase().includes('dni')) {
        throw new Error('DNI_DUPLICADO');
      }
      
      throw new Error(errorMessage);
    }
  }

  /**
   * Elimina un paciente
   * @param id - ID del paciente
   */
  async delete(id: number): Promise<void> {
    try {
      await apiService.deletePaciente(id);
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || error.message || 'Error al eliminar paciente');
    }
  }
}

export const pacientesService = new PacientesService();
export default pacientesService;

/**
 * Helper function to get pacientes using axios
 * @param all - For médicos, if true, gets all pacientes (uses ?all=true)
 * @returns Axios response with pacientes data
 */
export const getPacientes = (all = false) => {
  const params = all ? { all: true } : {};
  return api.get<Paciente[]>('/pacientes/', { params });
};/**
 * Get historia clínica by paciente ID
 * @param pacienteId - ID del paciente
 * @returns Historia clínica data
 */
export const getHistoriaClinica = async (pacienteId: number) => {
  try {
    const response = await api.get('/historias-clinicas/', {
      params: { paciente: pacienteId }
    });
    // La respuesta puede ser una lista, tomar el primero si existe
    const data = response.data.results || response.data;
    return Array.isArray(data) && data.length > 0 ? data[0] : null;
  } catch (error) {
    console.error('Error fetching historia clínica:', error);
    throw error;
  }
};