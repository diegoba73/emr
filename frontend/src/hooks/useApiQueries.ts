/**
 * Hooks de React Query para turnos, pacientes y archivos médicos.
 * Extienden el uso de React Query (actualmente solo en atenciones) a otros dominios.
 * Permiten cache, refetch automático y estados de loading/error consistentes.
 */
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiService } from '../services/api';
import { api } from '../services/apiService';

const STALE_TIME = 60 * 1000; // 1 minuto
const GC_TIME = 5 * 60 * 1000; // 5 minutos

export const useTurnosQuery = () =>
  useQuery({
    queryKey: ['turnos'],
    queryFn: async () => {
      const res = await apiService.getTurnos();
      return res.results || res;
    },
    staleTime: STALE_TIME,
    gcTime: GC_TIME,
  });

export const usePacientesQuery = (options?: { all?: boolean; enabled?: boolean }) =>
  useQuery({
    queryKey: ['pacientes', options?.all],
    queryFn: async () => {
      const params = options?.all ? { all: 'true', page_size: 1000 } : { page_size: 1000 };
      const res = await api.get('/pacientes/', { params });
      const data = res.data as { results?: unknown[] } | unknown[];
      return Array.isArray(data) ? data : (data && typeof data === 'object' && 'results' in data ? (data as { results: unknown[] }).results : []);
    },
    staleTime: STALE_TIME,
    gcTime: GC_TIME,
    enabled: options?.enabled !== false,
  });

export const useArchivosMedicosQuery = (pacienteId?: number | null) =>
  useQuery({
    queryKey: ['archivosMedicos', pacienteId ?? 'all'],
    queryFn: async () => {
      const params = pacienteId ? { paciente_id: pacienteId } : { page_size: 1000 };
      const res = await api.get('/archivos-medicos/archivos/', { params });
      const data = res.data as { results?: unknown[] } | unknown[];
      return Array.isArray(data) ? data : (data && typeof data === 'object' && 'results' in data ? (data as { results: unknown[] }).results : []);
    },
    staleTime: STALE_TIME,
    gcTime: GC_TIME,
  });

/**
 * Invalida y refetch de turnos (útil después de crear/actualizar/eliminar)
 */
export const useInvalidateTurnos = () => {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: ['turnos'] });
};

/**
 * Invalida y refetch de pacientes
 */
export const useInvalidatePacientes = () => {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: ['pacientes'] });
};
