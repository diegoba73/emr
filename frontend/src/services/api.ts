import { AxiosInstance, AxiosResponse } from 'axios';
import {
  Paciente,
  Medico,
  Turno,
  Consulta,
  SolicitudExamen,
  ResultadoExamen,
  DashboardStats,
  ApiResponse,
  User,
  CentroFisico,
  TipoAtencion,
  AreaInternacion,
  CamaInternacion,
  Internacion,
  Atencion,
  CreateAtencionPayload,
  Documento,
  EstudioDiagnostico,
  ProcedimientoCatalogo,
  ConsultaAmbulatoriaRecord,
  EvolucionInternacionRecord,
  RegistroProcedimientoRecord,
  RegistroQuirurgicoRecord,
  TipoExamen,
} from '../types';
import { fetchWithCSRF } from '../utils/csrf';
import { apiClient } from './apiClient';

/** Mensaje legible desde el JSON de error de Django REST (400/403). */
function formatDrfErrorBody(data: unknown): string {
  if (data == null || typeof data !== 'object') {
    return '';
  }
  const o = data as Record<string, unknown>;
  if (typeof o.detail === 'string') {
    return o.detail;
  }
  if (typeof o.error === 'string') {
    return o.error;
  }
  const parts: string[] = [];
  for (const [k, v] of Object.entries(o)) {
    if (Array.isArray(v)) {
      parts.push(`${k}: ${v.map(String).join(' ')}`);
    } else if (typeof v === 'string') {
      parts.push(`${k}: ${v}`);
    } else {
      parts.push(`${k}: ${JSON.stringify(v)}`);
    }
  }
  return parts.join(' · ') || JSON.stringify(data);
}

class ApiService {
  private api: AxiosInstance = apiClient;

  // Autenticación
  async getCurrentUser(): Promise<User> {
    const response: AxiosResponse<User> = await this.api.get('/auth/current-user/');
    return response.data;
  }

  async login(username: string, password: string): Promise<{ user: User; message: string }> {
    try {
      const response = await fetchWithCSRF(`${this.api.defaults.baseURL}/auth/login/`, {
        method: 'POST',
        body: JSON.stringify({
          username,
          password
        }),
      });
      
      if (!response.ok) {
        // Intentar parsear el error del servidor
        let errorData: Record<string, unknown> = {};
        try {
          const contentType = response.headers.get('content-type');
          if (contentType && contentType.includes('application/json')) {
            errorData = await response.json();
          } else {
            const text = await response.text();
            errorData = { error: text || `HTTP ${response.status}: ${response.statusText}` };
          }
        } catch (parseError) {
          errorData = { error: `HTTP ${response.status}: ${response.statusText}` };
        }
        
        const errorMsg = (errorData.error || errorData.detail || `HTTP ${response.status}: ${response.statusText}`) as string;
        const error = new Error(errorMsg) as Error & { response?: { status: number; statusText: string; data: Record<string, unknown> } };
        error.response = {
          status: response.status,
          statusText: response.statusText,
          data: errorData,
        };
        throw error;
      }
      
      return response.json();
    } catch (error: unknown) {
      const err = error as { isConnectionError?: boolean };
      // Si es un error de conexión, re-lanzarlo con el mensaje mejorado
      if (err?.isConnectionError) {
        throw error;
      }
      // Para otros errores, re-lanzar tal cual
      throw error;
    }
  }

  async logout(): Promise<void> {
    const response = await fetchWithCSRF(`${this.api.defaults.baseURL}/auth/logout/`, {
      method: 'POST',
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
  }

  async registerPaciente(data: {
    email: string;
    password: string;
    nombre: string;
    apellido: string;
    dni: string;
    telefono: string;
    fecha_nacimiento: string;
  }): Promise<{ message: string; user_id: number; email: string }> {
    try {
      const response = await fetchWithCSRF(`${this.api.defaults.baseURL}/auth/register/`, {
        method: 'POST',
        body: JSON.stringify(data),
      });
      
      if (!response.ok) {
        // Intentar parsear el error del servidor
        let errorData: Record<string, unknown> = {};
        try {
          const contentType = response.headers.get('content-type');
          if (contentType && contentType.includes('application/json')) {
            errorData = await response.json();
          } else {
            const text = await response.text();
            errorData = { error: text || `HTTP ${response.status}: ${response.statusText}` };
          }
        } catch (parseError) {
          // Si falla el parsing, usar un error genérico
          errorData = { 
            error: `Error ${response.status}: ${response.statusText}` 
          };
        }
        
        // Crear un error estructurado para el componente
        const errorMsg = (errorData.error || errorData.message || `Error ${response.status}: ${response.statusText}`) as string;
        const error = new Error(errorMsg) as Error & { details?: Record<string, unknown>; response?: { status: number; statusText: string; data: Record<string, unknown> } };
        
        // Agregar detalles si existen
        if (errorData.details) {
          error.details = errorData.details as Record<string, unknown>;
        } else if (errorData && Object.keys(errorData).length > 0) {
          error.details = errorData;
        }
        
        // Agregar información de la respuesta para debugging
        error.response = {
          status: response.status,
          statusText: response.statusText,
          data: errorData,
        };
        
        throw error;
      }
      
      // Si la respuesta es exitosa, parsear y retornar
      return await response.json();
    } catch (error: unknown) {
      const err = error as { response?: unknown; details?: unknown };
      // Si ya es un Error que lanzamos arriba, re-lanzarlo
      if (err?.response || err?.details) {
        throw error;
      }
      
      // Si es un error de red u otro tipo, envolverlo
      const origErr = error as Error;
      const wrappedError = new Error(
        origErr?.message || 'Error de conexión. Verifique su conexión a internet.'
      ) as Error & { originalError?: unknown; request?: boolean };
      wrappedError.originalError = error;
      wrappedError.request = true; // Indicar que es un error de request
      throw wrappedError;
    }
  }

  /**
   * Gestión de usuarios (admin) vía ``/api/usuarios/users/`` (sesión + CSRF vía ``apiClient``).
   * No usa DELETE: baja operativa con ``deactivate`` / ``activate``.
   */
  async listUsersForManagement(): Promise<User[]> {
    const collected: User[] = [];
    let nextUrl: string | null = '/usuarios/users/';
    while (nextUrl) {
      const response: AxiosResponse<User[] | { results?: User[]; next?: string | null }> =
        await this.api.get(nextUrl);
      const data = response.data;
      if (Array.isArray(data)) {
        return data;
      }
      if (data && typeof data === 'object' && Array.isArray(data.results)) {
        collected.push(...data.results);
        const next = data.next;
        if (typeof next === 'string' && next) {
          if (next.startsWith('http')) {
            nextUrl = next;
          } else {
            const base = this.api.defaults.baseURL || '';
            const origin = base.startsWith('http') ? new URL(base).origin : window.location.origin;
            nextUrl = new URL(next, origin).toString();
          }
        } else {
          nextUrl = null;
        }
      } else {
        break;
      }
    }
    return collected;
  }

  async createUserManagement(payload: Record<string, unknown>): Promise<User> {
    const response: AxiosResponse<User> = await this.api.post('/usuarios/users/', payload);
    return response.data;
  }

  async updateUserManagement(id: number, payload: Record<string, unknown>): Promise<User> {
    const response: AxiosResponse<User> = await this.api.put(`/usuarios/users/${id}/`, payload);
    return response.data;
  }

  async activateUserManagement(id: number): Promise<void> {
    await this.api.post(`/usuarios/users/${id}/activate/`);
  }

  async deactivateUserManagement(id: number): Promise<void> {
    await this.api.post(`/usuarios/users/${id}/deactivate/`);
  }

  // Panel
  async getDashboardStats(): Promise<DashboardStats> {
    const response: AxiosResponse<DashboardStats> = await this.api.get('/dashboard/estadisticas/');
    return response.data;
  }

  // Pacientes
  async getPacientes(params?: {
    page?: number;
    page_size?: number;
    search?: string;
  }): Promise<ApiResponse<Paciente>> {
    const response: AxiosResponse<ApiResponse<Paciente>> = await this.api.get('/pacientes/', {
      params: {
        page: params?.page,
        page_size: params?.page_size,
        search: params?.search?.trim() || undefined,
      },
    });
    return response.data;
  }

  async getPaciente(id: number): Promise<Paciente> {
    const response: AxiosResponse<Paciente> = await this.api.get(`/pacientes/${id}/`);
    return response.data;
  }

  async createPaciente(paciente: Partial<Paciente>): Promise<Paciente> {
    const response = await fetchWithCSRF(`${this.api.defaults.baseURL}/pacientes/`, {
      method: 'POST',
      body: JSON.stringify(paciente),
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    return response.json();
  }

  async updatePaciente(id: number, paciente: Partial<Paciente>): Promise<Paciente> {
    const response = await fetchWithCSRF(`${this.api.defaults.baseURL}/pacientes/${id}/`, {
      method: 'PUT',
      body: JSON.stringify(paciente),
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    return response.json();
  }

  async deletePaciente(id: number): Promise<void> {
    const response = await fetchWithCSRF(`${this.api.defaults.baseURL}/pacientes/${id}/`, {
      method: 'DELETE',
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
  }



  async buscarPacientes(query: string): Promise<Paciente[]> {
    if (!query || query.trim().length < 2) {
      return [];
    }
    try {
      const response = await this.api.get('/pacientes/buscar/', {
        params: { q: query.trim() },
      });
      const data = response.data as Paciente[] | { results?: Paciente[] };
      if (Array.isArray(data)) {
        return data;
      }
      return Array.isArray(data?.results) ? data.results : [];
    } catch {
      const fallback = await this.api.get('/pacientes/', {
        params: { search: query.trim() },
      });
      const data = fallback.data as Paciente[] | { results?: Paciente[] };
      if (Array.isArray(data)) {
        return data;
      }
      return Array.isArray(data?.results) ? data.results : [];
    }
  }

  // Médicos
  async getMedicos(): Promise<ApiResponse<Medico>> {
    const response: AxiosResponse<ApiResponse<Medico>> = await this.api.get('/medicos/');
    return response.data;
  }

  async getMedico(id: number): Promise<Medico> {
    const response: AxiosResponse<Medico> = await this.api.get(`/medicos/${id}/`);
    return response.data;
  }

  async buscarMedicos(query: string): Promise<Medico[]> {
    if (!query || query.trim().length < 2) {
      return [];
    }
    try {
      // DRF SearchFilter usa el parámetro 'search', no 'q'
      const response = await this.api.get('/medicos/', {
        params: { search: query.trim() },
      });
      const data = response.data as any;
      if (Array.isArray(data)) {
        return data;
      }
      return Array.isArray(data?.results) ? data.results : [];
    } catch {
      console.error('Error buscando médicos.');
      return [];
    }
  }

  // Especialidades
  async getEspecialidades(): Promise<ApiResponse<any>> {
    const response: AxiosResponse<ApiResponse<any>> = await this.api.get('/especialidades/');
    return response.data;
  }

  // Turnos
  async getTurnos(): Promise<ApiResponse<Turno>> {
    const response: AxiosResponse<ApiResponse<Turno>> = await this.api.get('/turnos/');
    return response.data;
  }

  async getTurno(id: number): Promise<Turno> {
    const response: AxiosResponse<Turno> = await this.api.get(`/turnos/${id}/`);
    return response.data;
  }

  async createTurno(turno: Partial<Turno>): Promise<Turno> {
    const response = await fetchWithCSRF(`${this.api.defaults.baseURL}/turnos/`, {
      method: 'POST',
      body: JSON.stringify(turno),
    });
    
    if (!response.ok) {
      const text = await response.text();
      let msg = '';
      try {
        msg = formatDrfErrorBody(JSON.parse(text) as unknown);
      } catch {
        msg = text;
      }
      throw new Error(msg || `HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  async updateTurno(id: number, turno: Partial<Turno>): Promise<Turno> {
    // Filtrar campos undefined antes de enviar
    const cleanTurno = Object.fromEntries(
      Object.entries(turno).filter(([_, value]) => value !== undefined)
    );
    
    const response = await fetchWithCSRF(`${this.api.defaults.baseURL}/turnos/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(cleanTurno),
    });
    
    if (!response.ok) {
      const text = await response.text();
      let msg = '';
      try {
        msg = formatDrfErrorBody(JSON.parse(text) as unknown);
      } catch {
        msg = text;
      }
      throw new Error(msg || `HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  async deleteTurno(id: number): Promise<void> {
    const response = await fetchWithCSRF(`${this.api.defaults.baseURL}/turnos/${id}/`, {
      method: 'DELETE',
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
  }

  async getTurnosDisponibles(fecha?: string): Promise<Turno[]> {
    const params = fecha ? `?fecha=${fecha}` : '';
    const response: AxiosResponse<Turno[]> = await this.api.get(`/turnos/disponibles/${params}`);
    return response.data;
  }

  async reservarTurno(id: number, pacienteId: number): Promise<Turno> {
    const response = await fetchWithCSRF(`${this.api.defaults.baseURL}/turnos/${id}/reservar/`, {
      method: 'POST',
      body: JSON.stringify({
        paciente_id: pacienteId
      }),
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    return response.json();
  }

  async getTurnosPorFecha(fecha: string): Promise<Turno[]> {
    const response: AxiosResponse<Turno[]> = await this.api.get(`/turnos/por_fecha/?fecha=${fecha}`);
    return response.data;
  }

  // Atenciones clíncias
  async getAtenciones(params?: Record<string, any>): Promise<ApiResponse<Atencion>> {
    const response: AxiosResponse<ApiResponse<Atencion>> = await this.api.get('/atenciones/', {
      params,
    });
    return response.data;
  }

  async getAtencion(id: number): Promise<Atencion> {
    try {
      const response: AxiosResponse<Atencion> = await this.api.get(`/atenciones/${id}/`);
      const data = response.data;
      
      // Normalizar documentos para asegurar consistencia
      if (data && typeof data === 'object') {
        if (!Array.isArray(data.documentos)) {
          data.documentos = (data.documentos as { results?: Documento[] })?.results || [];
        }
      }
      
      return data;
    } catch (error: unknown) {
      const err = error as { response?: { data?: { error?: string; detail?: string } }; message?: string };
      const errorMessage = err?.response?.data?.error || 
                          err?.response?.data?.detail || 
                          err?.message || 
                          'Error al obtener la atención';
      throw new Error(errorMessage);
    }
  }

  /** C5.10.1: flujo clínico real desde turno (REALIZADO + atención idempotente). */
  async iniciarAtencionTurno(turnoId: number): Promise<{
    atencion: Atencion;
    created_new: boolean;
    turno_estado: string;
    message: string;
  }> {
    try {
      const response = await this.api.post<{
        atencion: Atencion;
        created_new: boolean;
        turno_estado: string;
        message: string;
      }>(`/turnos/${turnoId}/iniciar-atencion/`, {});
      return response.data;
    } catch (error: unknown) {
      const err = error as { response?: { data?: { error?: string; detail?: string } }; message?: string };
      const errorMessage =
        err?.response?.data?.detail ||
        err?.response?.data?.error ||
        err?.message ||
        'Error al iniciar la atención';
      throw new Error(errorMessage);
    }
  }

  /**
   * @deprecated Compatibilidad técnica: no usar para iniciar atención desde agenda.
   * El backend no mueve el turno a REALIZADO. Usar {@link iniciarAtencionTurno}.
   */
  async createAtencion(data: CreateAtencionPayload): Promise<Atencion> {
    try {
      // Compat POST /api/atenciones/ — integraciones legacy; agenda usa iniciar-atencion.
      const payload = {
        turno: data.turno,
        ...(data.observaciones_generales && { observaciones_generales: data.observaciones_generales }),
      };

      const response: AxiosResponse<Atencion> = await this.api.post('/atenciones/', payload);
      return response.data;
    } catch (error: unknown) {
      const err = error as { response?: { data?: { error?: string; detail?: string }; status?: number }; message?: string };
      const errorMessage = err?.response?.data?.error || 
                          err?.response?.data?.detail || 
                          err?.message || 
                          'Error al crear la atención';
      throw new Error(errorMessage);
    }
  }

  async updateAtencion(id: number, payload: Partial<Atencion>): Promise<Atencion> {
    const response: AxiosResponse<Atencion> = await this.api.patch(`/atenciones/${id}/`, payload);
    return response.data;
  }

  /** Backend activo: AtencionViewSet.cerrar → POST /api/atenciones/{id}/cerrar/ */
  async closeAtencion(id: number): Promise<Atencion> {
    const response: AxiosResponse<Atencion> = await this.api.post(`/atenciones/${id}/cerrar/`);
    return response.data;
  }

  async iniciarAtencionGuardia(payload: {
    paciente_id: number;
    medico_id?: number;
    motivo_consulta?: string;
    turno_id?: number;
    observaciones_generales?: string;
  }): Promise<Atencion> {
    const response: AxiosResponse<Atencion> = await this.api.post('/atenciones/iniciar-guardia/', payload);
    return response.data;
  }

  async ensureConsultaHc(atencionId: number): Promise<number> {
    const response: AxiosResponse<{ consulta_hc_id: number }> = await this.api.post(
      `/atenciones/${atencionId}/ensure-consulta-hc/`
    );
    return response.data.consulta_hc_id;
  }

  // Documentos clínicos
  async getTiposDocumento(): Promise<Array<{ value: string; label: string }>> {
    const response: AxiosResponse<Array<{ value: string; label: string }>> = await this.api.get('/documentos/tipos/');
    return response.data;
  }

  async uploadDocumento(formData: FormData): Promise<Documento> {
    const response: AxiosResponse<Documento> = await this.api.post('/documentos/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  }

  async downloadDocumento(id: number): Promise<Blob> {
    const response = await this.api.get(`/documentos/${id}/download/`, {
      responseType: 'blob',
    });
    return response.data;
  }

  /** @deprecated C6.2: el backend responde 405; no usar desde UI. */
  async deleteDocumento(id: number): Promise<void> {
    await this.api.delete(`/documentos/${id}/`);
  }

  async getDocumentos(atencionId?: number): Promise<Documento[]> {
    const params = atencionId ? { atencion_id: atencionId } : {};
    const response: AxiosResponse<ApiResponse<Documento> | Documento[]> = await this.api.get('/documentos/', { params });
    if (Array.isArray(response.data)) {
      return response.data;
    }
    return response.data.results || [];
  }

  // Consulta ambulatoria
  async createConsultaAmbulatoria(atencionId: number, payload: Partial<ConsultaAmbulatoriaRecord>): Promise<ConsultaAmbulatoriaRecord> {
    const response: AxiosResponse<ConsultaAmbulatoriaRecord> = await this.api.post(`/atenciones/${atencionId}/crear_registro_ambulatorio/`, payload);
    return response.data;
  }

  async updateConsultaAmbulatoria(atencionId: number, payload: Partial<ConsultaAmbulatoriaRecord>, registroId?: number): Promise<ConsultaAmbulatoriaRecord> {
    // Si no se proporciona el ID del registro, obtenerlo de la atención
    let idToUse = registroId;
    if (!idToUse) {
      const atencion = await this.getAtencion(atencionId);
      if (atencion.consulta_ambulatoria?.id) {
        idToUse = atencion.consulta_ambulatoria.id;
      } else {
        throw new Error('No existe un registro de consulta ambulatoria para esta atención. Use createConsultaAmbulatoria para crear uno nuevo.');
      }
    }
    
    const response: AxiosResponse<ConsultaAmbulatoriaRecord> = await this.api.put(`/consultas-ambulatorias/${idToUse}/`, payload);
    return response.data;
  }

  async updateEvolucionInternacion(
    atencionId: number,
    payload: Partial<EvolucionInternacionRecord>,
    registroId?: number,
  ): Promise<EvolucionInternacionRecord> {
    let idToUse = registroId;
    if (!idToUse) {
      const atencion = await this.getAtencion(atencionId);
      if (atencion.evolucion_internacion?.id) {
        idToUse = atencion.evolucion_internacion.id;
      } else {
        throw new Error('No existe evolución de internación para esta atención.');
      }
    }
    const response: AxiosResponse<EvolucionInternacionRecord> = await this.api.patch(
      `/evoluciones-internacion/${idToUse}/`,
      payload,
    );
    return response.data;
  }

  // Procedimientos / estudios
  async createRegistroProcedimiento(atencionId: number, formData: FormData): Promise<RegistroProcedimientoRecord> {
    const response: AxiosResponse<RegistroProcedimientoRecord> = await this.api.post(
      `/atenciones/${atencionId}/crear_registro_procedimiento/`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return response.data;
  }

  async updateRegistroProcedimiento(atencionId: number, formData: FormData, registroId?: number): Promise<RegistroProcedimientoRecord> {
    // Si no se proporciona el ID del registro, obtenerlo de la atención
    let idToUse = registroId;
    if (!idToUse) {
      const atencion = await this.getAtencion(atencionId);
      if (atencion.registro_procedimiento?.id) {
        idToUse = atencion.registro_procedimiento.id;
      } else {
        throw new Error('No existe un registro de procedimiento para esta atención. Use createRegistroProcedimiento para crear uno nuevo.');
      }
    }
    
    const response: AxiosResponse<RegistroProcedimientoRecord> = await this.api.put(
      `/registros-procedimientos/${idToUse}/`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return response.data;
  }

  // Cirugías
  async createRegistroQuirurgico(atencionId: number, formData: FormData): Promise<RegistroQuirurgicoRecord> {
    const response: AxiosResponse<RegistroQuirurgicoRecord> = await this.api.post(
      `/atenciones/${atencionId}/crear_registro_quirurgico/`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return response.data;
  }

  async updateRegistroQuirurgico(atencionId: number, formData: FormData, registroId?: number): Promise<RegistroQuirurgicoRecord> {
    // Si no se proporciona el ID del registro, obtenerlo de la atención
    let idToUse = registroId;
    if (!idToUse) {
      // Siempre intentar obtener el ID de la atención primero
      const atencion = await this.getAtencion(atencionId);
      if (atencion.registro_quirurgico?.id) {
        idToUse = atencion.registro_quirurgico.id;
      } else {
        // Si no existe en la atención, el registro no existe, no intentar actualizar
        throw new Error('No existe un registro quirúrgico para esta atención. Use createRegistroQuirurgico para crear uno nuevo.');
      }
    }
    
    const response: AxiosResponse<RegistroQuirurgicoRecord> = await this.api.put(
      `/registros-quirurgicos/${idToUse}/`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return response.data;
  }

  // Catálogos para formularios clínicos
  async getEstudiosDiagnostico(): Promise<EstudioDiagnostico[]> {
    const response: AxiosResponse<ApiResponse<EstudioDiagnostico>> = await this.api.get('/estudios-diagnosticos/');
    return response.data.results;
  }

  async getProcedimientosCatalogo(): Promise<ProcedimientoCatalogo[]> {
    const response: AxiosResponse<ApiResponse<ProcedimientoCatalogo>> = await this.api.get('/procedimientos-catalogo/');
    return response.data.results;
  }

  // Acciones específicas para médicos
  async confirmarTurno(id: number): Promise<{ turno: Turno; message: string }> {
    const response = await fetchWithCSRF(`${this.api.defaults.baseURL}/turnos/${id}/confirmar/`, {
      method: 'POST',
      body: JSON.stringify({}),
    });

    if (!response.ok) {
      const text = await response.text();
      let msg = '';
      try {
        msg = formatDrfErrorBody(JSON.parse(text) as unknown);
      } catch {
        msg = text;
      }
      throw new Error(msg || `HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    return { turno: data.turno as Turno, message: data.message || '' };
  }

  async cancelarTurno(id: number, motivo: string): Promise<{ turno: Turno; message: string }> {
    const response = await fetchWithCSRF(`${this.api.defaults.baseURL}/turnos/${id}/cancelar/`, {
      method: 'POST',
      body: JSON.stringify({ motivo }),
    });

    if (!response.ok) {
      const text = await response.text();
      let msg = '';
      try {
        msg = formatDrfErrorBody(JSON.parse(text) as unknown);
      } catch {
        msg = text;
      }
      throw new Error(msg || `HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    return { turno: data.turno as Turno, message: data.message || '' };
  }

  async reprogramarTurno(
    id: number,
    body: {
      fecha_hora_inicio: string;
      fecha_hora_fin: string;
      motivo: string;
      medico_id?: number;
      recurso_id?: number;
    },
  ): Promise<{ turno: Turno; message: string }> {
    const response = await fetchWithCSRF(`${this.api.defaults.baseURL}/turnos/${id}/reprogramar/`, {
      method: 'POST',
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      const text = await response.text();
      let msg = '';
      try {
        msg = formatDrfErrorBody(JSON.parse(text) as unknown);
      } catch {
        msg = text;
      }
      throw new Error(msg || `HTTP ${response.status}: ${response.statusText}`);
    }
    const data = await response.json();
    return { turno: data.turno as Turno, message: data.message || '' };
  }

  async marcarRealizadoTurno(
    id: number,
    motivo?: string,
  ): Promise<{ turno: Turno; message: string }> {
    const response = await fetchWithCSRF(
      `${this.api.defaults.baseURL}/turnos/${id}/marcar-realizado/`,
      {
        method: 'POST',
        body: JSON.stringify(motivo ? { motivo } : {}),
      },
    );
    if (!response.ok) {
      const text = await response.text();
      let msg = '';
      try {
        msg = formatDrfErrorBody(JSON.parse(text) as unknown);
      } catch {
        msg = text;
      }
      throw new Error(msg || `HTTP ${response.status}: ${response.statusText}`);
    }
    const data = await response.json();
    return { turno: data.turno as Turno, message: data.message || '' };
  }

  async marcarNoAsistioTurno(
    id: number,
    motivo: string,
  ): Promise<{ turno: Turno; message: string }> {
    const response = await fetchWithCSRF(
      `${this.api.defaults.baseURL}/turnos/${id}/marcar-no-asistio/`,
      {
        method: 'POST',
        body: JSON.stringify({ motivo }),
      },
    );
    if (!response.ok) {
      const text = await response.text();
      let msg = '';
      try {
        msg = formatDrfErrorBody(JSON.parse(text) as unknown);
      } catch {
        msg = text;
      }
      throw new Error(msg || `HTTP ${response.status}: ${response.statusText}`);
    }
    const data = await response.json();
    return { turno: data.turno as Turno, message: data.message || '' };
  }

  // Consultas
  async crearConsulta(turnoId: number, consultaData: Partial<Consulta>): Promise<Consulta> {
    const response = await fetchWithCSRF(`${this.api.defaults.baseURL}/turnos/${turnoId}/crear_consulta/`, {
      method: 'POST',
      body: JSON.stringify(consultaData),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
    }
    
    return response.json();
  }

  async getConsultaInfo(turnoId: number): Promise<Consulta | null> {
    try {
      const response: AxiosResponse<Consulta> = await this.api.get(`/turnos/${turnoId}/consulta_info/`);
      return response.data;
    } catch (error: unknown) {
      const err = error as { response?: { status?: number } };
      // Si es un 404, significa que no hay consulta (comportamiento esperado)
      if (err?.response?.status === 404) {
        return null;
      }
      // Para otros errores, relanzar
      throw error;
    }
  }

  async getConsultas(): Promise<ApiResponse<Consulta>> {
    const response: AxiosResponse<ApiResponse<Consulta>> = await this.api.get('/consultas/');
    return response.data;
  }

  // Laboratorio - Tipos de Examen
  async getTiposExamen(search?: string): Promise<ApiResponse<TipoExamen>> {
    let url = '/laboratorio/tipos-examen/';
    if (search) {
      url += `?search=${encodeURIComponent(search)}`;
    }
    const response: AxiosResponse<ApiResponse<TipoExamen>> = await this.api.get(url);
    return response.data;
  }

  async getTipoExamen(id: number): Promise<TipoExamen> {
    const response: AxiosResponse<TipoExamen> = await this.api.get(`/laboratorio/tipos-examen/${id}/`);
    return response.data;
  }

  // Laboratorio - Solicitudes de Examen
  async getSolicitudesExamen(): Promise<ApiResponse<SolicitudExamen>> {
    const response: AxiosResponse<ApiResponse<SolicitudExamen>> = await this.api.get('/solicitudes-examen/');
    return response.data;
  }

  async getSolicitudExamen(id: number): Promise<SolicitudExamen> {
    const response: AxiosResponse<SolicitudExamen> = await this.api.get(`/solicitudes-examen/${id}/`);
    return response.data;
  }

  async createSolicitudExamen(solicitud: Partial<SolicitudExamen>): Promise<SolicitudExamen> {
    const response: AxiosResponse<SolicitudExamen> = await this.api.post('/solicitudes-examen/', solicitud);
    return response.data;
  }

  async updateSolicitudExamen(id: number, solicitud: Partial<SolicitudExamen>): Promise<SolicitudExamen> {
    const response: AxiosResponse<SolicitudExamen> = await this.api.put(`/solicitudes-examen/${id}/`, solicitud);
    return response.data;
  }

  async deleteSolicitudExamen(id: number): Promise<void> {
    await this.api.delete(`/solicitudes-examen/${id}/`);
  }

  async cambiarEstadoSolicitud(id: number, estado: string): Promise<SolicitudExamen> {
    const response: AxiosResponse<SolicitudExamen> = await this.api.post(`/solicitudes-examen/${id}/cambiar_estado/`, {
      estado
    });
    return response.data;
  }

  async getEstadisticasSolicitudes(): Promise<any> {
    const response: AxiosResponse<any> = await this.api.get('/solicitudes-examen/estadisticas/');
    return response.data;
  }

  // Laboratorio - Resultados de Examen
  async getResultadosExamen(): Promise<ApiResponse<ResultadoExamen>> {
    const response: AxiosResponse<ApiResponse<ResultadoExamen>> = await this.api.get('/resultados-examen/');
    return response.data;
  }

  async getResultadoExamen(id: number): Promise<ResultadoExamen> {
    const response: AxiosResponse<ResultadoExamen> = await this.api.get(`/resultados-examen/${id}/`);
    return response.data;
  }

  async createResultadoExamen(resultado: Partial<ResultadoExamen>): Promise<ResultadoExamen> {
    const response: AxiosResponse<ResultadoExamen> = await this.api.post('/resultados-examen/', resultado);
    return response.data;
  }

  async updateResultadoExamen(id: number, resultado: Partial<ResultadoExamen>): Promise<ResultadoExamen> {
    const response: AxiosResponse<ResultadoExamen> = await this.api.put(`/resultados-examen/${id}/`, resultado);
    return response.data;
  }

  async deleteResultadoExamen(id: number): Promise<void> {
    await this.api.delete(`/resultados-examen/${id}/`);
  }

  async getResultadosPorSolicitud(solicitudId: number): Promise<ResultadoExamen[]> {
    const response: AxiosResponse<ResultadoExamen[]> = await this.api.get(`/resultados-examen/por_solicitud/?solicitud_id=${solicitudId}`);
    return response.data;
  }

  // NUEVO: Centros Físicos
  async getCentrosFisicos(): Promise<ApiResponse<CentroFisico>> {
    const response: AxiosResponse<ApiResponse<CentroFisico>> = await this.api.get('/catalogos/centros-fisicos/');
    return response.data;
  }

  async getCentroFisico(id: number): Promise<CentroFisico> {
    const response: AxiosResponse<CentroFisico> = await this.api.get(`/catalogos/centros-fisicos/${id}/`);
    return response.data;
  }

  // NUEVO: Tipos de Atención
  async getTiposAtencion(centroFisico?: string): Promise<ApiResponse<TipoAtencion>> {
    const url = centroFisico 
      ? `/catalogos/tipos-atencion/?centro_fisico=${centroFisico}`
      : '/catalogos/tipos-atencion/';
    const response: AxiosResponse<ApiResponse<TipoAtencion>> = await this.api.get(url);
    return response.data;
  }

  async getTipoAtencion(id: number): Promise<TipoAtencion> {
    const response: AxiosResponse<TipoAtencion> = await this.api.get(`/catalogos/tipos-atencion/${id}/`);
    return response.data;
  }

  // NUEVO: Áreas de Internación
  async getAreasInternacion(centroFisico?: string): Promise<ApiResponse<AreaInternacion>> {
    const url = centroFisico 
      ? `/catalogos/areas-internacion/?centro_fisico=${centroFisico}`
      : '/catalogos/areas-internacion/';
    const response: AxiosResponse<ApiResponse<AreaInternacion>> = await this.api.get(url);
    return response.data;
  }

  async getAreaInternacion(id: number): Promise<AreaInternacion> {
    const response: AxiosResponse<AreaInternacion> = await this.api.get(`/catalogos/areas-internacion/${id}/`);
    return response.data;
  }

  // NUEVO: Camas de Internación
  async getCamasInternacion(area?: string, estado?: string): Promise<ApiResponse<CamaInternacion>> {
    let url = '/catalogos/camas-internacion/';
    const params = new URLSearchParams();
    if (area) params.append('area', area);
    if (estado) params.append('estado', estado);
    if (params.toString()) url += `?${params.toString()}`;
    
    const response: AxiosResponse<ApiResponse<CamaInternacion>> = await this.api.get(url);
    return response.data;
  }

  async getCamaInternacion(id: number): Promise<CamaInternacion> {
    const response: AxiosResponse<CamaInternacion> = await this.api.get(`/catalogos/camas-internacion/${id}/`);
    return response.data;
  }

  // NUEVO: Internaciones
  async getInternaciones(estado?: string, centroFisico?: string, area?: string): Promise<ApiResponse<Internacion>> {
    let url = '/internaciones/';
    const params = new URLSearchParams();
    if (estado) params.append('estado', estado);
    if (centroFisico) params.append('centro_fisico', centroFisico);
    if (area) params.append('area', area);
    if (params.toString()) url += `?${params.toString()}`;
    
    const response: AxiosResponse<ApiResponse<Internacion>> = await this.api.get(url);
    return response.data;
  }

  async getInternacion(id: number): Promise<Internacion> {
    const response: AxiosResponse<Internacion> = await this.api.get(`/internaciones/${id}/`);
    return response.data;
  }

  async createInternacion(internacion: Partial<Internacion>): Promise<Internacion> {
    const response: AxiosResponse<Internacion> = await this.api.post('/internaciones/', internacion);
    return response.data;
  }

  async updateInternacion(id: number, internacion: Partial<Internacion>): Promise<Internacion> {
    const response: AxiosResponse<Internacion> = await this.api.put(`/internaciones/${id}/`, internacion);
    return response.data;
  }

  async deleteInternacion(id: number): Promise<void> {
    await this.api.delete(`/internaciones/${id}/`);
  }

  async darAltaInternacion(id: number, data: { fecha_alta?: string; observaciones?: string }): Promise<Internacion> {
    const response: AxiosResponse<Internacion> = await this.api.post(`/internaciones/${id}/dar_alta/`, data);
    return response.data;
  }

  async getEstadisticasInternaciones(): Promise<any> {
    const response: AxiosResponse<any> = await this.api.get('/internaciones/estadisticas/');
    return response.data;
  }
}

// Instancia singleton del servicio
export const apiService = new ApiService();
export default apiService; 