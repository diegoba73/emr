/**
 * Servicio para gestión de infraestructura de internación (Sectores y Camas)
 */
import { api } from './apiService';
import { Sector, Cama, InternacionCama } from '../types';

// Tipo para respuestas paginadas de la API
interface PaginatedResponse<T> {
  results?: T[];
  count?: number;
  next?: string | null;
  previous?: string | null;
}

// ============================================================================
// SECTORES
// ============================================================================

/**
 * Obtiene todos los sectores
 */
export const getSectores = async (): Promise<Sector[]> => {
  try {
    const response = await api.get<Sector[] | PaginatedResponse<Sector>>('/internacion/sectores/');
    const data = response.data as PaginatedResponse<Sector> | Sector[];
    return (data as PaginatedResponse<Sector>).results || (data as Sector[]);
  } catch (error) {
    console.error('Error fetching sectores:', error);
    throw error;
  }
};

/**
 * Crea un nuevo sector
 */
export const createSector = async (sectorData: { nombre: string }): Promise<Sector> => {
  try {
    const response = await api.post<Sector>('/internacion/sectores/', sectorData);
    return response.data;
  } catch (error) {
    console.error('Error creating sector:', error);
    throw error;
  }
};

/**
 * Actualiza un sector existente
 */
export const updateSector = async (id: number, sectorData: Partial<Sector>): Promise<Sector> => {
  try {
    const response = await api.patch<Sector>(`/internacion/sectores/${id}/`, sectorData);
    return response.data;
  } catch (error) {
    console.error('Error updating sector:', error);
    throw error;
  }
};

/**
 * Elimina un sector
 */
export const deleteSector = async (id: number): Promise<void> => {
  try {
    await api.delete(`/internacion/sectores/${id}/`);
  } catch (error) {
    console.error('Error deleting sector:', error);
    throw error;
  }
};

// ============================================================================
// CAMAS
// ============================================================================

/**
 * Obtiene todas las camas (opcionalmente filtradas por sector)
 */
export const getCamas = async (sector?: string | number): Promise<Cama[]> => {
  try {
    const url = sector 
      ? `/internacion/camas/?sector=${sector}`
      : '/internacion/camas/';
    const response = await api.get<Cama[] | PaginatedResponse<Cama>>(url);
    const data = response.data as PaginatedResponse<Cama> | Cama[];
    return (data as PaginatedResponse<Cama>).results || (data as Cama[]);
  } catch (error) {
    console.error('Error fetching camas:', error);
    throw error;
  }
};

/**
 * Obtiene una cama por ID
 */
export const getCama = async (id: number): Promise<Cama> => {
  try {
    const response = await api.get<Cama>(`/internacion/camas/${id}/`);
    return response.data;
  } catch (error) {
    console.error('Error fetching cama:', error);
    throw error;
  }
};

/**
 * Crea una nueva cama
 */
export const createCama = async (camaData: {
  nombre: string;
  sector: number;
  estado?: 'DISPONIBLE' | 'OCUPADA' | 'LIMPIEZA' | 'MANTENIMIENTO';
  aislada?: boolean;
}): Promise<Cama> => {
  try {
    // El serializer espera sector_id, no sector
    const response = await api.post<Cama>('/internacion/camas/', {
      nombre: camaData.nombre,
      sector_id: camaData.sector, // Mapear sector a sector_id
      estado: camaData.estado || 'DISPONIBLE',
      aislada: camaData.aislada || false,
    });
    return response.data;
  } catch (error) {
    console.error('Error creating cama:', error);
    throw error;
  }
};

/**
 * Actualiza una cama existente
 */
export const updateCama = async (
  id: number,
  camaData: {
    nombre?: string;
    sector?: number;
    estado?: 'DISPONIBLE' | 'OCUPADA' | 'LIMPIEZA' | 'MANTENIMIENTO';
    aislada?: boolean;
  }
): Promise<Cama> => {
  try {
    const payload: Record<string, unknown> = { ...camaData };
    if (camaData.sector !== undefined) {
      payload.sector_id = camaData.sector;
      delete payload.sector;
    }
    const response = await api.patch<Cama>(`/internacion/camas/${id}/`, payload);
    return response.data;
  } catch (error) {
    console.error('Error updating cama:', error);
    throw error;
  }
};

/**
 * Elimina una cama
 */
export const deleteCama = async (id: number): Promise<void> => {
  try {
    await api.delete(`/internacion/camas/${id}/`);
  } catch (error) {
    console.error('Error deleting cama:', error);
    throw error;
  }
};

// ============================================================================
// INTERNACIONES
// ============================================================================

/**
 * Obtiene todas las internaciones activas
 */
export const getInternacionesActivas = async (): Promise<InternacionCama[]> => {
  try {
    const response = await api.get<InternacionCama[] | PaginatedResponse<InternacionCama>>('/internacion/internaciones/');
    const data = response.data as PaginatedResponse<InternacionCama> | InternacionCama[];
    return (data as PaginatedResponse<InternacionCama>).results || (data as InternacionCama[]);
  } catch (error) {
    console.error('Error fetching internaciones activas:', error);
    throw error;
  }
};

/**
 * Crea una nueva internación (admitir paciente)
 */
export const createInternacion = async (data: {
  paciente: number;
  cama: number;
  medico?: number | null;
  diagnostico_ingreso?: string;
  diagnostico_cie_id?: number | null;
}): Promise<InternacionCama> => {
  try {
    const response = await api.post<InternacionCama>('/internacion/internaciones/', data);
    return response.data;
  } catch (error) {
    console.error('Error creating internacion:', error);
    throw error;
  }
};

