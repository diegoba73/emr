import { 
  Paciente, 
  Turno, 
  Medico, 
  Consulta, 
  ArchivoMedico,
  Solicitud,
  DiagnosticoCIE10,
  EstudioDiagnostico,
  ProcedimientoCatalogo,
  Medicamento,
  Especialidad,
  Cama,
  InternacionCama,
  Sector,
  TipoExamen
} from '../types';
import { apiClient as api, API_BASE_URL } from './apiClient';

/**
 * Normaliza una URL absoluta a una ruta relativa para usar con la instancia de api
 * que ya tiene baseURL configurado. Evita duplicar /api/ en la URL.
 * 
 * @param url - URL absoluta o relativa (ej: 'http://localhost:8000/api/medicos/?page=2')
 * @returns Ruta relativa (ej: '/medicos/?page=2')
 */
const normalizeUrl = (url: string): string => {
  if (!url) return '';
  
  // Si ya es relativa y no empieza con /api/, retornarla tal cual
  if (url.startsWith('/') && !url.startsWith('/api/')) {
    return url;
  }
  
  // Si empieza con http://localhost:8000/api/, extraer solo la ruta después de /api
  if (url.startsWith(API_BASE_URL + '/')) {
    return url.replace(API_BASE_URL, '') || '/';
  }
  
  // Si empieza con /api/, quitar /api
  if (url.startsWith('/api/')) {
    return url.replace('/api', '');
  }
  
  // Si no empieza con /, agregarlo
  if (!url.startsWith('/')) {
    return '/' + url;
  }
  
  return url;
};

// Re-exportar la instancia api para compatibilidad
export { api };

// Pacientes
export const getPacientes = async (): Promise<Paciente[]> => {
  try {
    const response = await api.get('/pacientes/');
    return response.data.results || response.data;
  } catch (error) {
    console.error('Error fetching pacientes:', error);
    throw error;
  }
};

export const createPaciente = async (pacienteData: Partial<Paciente>): Promise<Paciente> => {
  try {
    const response = await api.post('/pacientes/', pacienteData);
    return response.data;
  } catch (error) {
    console.error('Error creating paciente:', error);
    throw error;
  }
};

export const updatePaciente = async (id: number, pacienteData: Partial<Paciente>): Promise<Paciente> => {
  try {
    const response = await api.patch(`/pacientes/${id}/`, pacienteData);
    return response.data;
  } catch (error) {
    console.error('Error updating paciente:', error);
    throw error;
  }
};

export const deletePaciente = async (id: number): Promise<void> => {
  try {
    await api.delete(`/pacientes/${id}/`);
  } catch (error) {
    console.error('Error deleting paciente:', error);
    throw error;
  }
};

// Médicos - SIEMPRE obtener TODOS los registros
export const getMedicos = async (): Promise<Medico[]> => {
  try {
    const response = await api.get('/medicos/');
    // Si hay paginación, obtener todas las páginas
    if (response.data.results) {
      let allMedicos = [...response.data.results];
      let nextUrl = response.data.next;
      
      // Obtener todas las páginas si existen
      while (nextUrl) {
        const relativeUrl = normalizeUrl(nextUrl);
        const nextResponse = await api.get(relativeUrl);
        allMedicos = [...allMedicos, ...nextResponse.data.results];
        nextUrl = nextResponse.data.next;
      }
      
      return allMedicos;
    }
    // Si no hay paginación, retornar directamente
    return Array.isArray(response.data) ? response.data : [];
  } catch (error) {
    console.error('Error fetching medicos:', error);
    throw error;
  }
};

// Turnos
export const getTurnos = async (): Promise<Turno[]> => {
  try {
    const response = await api.get('/turnos/');
    return response.data.results || response.data;
  } catch (error) {
    console.error('Error fetching turnos:', error);
    throw error;
  }
};

export const createTurno = async (turnoData: Partial<Turno>): Promise<Turno> => {
  try {
    const response = await api.post('/turnos/', turnoData);
    return response.data;
  } catch (error) {
    console.error('Error creating turno:', error);
    throw error;
  }
};

export const updateTurno = async (id: number, turnoData: Partial<Turno>): Promise<Turno> => {
  try {
    const response = await api.patch(`/turnos/${id}/`, turnoData);
    return response.data;
  } catch (error) {
    console.error('Error updating turno:', error);
    throw error;
  }
};

export const deleteTurno = async (id: number): Promise<void> => {
  try {
    await api.delete(`/turnos/${id}/`);
  } catch (error) {
    console.error('Error deleting turno:', error);
    throw error;
  }
};

export const confirmarTurno = async (id: number): Promise<Turno> => {
  try {
    const response = await api.post(`/turnos/${id}/confirmar/`, {});
    return response.data.turno ?? response.data;
  } catch (error) {
    console.error('Error confirming turno:', error);
    throw error;
  }
};

export const cancelarTurno = async (id: number, motivo: string): Promise<Turno> => {
  try {
    const response = await api.post(`/turnos/${id}/cancelar/`, { motivo });
    return response.data.turno ?? response.data;
  } catch (error) {
    console.error('Error cancelling turno:', error);
    throw error;
  }
};

// Consultas
export const getConsultas = async (params?: { historia_clinica_id?: number; page_size?: number }): Promise<{ results: Consulta[]; count: number; next?: string; previous?: string }> => {
  try {
    const queryParams: Record<string, string | number> = { page_size: params?.page_size || 1000 };
    if (params?.historia_clinica_id) {
      queryParams.historia_clinica_id = params.historia_clinica_id;
    }
    const response = await api.get('/consultas/', { params: queryParams });
    
    // Si hay paginación, obtener todas las páginas
    if (response.data.results && response.data.next) {
      let allItems = [...response.data.results];
      let nextUrl = response.data.next;
      
      while (nextUrl) {
        const nextResponse = await api.get(normalizeUrl(nextUrl));
        allItems = [...allItems, ...nextResponse.data.results];
        nextUrl = nextResponse.data.next;
      }
      
      return {
        results: allItems,
        count: response.data.count || allItems.length,
        next: undefined,
        previous: undefined,
      };
    }
    
    // Si no hay paginación, retornar como está
    if (response.data.results) {
      return response.data;
    }
    
    // Si es un array directo
    return {
      results: Array.isArray(response.data) ? response.data : [],
      count: Array.isArray(response.data) ? response.data.length : 0,
    };
  } catch (error) {
    console.error('Error fetching consultas:', error);
    throw error;
  }
};

export const createConsulta = async (consultaData: Partial<Consulta>): Promise<Consulta> => {
  try {
    const response = await api.post('/consultas/', consultaData);
    return response.data;
  } catch (error) {
    console.error('Error creating consulta:', error);
    throw error;
  }
};

export const updateConsulta = async (id: number, consultaData: Partial<Consulta>): Promise<Consulta> => {
  try {
    const response = await api.patch(`/consultas/${id}/`, consultaData);
    return response.data;
  } catch (error) {
    console.error('Error updating consulta:', error);
    throw error;
  }
};

export const deleteConsulta = async (id: number): Promise<void> => {
  try {
    await api.delete(`/consultas/${id}/`);
  } catch (error) {
    console.error('Error deleting consulta:', error);
    throw error;
  }
};

// Archivos Médicos
export const getArchivosMedicos = async (): Promise<ArchivoMedico[]> => {
  try {
    const response = await api.get('/archivos-medicos/archivos/');
    return response.data.results || response.data;
  } catch {
    throw new Error('No se pudieron cargar los archivos médicos.');
  }
};

export const getArchivosPorPaciente = async (pacienteId: number): Promise<ArchivoMedico[]> => {
  try {
    // Usar parámetro paciente_id para compatibilidad
    const response = await api.get(`/archivos-medicos/archivos/`, {
      params: { paciente_id: pacienteId }
    });
    return response.data.results || response.data || [];
  } catch {
    throw new Error('No se pudieron cargar los archivos del paciente.');
  }
};

export const getArchivosPorConsulta = async (consultaId: number): Promise<ArchivoMedico[]> => {
  try {
    const response = await api.get(`/archivos-medicos/archivos/`, {
      params: { consulta: consultaId },
    });
    return response.data.results || response.data || [];
  } catch {
    throw new Error('No se pudieron cargar los archivos de la consulta.');
  }
};

export const createArchivoMedico = async (archivoData: FormData | Partial<ArchivoMedico>): Promise<ArchivoMedico> => {
  try {
    const isForm = (typeof FormData !== 'undefined') && archivoData instanceof FormData;
    const response = await api.post('/archivos-medicos/archivos/', archivoData, {
      headers: isForm ? { 'Content-Type': 'multipart/form-data' } : { 'Content-Type': 'application/json' },
    });
    return response.data;
  } catch {
    throw new Error('No se pudo crear el archivo médico.');
  }
};

export const updateArchivoMedico = async (id: number, archivoData: FormData | Partial<ArchivoMedico>): Promise<ArchivoMedico> => {
  try {
    const isForm = (typeof FormData !== 'undefined') && archivoData instanceof FormData;
    const response = await api.patch(`/archivos-medicos/archivos/${id}/`, archivoData, {
      headers: isForm ? { 'Content-Type': 'multipart/form-data' } : undefined,
    });
    return response.data;
  } catch {
    throw new Error('No se pudo actualizar el archivo médico.');
  }
};

export const downloadArchivoMedico = async (id: number): Promise<Blob> => {
  try {
    const response = await api.get(`/archivos-medicos/archivos/${id}/download/`, {
      responseType: 'blob',
    });
    return response.data;
  } catch {
    throw new Error('No se pudo descargar el archivo médico.');
  }
};

export const getTiposArchivo = async (): Promise<{value: string, label: string}[]> => {
  try {
    const response = await api.get('/archivos-medicos/archivos/tipos_disponibles/');
    return response.data;
  } catch {
    throw new Error('No se pudieron cargar los tipos de archivo.');
  }
};

// Solicitudes
export const getSolicitudes = async (): Promise<Solicitud[]> => {
  try {
    const response = await api.get('/solicitudes/');
    return response.data.results || response.data;
  } catch (error) {
    console.error('Error fetching solicitudes:', error);
    throw error;
  }
};

export const getSolicitud = async (id: number): Promise<Solicitud> => {
  try {
    const response = await api.get(`/solicitudes/${id}/`);
    return response.data;
  } catch (error) {
    console.error('Error fetching solicitud:', error);
    throw error;
  }
};

export const createSolicitud = async (data: Partial<Solicitud>): Promise<Solicitud> => {
  try {
    const response = await api.post('/solicitudes/', data);
    return response.data;
  } catch (error) {
    console.error('Error creating solicitud:', error);
    throw error;
  }
};

export const updateSolicitud = async (id: number, data: Partial<Solicitud>): Promise<Solicitud> => {
  try {
    const response = await api.patch(`/solicitudes/${id}/`, data);
    return response.data;
  } catch (error) {
    console.error('Error updating solicitud:', error);
    throw error;
  }
};

export const deleteSolicitud = async (id: number): Promise<void> => {
  try {
    await api.delete(`/solicitudes/${id}/`);
  } catch (error) {
    console.error('Error deleting solicitud:', error);
    throw error;
  }
};

export const getSolicitudesPendientes = async (): Promise<Solicitud[]> => {
  try {
    const response = await api.get('/solicitudes/pendientes/');
    return response.data.results || response.data;
  } catch (error) {
    console.error('Error fetching solicitudes pendientes:', error);
    throw error;
  }
};

export const cambiarEstadoSolicitud = async (id: number, nuevoEstado: string): Promise<Solicitud> => {
  try {
    const response = await api.patch(`/solicitudes/${id}/cambiar_estado/`, {
      estado: nuevoEstado
    });
    return response.data;
  } catch (error) {
    console.error('Error changing solicitud state:', error);
    throw error;
  }
};

export const marcarSolicitudCompletada = async (id: number): Promise<Solicitud> => {
  try {
    const response = await api.post(`/solicitudes/${id}/marcar_como_completada/`);
    return response.data;
  } catch (error) {
    console.error('Error marking solicitud as completed:', error);
    throw error;
  }
};

export const cancelarSolicitud = async (id: number): Promise<Solicitud> => {
  try {
    const response = await api.post(`/solicitudes/${id}/cancelar/`);
    return response.data;
  } catch (error) {
    console.error('Error canceling solicitud:', error);
    throw error;
  }
};

export const reabrirSolicitud = async (id: number): Promise<Solicitud> => {
  try {
    const response = await api.post(`/solicitudes/${id}/reabrir/`);
    return response.data;
  } catch (error) {
    console.error('Error reopening solicitud:', error);
    throw error;
  }
};

export const enviarSolicitudALims = async (id: number, data: { paneles?: (number|string)[]; tipos_examen?: (number|string)[] }): Promise<{ lims_id: string }> => {
  try {
    const response = await api.post(`/solicitudes/${id}/enviar_lims/`, data);
    return response.data;
  } catch (error) {
    console.error('Error enviando solicitud al LIMS:', error);
    throw error;
  }
};

export const getSolicitudesEstadisticas = async (): Promise<any> => {
  try {
    const response = await api.get('/solicitudes/estadisticas/');
    return response.data;
  } catch (error) {
    console.error('Error fetching solicitudes statistics:', error);
    throw error;
  }
};

export const getSolicitudesVencidas = async (): Promise<Solicitud[]> => {
  try {
    const response = await api.get('/solicitudes/vencidas/');
    return response.data.results || response.data;
  } catch (error) {
    console.error('Error fetching solicitudes vencidas:', error);
    throw error;
  }
};

export const getSolicitudesProximasVencer = async (): Promise<Solicitud[]> => {
  try {
    const response = await api.get('/solicitudes/proximas_vencer/');
    return response.data.results || response.data;
  } catch (error) {
    console.error('Error fetching solicitudes próximas a vencer:', error);
    throw error;
  }
};

// Médicos - CRUD (solo admin)
export const getMedico = async (id: number): Promise<Medico> => {
  try {
    const response = await api.get(`/medicos/${id}/`);
    return response.data;
  } catch (error) {
    console.error('Error fetching medico:', error);
    throw error;
  }
};

export const createMedico = async (medicoData: Partial<Medico>): Promise<Medico> => {
  try {
    const response = await api.post('/medicos/', medicoData);
    return response.data;
  } catch (error) {
    console.error('Error creating medico:', error);
    throw error;
  }
};

export const updateMedico = async (id: number, medicoData: Partial<Medico>): Promise<Medico> => {
  try {
    const response = await api.patch(`/medicos/${id}/`, medicoData);
    return response.data;
  } catch (error) {
    console.error('Error updating medico:', error);
    throw error;
  }
};

export const deleteMedico = async (id: number): Promise<void> => {
  try {
    await api.delete(`/medicos/${id}/`);
  } catch (error) {
    console.error('Error deleting medico:', error);
    throw error;
  }
};

// Diagnósticos CIE-10 - CRUD (médicos y admin) - SIEMPRE obtener TODOS
export const getDiagnosticosCIE10 = async (): Promise<DiagnosticoCIE10[]> => {
  try {
    const response = await api.get('/diagnosticos-cie10/');
    // Si hay paginación, obtener todas las páginas
    if (response.data.results) {
      let allItems = [...response.data.results];
      let nextUrl = response.data.next;
      while (nextUrl) {
        const nextResponse = await api.get(normalizeUrl(nextUrl));
        allItems = [...allItems, ...nextResponse.data.results];
        nextUrl = nextResponse.data.next;
      }
      return allItems;
    }
    return Array.isArray(response.data) ? response.data : [];
  } catch (error) {
    console.error('Error fetching diagnosticos CIE-10:', error);
    throw error;
  }
};

// Búsqueda de diagnósticos CIE-10
export const buscarDiagnosticosCIE10 = async (query: string): Promise<DiagnosticoCIE10[]> => {
  if (!query || query.trim().length < 2) {
    return [];
  }
  try {
    const trimmedQuery = query.trim();
    console.log(`🔍 Buscando diagnósticos CIE-10: "${trimmedQuery}"`);
    
    const response = await api.get('/diagnosticos-cie10/buscar/', {
      params: { q: trimmedQuery },
    });
    
    const data = response.data as any;
    let results: DiagnosticoCIE10[] = [];
    
    if (Array.isArray(data)) {
      results = data;
    } else if (Array.isArray(data?.results)) {
      results = data.results;
    } else {
      console.warn('⚠️ Formato de respuesta inesperado:', data);
      return [];
    }
    
    console.log(`✅ Respuesta recibida: ${results.length} diagnósticos`);
    return results;
  } catch (error: unknown) {
    const err = error as { response?: { status?: number; data?: unknown } };
    console.error('❌ Error buscando diagnósticos CIE-10:', error);
    if (err?.response) {
      console.error('   Status:', err.response.status);
      console.error('   Data:', err.response.data);
    }
    throw error; // Re-lanzar para que el componente maneje el error
  }
};

export const createDiagnosticoCIE10 = async (data: Partial<DiagnosticoCIE10>): Promise<DiagnosticoCIE10> => {
  try {
    const response = await api.post('/diagnosticos-cie10/', data);
    return response.data;
  } catch (error) {
    console.error('Error creating diagnostico CIE-10:', error);
    throw error;
  }
};

export const updateDiagnosticoCIE10 = async (id: number, data: Partial<DiagnosticoCIE10>): Promise<DiagnosticoCIE10> => {
  try {
    const response = await api.patch(`/diagnosticos-cie10/${id}/`, data);
    return response.data;
  } catch (error) {
    console.error('Error updating diagnostico CIE-10:', error);
    throw error;
  }
};

export const deleteDiagnosticoCIE10 = async (id: number): Promise<void> => {
  try {
    await api.delete(`/diagnosticos-cie10/${id}/`);
  } catch (error) {
    console.error('Error deleting diagnostico CIE-10:', error);
    throw error;
  }
};

// Estudios Diagnósticos - CRUD (médicos y admin) - SIEMPRE obtener TODOS
export const getEstudiosDiagnostico = async (): Promise<EstudioDiagnostico[]> => {
  try {
    const response = await api.get('/estudios-diagnosticos/');
    // Si hay paginación, obtener todas las páginas
    if (response.data.results) {
      let allItems = [...response.data.results];
      let nextUrl = response.data.next;
      while (nextUrl) {
        const nextResponse = await api.get(normalizeUrl(nextUrl));
        allItems = [...allItems, ...nextResponse.data.results];
        nextUrl = nextResponse.data.next;
      }
      return allItems;
    }
    return Array.isArray(response.data) ? response.data : [];
  } catch (error) {
    console.error('Error fetching estudios diagnostico:', error);
    throw error;
  }
};

export const createEstudioDiagnostico = async (data: Partial<EstudioDiagnostico>): Promise<EstudioDiagnostico> => {
  try {
    const response = await api.post('/estudios-diagnosticos/', data);
    return response.data;
  } catch (error) {
    console.error('Error creating estudio diagnostico:', error);
    throw error;
  }
};

export const updateEstudioDiagnostico = async (id: number, data: Partial<EstudioDiagnostico>): Promise<EstudioDiagnostico> => {
  try {
    const response = await api.patch(`/estudios-diagnosticos/${id}/`, data);
    return response.data;
  } catch (error) {
    console.error('Error updating estudio diagnostico:', error);
    throw error;
  }
};

export const deleteEstudioDiagnostico = async (id: number): Promise<void> => {
  try {
    await api.delete(`/estudios-diagnosticos/${id}/`);
  } catch (error) {
    console.error('Error deleting estudio diagnostico:', error);
    throw error;
  }
};

// Procedimientos Catálogo - CRUD (médicos y admin) - SIEMPRE obtener TODOS
export const getProcedimientosCatalogo = async (): Promise<ProcedimientoCatalogo[]> => {
  try {
    const response = await api.get('/procedimientos-catalogo/');
    // Si hay paginación, obtener todas las páginas
    if (response.data.results) {
      let allItems = [...response.data.results];
      let nextUrl = response.data.next;
      while (nextUrl) {
        const nextResponse = await api.get(normalizeUrl(nextUrl));
        allItems = [...allItems, ...nextResponse.data.results];
        nextUrl = nextResponse.data.next;
      }
      return allItems;
    }
    return Array.isArray(response.data) ? response.data : [];
  } catch (error) {
    console.error('Error fetching procedimientos catalogo:', error);
    throw error;
  }
};

export const createProcedimientoCatalogo = async (data: Partial<ProcedimientoCatalogo>): Promise<ProcedimientoCatalogo> => {
  try {
    const response = await api.post('/procedimientos-catalogo/', data);
    return response.data;
  } catch (error) {
    console.error('Error creating procedimiento catalogo:', error);
    throw error;
  }
};

export const updateProcedimientoCatalogo = async (id: number, data: Partial<ProcedimientoCatalogo>): Promise<ProcedimientoCatalogo> => {
  try {
    const response = await api.patch(`/procedimientos-catalogo/${id}/`, data);
    return response.data;
  } catch (error) {
    console.error('Error updating procedimiento catalogo:', error);
    throw error;
  }
};

export const deleteProcedimientoCatalogo = async (id: number): Promise<void> => {
  try {
    await api.delete(`/procedimientos-catalogo/${id}/`);
  } catch (error) {
    console.error('Error deleting procedimiento catalogo:', error);
    throw error;
  }
};

// Medicamentos - CRUD (médicos y admin) - SIEMPRE obtener TODOS
export const getMedicamentos = async (): Promise<Medicamento[]> => {
  try {
    const response = await api.get('/medicamentos/');
    // Si hay paginación, obtener todas las páginas
    if (response.data.results) {
      let allItems = [...response.data.results];
      let nextUrl = response.data.next;
      while (nextUrl) {
        const nextResponse = await api.get(normalizeUrl(nextUrl));
        allItems = [...allItems, ...nextResponse.data.results];
        nextUrl = nextResponse.data.next;
      }
      return allItems;
    }
    return Array.isArray(response.data) ? response.data : [];
  } catch (error) {
    console.error('Error fetching medicamentos:', error);
    throw error;
  }
};

export const createMedicamento = async (data: Partial<Medicamento>): Promise<Medicamento> => {
  try {
    const response = await api.post('/medicamentos/', data);
    return response.data;
  } catch (error) {
    console.error('Error creating medicamento:', error);
    throw error;
  }
};

export const updateMedicamento = async (id: number, data: Partial<Medicamento>): Promise<Medicamento> => {
  try {
    const response = await api.patch(`/medicamentos/${id}/`, data);
    return response.data;
  } catch (error) {
    console.error('Error updating medicamento:', error);
    throw error;
  }
};

export const deleteMedicamento = async (id: number): Promise<void> => {
  try {
    await api.delete(`/medicamentos/${id}/`);
  } catch (error) {
    console.error('Error deleting medicamento:', error);
    throw error;
  }
};

// Especialidades - CRUD (médicos y admin) - SIEMPRE obtener TODAS
export const getEspecialidades = async (): Promise<Especialidad[]> => {
  try {
    const response = await api.get('/especialidades/');
    // Si hay paginación, obtener todas las páginas
    if (response.data.results) {
      let allItems = [...response.data.results];
      let nextUrl = response.data.next;
      while (nextUrl) {
        const nextResponse = await api.get(normalizeUrl(nextUrl));
        allItems = [...allItems, ...nextResponse.data.results];
        nextUrl = nextResponse.data.next;
      }
      return allItems;
    }
    return Array.isArray(response.data) ? response.data : [];
  } catch (error) {
    console.error('Error fetching especialidades:', error);
    throw error;
  }
};

export const createEspecialidad = async (data: Partial<Especialidad>): Promise<Especialidad> => {
  try {
    const response = await api.post('/especialidades/', data);
    return response.data;
  } catch (error) {
    console.error('Error creating especialidad:', error);
    throw error;
  }
};

export const updateEspecialidad = async (id: number, data: Partial<Especialidad>): Promise<Especialidad> => {
  try {
    const response = await api.patch(`/especialidades/${id}/`, data);
    return response.data;
  } catch (error) {
    console.error('Error updating especialidad:', error);
    throw error;
  }
};

export const deleteEspecialidad = async (id: number): Promise<void> => {
  try {
    await api.delete(`/especialidades/${id}/`);
  } catch (error) {
    console.error('Error deleting especialidad:', error);
    throw error;
  }
};

// Internación - Gestión de Camas
export const getCamas = async (sector?: string): Promise<Cama[]> => {
  try {
    const url = sector 
      ? `/internacion/camas/?sector=${sector}`
      : '/internacion/camas/';
    const response = await api.get(url);
    return response.data.results || response.data;
  } catch (error) {
    console.error('Error fetching camas:', error);
    throw error;
  }
};

export const getCama = async (id: number): Promise<Cama> => {
  try {
    const response = await api.get(`/internacion/camas/${id}/`);
    return response.data;
  } catch (error) {
    console.error('Error fetching cama:', error);
    throw error;
  }
};

export const getSectores = async (): Promise<Sector[]> => {
  try {
    const response = await api.get('/internacion/sectores/');
    return response.data.results || response.data;
  } catch (error) {
    console.error('Error fetching sectores:', error);
    throw error;
  }
};

export const createInternacion = async (data: {
  paciente: number;
  cama: number;
  medico: number | null;
  diagnostico_cie_id?: number | null;
  diagnostico_ingreso?: string;
}): Promise<InternacionCama> => {
  try {
    const response = await api.post('/internacion/internaciones/ingresar/', data);
    return response.data;
  } catch (error) {
    console.error('Error creating internacion:', error);
    throw error;
  }
};

export const darAltaInternacion = async (id: number, fecha_alta?: string): Promise<InternacionCama> => {
  try {
    const response = await api.post(`/internacion/internaciones/${id}/alta/`, {
      fecha_alta: fecha_alta || null
    });
    return response.data;
  } catch (error) {
    console.error('Error dando alta a internacion:', error);
    throw error;
  }
};

export const getInternaciones = async (): Promise<InternacionCama[]> => {
  try {
    const response = await api.get('/internacion/internaciones/');
    return response.data.results || response.data;
  } catch (error) {
    console.error('Error fetching internaciones:', error);
    throw error;
  }
};

export const updateInternacion = async (id: number, data: Partial<InternacionCama>): Promise<InternacionCama> => {
  try {
    console.log('API: Actualizando internación', id, 'con datos:', data);
    const response = await api.patch(`/internacion/internaciones/${id}/`, data);
    console.log('API: Respuesta recibida:', response.data);
    console.log('API: Status:', response.status);
    return response.data;
  } catch (error: unknown) {
    const err = error as { response?: { data?: unknown; status?: number } };
    console.error('API: Error updating internacion:', error);
    console.error('API: Error response:', err?.response?.data);
    console.error('API: Error status:', err?.response?.status);
    throw error;
  }
};

export const moverPacienteCama = async (internacionId: number, camaDestinoId: number): Promise<{ message?: string; mensaje?: string }> => {
  try {
    const response = await api.post(`/internacion/internaciones/${internacionId}/mover-cama/`, {
      cama_id: camaDestinoId,
    });
    return response.data;
  } catch (error: unknown) {
    console.error('Error moving paciente to cama:', error);
    throw error;
  }
};

export const updateCama = async (id: number, data: Partial<Cama>): Promise<Cama> => {
  try {
    const response = await api.patch(`/internacion/camas/${id}/`, data);
    return response.data;
  } catch (error: unknown) {
    console.error('Error updating cama:', error);
    throw error;
  }
};

// Laboratorio - Tipos de Examen
// Documentos - Tipos de documento
export const getTiposDocumento = async (): Promise<Array<{ value: string; label: string }>> => {
  try {
    const response = await api.get('/documentos/tipos/');
    return response.data;
  } catch (error) {
    console.error('Error fetching tipos de documento:', error);
    throw error;
  }
};

export const getTiposExamen = async (): Promise<TipoExamen[]> => {
  try {
    console.log('🌐🌐🌐 getTiposExamen: Iniciando llamada HTTP 🌐🌐🌐');
    console.log('📡 URL:', '/laboratorio/tipos-examen/');
    console.log('📡 Base URL completa:', 'http://localhost:8000/api/laboratorio/tipos-examen/');
    
    const response = await api.get('/laboratorio/tipos-examen/');
    
    console.log('✅✅✅ getTiposExamen: Respuesta recibida ✅✅✅');
    console.log('📦 Status:', response.status);
    console.log('📦 Data type:', typeof response.data);
    console.log('📦 Has results?', !!response.data?.results);
    console.log('📦 Is array?', Array.isArray(response.data));
    console.log('📦 Response data keys:', Object.keys(response.data || {}));
    
    // Si hay paginación, obtener todas las páginas
    if (response.data.results) {
      console.log('📄 Respuesta paginada detectada');
      console.log('📄 Total en primera página:', response.data.results.length);
      console.log('📄 Total count:', response.data.count);
      console.log('📄 Next URL:', response.data.next);
      
      let allItems = [...response.data.results];
      let nextUrl = response.data.next;
      let pageCount = 1;
      
      while (nextUrl) {
        pageCount++;
        console.log(`📄 Obteniendo página ${pageCount}...`);
        console.log(`📄 Next URL original: ${nextUrl}`);
        
        // Normalizar la URL para evitar duplicar /api/
        const relativeUrl = normalizeUrl(nextUrl);
        
        console.log(`📄 URL relativa procesada: ${relativeUrl}`);
        const nextResponse = await api.get(relativeUrl);
        allItems = [...allItems, ...nextResponse.data.results];
        nextUrl = nextResponse.data.next;
      }
      
      console.log(`✅ Total de páginas obtenidas: ${pageCount}`);
      console.log(`✅ Total de items: ${allItems.length}`);
      return allItems;
    }
    
    const result = Array.isArray(response.data) ? response.data : [];
    console.log('✅ Items retornados (sin paginación):', result.length);
    return result;
  } catch (error: unknown) {
    const err = error as { message?: string; response?: { status?: number; data?: unknown } };
    console.error('❌❌❌ ERROR en getTiposExamen ❌❌❌');
    console.error('❌ Error message:', err?.message);
    console.error('❌ Error response:', err?.response);
    console.error('❌ Error status:', err?.response?.status);
    console.error('❌ Error data:', err?.response?.data);
    throw error;
  }
};
