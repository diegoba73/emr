import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import {
  Atencion,
  ConsultaAmbulatoriaRecord,
  EstudioDiagnostico,
  ProcedimientoCatalogo,
} from '../../types';
import { apiService } from '../../services/api';

export interface AtencionFilters {
  tipo_intervencion?: string;
  medico_id?: number | null;
  estado_clinico?: string;
  start_date?: string;
  end_date?: string;
  search?: string;
}

const buildParams = (filters: AtencionFilters | undefined) => {
  if (!filters) return undefined;
  const params: Record<string, any> = {};
  if (filters.tipo_intervencion) params.tipo_intervencion = filters.tipo_intervencion;
  if (filters.medico_id) params.medico_principal = filters.medico_id;
  if (filters.estado_clinico) params.estado_clinico = filters.estado_clinico;
  if (filters.start_date) params.fecha_admision__gte = filters.start_date;
  if (filters.end_date) params.fecha_admision__lte = filters.end_date;
  if (filters.search) params.search = filters.search;
  return params;
};

export const useAtencionesQuery = (filters: AtencionFilters, options?: { enabled?: boolean }) =>
  useQuery({
    queryKey: ['atenciones', filters],
    queryFn: () => apiService.getAtenciones(buildParams(filters)),
    placeholderData: (previousData) => previousData,
    enabled: options?.enabled !== false, // OPTIMIZACIÓN: Permitir deshabilitar la query
    staleTime: 60000, // 1 minuto - OPTIMIZACIÓN: Cache por 1 minuto para evitar recargas innecesarias
    gcTime: 5 * 60 * 1000, // 5 minutos
  });

export const useAtencionQuery = (atencionId?: number | null) =>
  useQuery({
    queryKey: ['atencion', atencionId],
    queryFn: async () => {
      const atencion = await apiService.getAtencion(atencionId as number);
      // Normalizar documentos para asegurar que sea un array
      if (atencion) {
        if (!Array.isArray(atencion.documentos)) {
          atencion.documentos = (atencion.documentos as any)?.results || [];
        }
      }
      return atencion;
    },
    enabled: Boolean(atencionId) && atencionId !== null && atencionId !== undefined,
    retry: (failureCount, error: any) => {
      if (error?.response?.status === 404 || error?.response?.status === 403) {
        return false;
      }
      return failureCount < 2;
    },
    retryDelay: 1000,
    staleTime: 0,
    gcTime: 5 * 60 * 1000,
  });

/**
 * Hook centralizado para refrescar todos los datos relacionados con una atención.
 * Invalida y refetch todas las queries relacionadas: atención y archivos médicos.
 */
export const useAtencionRefetch = (atencionId: number) => {
  const queryClient = useQueryClient();

  const refetchAtencionCompleta = async () => {
    // Invalidar todas las queries relacionadas con esta atención
    await queryClient.invalidateQueries({ queryKey: ['atencion', atencionId] });
    await queryClient.invalidateQueries({ queryKey: ['archivosMedicos', atencionId] });
    await queryClient.invalidateQueries({ queryKey: ['archivosMedicos'] });
    
    // Forzar refetch de la atención principal
    await queryClient.refetchQueries({ queryKey: ['atencion', atencionId] });
    
    // También invalidar la lista de atenciones
    await queryClient.invalidateQueries({ queryKey: ['atenciones'] });
  };

  return { refetchAtencionCompleta };
};

export const useUpdateAtencionMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Atencion> }) => apiService.updateAtencion(id, data),
    onSuccess: (data) => {
      toast.success('Atención actualizada');
      queryClient.invalidateQueries({ queryKey: ['atencion', data.id] });
      queryClient.invalidateQueries({ queryKey: ['atenciones'] });
    },
    onError: () => toast.error('No se pudo actualizar la atención'),
  });
};

export const useCloseAtencionMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiService.closeAtencion(id),
    onSuccess: (data) => {
      toast.success('Atención cerrada correctamente');
      queryClient.invalidateQueries({ queryKey: ['atencion', data.id] });
      queryClient.invalidateQueries({ queryKey: ['atenciones'] });
    },
    onError: () => toast.error('No se pudo cerrar la atención'),
  });
};

export const useUploadDocumentoMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (formData: FormData) => apiService.uploadDocumento(formData),
    onSuccess: async (data, variables) => {
      toast.success('Documento subido');
      // Obtener el atencion_id de la respuesta o del FormData
      let atencionId: number | undefined = data.atencion_id;
      if (!atencionId && variables instanceof FormData) {
        const atencionIdStr = variables.get('atencion_id');
        if (atencionIdStr) {
          atencionId = Number(atencionIdStr);
        }
      }
      if (atencionId) {
        await queryClient.invalidateQueries({ queryKey: ['atencion', atencionId] });
        await queryClient.invalidateQueries({ queryKey: ['archivosMedicos', atencionId] });
        await queryClient.invalidateQueries({ queryKey: ['archivosMedicos'] });
        await queryClient.invalidateQueries({ queryKey: ['atenciones'] });
        await queryClient.refetchQueries({
          queryKey: ['atencion', atencionId],
          exact: false,
        });
      }
    },
    onError: () => toast.error('No se pudo subir el documento'),
  });
};

export const useDeleteDocumentoMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, atencionId }: { id: number; atencionId: number }) => apiService.deleteDocumento(id),
    onSuccess: async (_data, variables) => {
      toast.success('Documento eliminado');
      // Invalidar queries para que se refresquen automáticamente
      // No necesitamos refetches defensivos porque los IDs siempre están presentes
      await queryClient.invalidateQueries({ queryKey: ['atencion', variables.atencionId] });
      await queryClient.invalidateQueries({ queryKey: ['archivosMedicos', variables.atencionId] });
      await queryClient.invalidateQueries({ queryKey: ['archivosMedicos'] });
      await queryClient.invalidateQueries({ queryKey: ['atenciones'] });
    },
    onError: () => toast.error('No se pudo eliminar el documento'),
  });
};

interface SaveConsultaPayload {
  atencionId: number;
  data: Partial<ConsultaAmbulatoriaRecord>;
  exists: boolean;
  registroId?: number;
}

export const useSaveConsultaAmbulatoriaMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ atencionId, data, exists, registroId }: SaveConsultaPayload) => {
      try {
        const atencion = await apiService.getAtencion(atencionId);
        
        // Extraer el ID de consulta_ambulatoria de diferentes formas posibles
        let consultaId: number | undefined = undefined;
        
        if (atencion.consulta_ambulatoria) {
          // Caso 1: consulta_ambulatoria es un objeto con id
          if (typeof atencion.consulta_ambulatoria === 'object') {
            if ('id' in atencion.consulta_ambulatoria && atencion.consulta_ambulatoria.id) {
              consultaId = atencion.consulta_ambulatoria.id;
            }
          }
          // Caso 2: consulta_ambulatoria es directamente un número (poco probable pero posible)
          else if (typeof atencion.consulta_ambulatoria === 'number') {
            consultaId = atencion.consulta_ambulatoria;
          }
        }
        
        // Si tenemos registroId del prop, usarlo como fallback
        if (!consultaId && registroId) {
          consultaId = registroId;
        }
        
        // Si encontramos un ID, usar PATCH para actualizar
        if (consultaId) {
          return apiService.updateConsultaAmbulatoria(atencionId, data, consultaId);
        }

        return apiService.createConsultaAmbulatoria(atencionId, data);
      } catch (error: any) {
        // Si el error es que ya existe, intentar obtener el ID y actualizar
        if (error?.response?.status === 400) {
          const errorMessage = error?.response?.data?.error || '';
          if (errorMessage.includes('Ya existe un registro') || errorMessage.includes('ya existe') || errorMessage.toLowerCase().includes('ya existe')) {
            try {
              await new Promise(resolve => setTimeout(resolve, 100));

              const atencion = await apiService.getAtencion(atencionId);
              
              let consultaId: number | undefined = undefined;
              
              if (atencion.consulta_ambulatoria) {
                if (typeof atencion.consulta_ambulatoria === 'object' && 'id' in atencion.consulta_ambulatoria) {
                  consultaId = atencion.consulta_ambulatoria.id;
                } else if (typeof atencion.consulta_ambulatoria === 'number') {
                  consultaId = atencion.consulta_ambulatoria;
                }
              }
              
              if (consultaId) {
                return apiService.updateConsultaAmbulatoria(atencionId, data, consultaId);
              } else if (registroId) {
                return apiService.updateConsultaAmbulatoria(atencionId, data, registroId);
              } else {
                return apiService.updateConsultaAmbulatoria(atencionId, data);
              }
            } catch (retryError: any) {
              // Si updateConsultaAmbulatoria falla porque no existe, relanzar el error original
              if (retryError?.message?.includes('No existe un registro')) {
                throw error; // Relanzar el error original
              }
              throw retryError;
            }
          }
        }
        
        // Si falla al obtener la atención o no se pudo resolver, intentar crear/actualizar según registroId
        if (registroId) {
          return apiService.updateConsultaAmbulatoria(atencionId, data, registroId);
        }
        return apiService.createConsultaAmbulatoria(atencionId, data);
      }
    },
    onSuccess: async (_data, variables) => {
      toast.success('Consulta guardada');
      
      // SIEMPRE actualizar el turno a REALIZADO después de guardar la consulta
      try {
        // Obtener la atención para acceder al turno asociado
        const atencion = await apiService.getAtencion(variables.atencionId);
        const turnoId = atencion.turno?.id || atencion.turno_id;
        if (turnoId) {
          await apiService.updateTurno(turnoId, { estado: 'REALIZADO' });
        }
      } catch {
        // No fallar la operación si no se puede actualizar el turno
      }

      await queryClient.invalidateQueries({ queryKey: ['atencion', variables.atencionId] });
      await queryClient.invalidateQueries({ queryKey: ['atenciones'] });
      await queryClient.invalidateQueries({ queryKey: ['turnos'] });
      
      // 2. Forzar refetch inmediato y esperar a que complete
      await Promise.all([
        queryClient.refetchQueries({ queryKey: ['atencion', variables.atencionId] }),
        queryClient.refetchQueries({ queryKey: ['turnos'] })
      ]);
    },
    onError: (error: any) => {
      const errorMessage = error?.response?.data?.error || error?.message || 'No se pudo guardar la consulta';
      toast.error(errorMessage);
    },
  });
};

interface SaveProcedimientoPayload {
  atencionId: number;
  formData: FormData;
  exists: boolean;
  registroId?: number;
}

export const useSaveRegistroProcedimientoMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ atencionId, formData, exists, registroId }: SaveProcedimientoPayload) =>
      exists
        ? apiService.updateRegistroProcedimiento(atencionId, formData, registroId)
        : apiService.createRegistroProcedimiento(atencionId, formData),
    onSuccess: async (_data, variables) => {
      toast.success('Registro de procedimiento guardado');
      // Invalidar todas las queries relacionadas y forzar refetch
      await queryClient.invalidateQueries({ queryKey: ['atencion', variables.atencionId] });
      await queryClient.invalidateQueries({ queryKey: ['atenciones'] });
      await queryClient.invalidateQueries({ queryKey: ['turnos'] });
      // Forzar refetch inmediato de atención y turnos para asegurar que se actualicen
      await queryClient.refetchQueries({ queryKey: ['atencion', variables.atencionId] });
      await queryClient.refetchQueries({ queryKey: ['turnos'] });
    },
    onError: () => toast.error('No se pudo guardar el procedimiento'),
  });
};

interface SaveCirugiaPayload {
  atencionId: number;
  formData: FormData;
  exists: boolean;
  registroId?: number;
}

export const useSaveRegistroQuirurgicoMutation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ atencionId, formData, exists, registroId }: SaveCirugiaPayload) => {
      if (exists || registroId) {
        try {
          let idToUse = registroId;
          if (!idToUse) {
            const atencion = await apiService.getAtencion(atencionId);
            idToUse = atencion.registro_quirurgico?.id || 
                     (atencion.registro_quirurgico && typeof atencion.registro_quirurgico === 'object' && 'id' in atencion.registro_quirurgico 
                       ? (atencion.registro_quirurgico as any).id 
                       : undefined);
          }
          
          if (!idToUse) {
            throw new Error('No se pudo obtener el ID del registro quirúrgico para actualizar');
          }
          
          return await apiService.updateRegistroQuirurgico(atencionId, formData, idToUse);
        } catch (updateError: any) {
          if (updateError?.message?.includes('No existe un registro')) {
            return await apiService.createRegistroQuirurgico(atencionId, formData);
          }
          if (updateError?.response?.data?.error?.includes('Ya existe un registro')) {
            const atencion = await apiService.getAtencion(atencionId);
            const idToUse = atencion.registro_quirurgico?.id || 
                           (atencion.registro_quirurgico && typeof atencion.registro_quirurgico === 'object' && 'id' in atencion.registro_quirurgico 
                             ? (atencion.registro_quirurgico as any).id 
                             : undefined);
            if (idToUse) {
              return await apiService.updateRegistroQuirurgico(atencionId, formData, idToUse);
            }
          }
          throw updateError;
        }
      } else {
        try {
          return await apiService.createRegistroQuirurgico(atencionId, formData);
        } catch (createError: any) {
          const errorMessage = createError?.response?.data?.error || createError?.message || '';
          if (errorMessage.includes('Ya existe un registro') || errorMessage.includes('ya existe')) {
            try {
              const atencion = await apiService.getAtencion(atencionId);
              
              const idToUse = atencion.registro_quirurgico?.id || 
                             (atencion.registro_quirurgico && typeof atencion.registro_quirurgico === 'object' && 'id' in atencion.registro_quirurgico 
                               ? (atencion.registro_quirurgico as any).id 
                               : undefined);
              
              if (idToUse) {
                return await apiService.updateRegistroQuirurgico(atencionId, formData, idToUse);
              } else {
                throw new Error('No se pudo obtener el ID del registro quirúrgico para actualizar');
              }
            } catch (updateError: any) {
              throw updateError;
            }
          }
          throw createError;
        }
      }
    },
    onSuccess: async (_data, variables) => {
      toast.success('Registro quirúrgico guardado exitosamente');
      // Invalidar todas las queries relacionadas y forzar refetch
      await queryClient.invalidateQueries({ queryKey: ['atencion', variables.atencionId] });
      await queryClient.invalidateQueries({ queryKey: ['atenciones'] });
      await queryClient.invalidateQueries({ queryKey: ['turnos'] });
      // Forzar refetch inmediato de atención y turnos para asegurar que se actualicen
      await queryClient.refetchQueries({ queryKey: ['atencion', variables.atencionId] });
      await queryClient.refetchQueries({ queryKey: ['turnos'] });
    },
    onError: (error: any) => {
      const errorMessage = error?.response?.data?.error || error?.message || 'No se pudo guardar la cirugía';
      toast.error(errorMessage);
    },
  });
};

export const useEstudiosDiagnosticoQuery = () =>
  useQuery<EstudioDiagnostico[]>({
    queryKey: ['catalogo-estudios'],
    queryFn: () => apiService.getEstudiosDiagnostico(),
    staleTime: 1000 * 60 * 5,
  });

export const useProcedimientosCatalogoQuery = () =>
  useQuery<ProcedimientoCatalogo[]>({
    queryKey: ['catalogo-procedimientos'],
    queryFn: () => apiService.getProcedimientosCatalogo(),
    staleTime: 1000 * 60 * 5,
  });

export type SaveConsultaMutation = ReturnType<typeof useSaveConsultaAmbulatoriaMutation>;
export type SaveProcedimientoMutation = ReturnType<typeof useSaveRegistroProcedimientoMutation>;
export type SaveCirugiaMutation = ReturnType<typeof useSaveRegistroQuirurgicoMutation>;

