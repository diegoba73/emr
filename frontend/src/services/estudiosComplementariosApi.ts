import { apiClient as api } from './apiClient';
import type { AxiosResponse } from 'axios';
import type {
  AgregarArchivoEstudioPayload,
  AgendarTurnoEstudioDesdeAgendaPayload,
  AsignarTurnoEstudioPayload,
  ArchivoEstudioComplementario,
  CreateEstudioComplementarioPayload,
  EstudioComplementario,
  InformeEstudioComplementario,
  SubirArchivoEstudioPayload,
  TipoEstudioComplementario,
  UpdateEstudioComplementarioPayload,
} from '../types/estudios';
import type { ApiResponse } from '../types';

export interface ListEstudiosParams {
  paciente?: number;
  paciente_id?: number;
  estado?: string;
  modalidad?: string;
  search?: string;
  page?: number;
}

function unwrapList<T>(data: T[] | ApiResponse<T>): T[] {
  if (Array.isArray(data)) {
    return data;
  }
  return data.results ?? [];
}

async function fetchAllPages<T>(initialPath: string, params?: Record<string, string | number>): Promise<T[]> {
  const qs = new URLSearchParams();
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== '') qs.append(k, String(v));
    }
  }
  const q = qs.toString();
  let path: string | null = `${initialPath}${q ? `?${q}` : ''}`;
  const out: T[] = [];
  const seen = new Set<string>();
  while (path && seen.size < 8) {
    if (seen.has(path)) break;
    seen.add(path);
    const response: AxiosResponse<ApiResponse<T> | T[]> = await api.get(path);
    const body = response.data;
    if (Array.isArray(body)) {
      out.push(...body);
      break;
    }
    if (body?.results) out.push(...body.results);
    const next = body?.next;
    if (!next) break;
    try {
      const u = new URL(next, api.defaults.baseURL || undefined);
      path = u.pathname.replace(/^\/api/, '') + u.search;
    } catch {
      break;
    }
  }
  return out;
}

export const listTiposEstudioComplementario = async (): Promise<TipoEstudioComplementario[]> => {
  return fetchAllPages<TipoEstudioComplementario>('/estudios-complementarios/tipos/', {
    page_size: 200,
  });
};

export const listEstudiosComplementarios = async (
  params?: ListEstudiosParams
): Promise<EstudioComplementario[]> => {
  const response = await api.get('/estudios-complementarios/', { params });
  return unwrapList<EstudioComplementario>(response.data);
};

export const getEstudioComplementario = async (
  id: number
): Promise<EstudioComplementario> => {
  const response = await api.get(`/estudios-complementarios/${id}/`);
  return response.data;
};

export const createEstudioComplementario = async (
  payload: CreateEstudioComplementarioPayload
): Promise<EstudioComplementario> => {
  const response = await api.post('/estudios-complementarios/', payload);
  return response.data;
};

export const updateEstudioComplementario = async (
  id: number,
  payload: UpdateEstudioComplementarioPayload
): Promise<EstudioComplementario> => {
  const response = await api.patch(`/estudios-complementarios/${id}/`, payload);
  return response.data;
};

export const marcarRealizadoEstudio = async (id: number): Promise<EstudioComplementario> => {
  const response = await api.post(`/estudios-complementarios/${id}/marcar-realizado/`);
  return response.data;
};

export const asignarTurnoEstudio = async (
  id: number,
  payload: AsignarTurnoEstudioPayload
): Promise<EstudioComplementario> => {
  const response = await api.post(`/estudios-complementarios/${id}/asignar-turno/`, payload);
  return response.data;
};

/** Crea estudio (si hace falta) y asigna turno de sala en un paso — turnera. */
export const agendarTurnoEstudioDesdeAgenda = async (
  payload: AgendarTurnoEstudioDesdeAgendaPayload
): Promise<EstudioComplementario> => {
  const response = await api.post('/estudios-complementarios/agendar-turno/', payload);
  return response.data;
};

export const anularEstudio = async (
  id: number,
  motivo_anulacion: string
): Promise<EstudioComplementario> => {
  const response = await api.post(`/estudios-complementarios/${id}/anular/`, {
    motivo_anulacion,
  });
  return response.data;
};

export const entregarEstudio = async (id: number): Promise<EstudioComplementario> => {
  const response = await api.post(`/estudios-complementarios/${id}/entregar/`);
  return response.data;
};

export interface SugerirInformeEstudioResponse {
  texto: string;
  fuente: 'reglas' | 'medgemma' | string;
  marcado_sugerencia?: boolean;
  modelo?: string;
  vacio?: boolean;
  detalle?: Record<string, unknown>;
}

/** Borrador de informe (plantilla y/o MedGemma). No persiste. */
export const sugerirInformeEstudio = async (
  estudioId: number,
  payload?: { notas_medico?: string; prefer_medgemma?: boolean }
): Promise<SugerirInformeEstudioResponse> => {
  const response = await api.post(
    `/estudios-complementarios/${estudioId}/sugerir-informe/`,
    payload || {}
  );
  return response.data;
};

export const listArchivosEstudio = async (
  estudioId: number
): Promise<ArchivoEstudioComplementario[]> => {
  const response = await api.get(`/estudios-complementarios/${estudioId}/archivos/`);
  return response.data;
};

export const agregarArchivoEstudio = async (
  estudioId: number,
  payload: AgregarArchivoEstudioPayload
): Promise<ArchivoEstudioComplementario> => {
  const response = await api.post(
    `/estudios-complementarios/${estudioId}/agregar-archivo/`,
    payload
  );
  return response.data;
};

export const subirArchivoEstudio = async (
  estudioId: number,
  payload: SubirArchivoEstudioPayload
): Promise<ArchivoEstudioComplementario> => {
  const form = new FormData();
  form.append('archivo', payload.archivo);
  if (payload.titulo) form.append('titulo', payload.titulo);
  if (payload.tipo_archivo) form.append('tipo_archivo', payload.tipo_archivo);
  if (payload.tipo_rol) form.append('tipo_rol', payload.tipo_rol);
  if (payload.descripcion) form.append('descripcion', payload.descripcion);
  if (payload.orden != null) form.append('orden', String(payload.orden));
  if (payload.es_principal != null) form.append('es_principal', String(payload.es_principal));
  const response = await api.post(
    `/estudios-complementarios/${estudioId}/subir-archivo/`,
    form
  );
  return response.data;
};

export const quitarArchivoEstudio = async (
  estudioId: number,
  archivoEstudioId: number
): Promise<{
  ok: boolean;
  archivo_estudio_id: number;
  archivo_medico_id: number;
  archivo_medico_eliminado: boolean;
}> => {
  const response = await api.post(`/estudios-complementarios/${estudioId}/quitar-archivo/`, {
    archivo_estudio_id: archivoEstudioId,
  });
  return response.data;
};

export const downloadArchivoEstudio = async (
  estudioId: number,
  archivoEstudioId: number
): Promise<Blob> => {
  const response = await api.get(
    `/estudios-complementarios/${estudioId}/archivos/${archivoEstudioId}/download/`,
    { responseType: 'blob' }
  );
  return response.data;
};

export const listInformesEstudio = async (
  estudioId: number
): Promise<InformeEstudioComplementario[]> => {
  const response = await api.get(`/estudios-complementarios/${estudioId}/informes/`);
  return response.data;
};

export const crearInformeEstudio = async (
  estudioId: number,
  payload: { texto?: string; tipo?: 'PRELIMINAR' | 'FINAL' }
): Promise<InformeEstudioComplementario> => {
  const response = await api.post(
    `/estudios-complementarios/${estudioId}/informes/`,
    payload
  );
  return response.data;
};

export const emitirInformeEstudio = async (
  estudioId: number,
  informeId: number
): Promise<InformeEstudioComplementario> => {
  const response = await api.post(
    `/estudios-complementarios/${estudioId}/informes/${informeId}/emitir/`
  );
  return response.data;
};

export const validarInformeEstudio = async (
  estudioId: number,
  informeId: number
): Promise<InformeEstudioComplementario> => {
  const response = await api.post(
    `/estudios-complementarios/${estudioId}/informes/${informeId}/validar/`
  );
  return response.data;
};

export const downloadInformeEstudioPdf = async (
  estudioId: number,
  informeId: number
): Promise<Blob> => {
  const response = await api.get(
    `/estudios-complementarios/${estudioId}/informes/${informeId}/download-pdf/`,
    { responseType: 'blob' }
  );
  return response.data;
};

export const rectificarInformeEstudio = async (
  estudioId: number,
  informeId: number,
  payload: { motivo_rectificacion: string; texto?: string }
): Promise<InformeEstudioComplementario> => {
  const response = await api.post(
    `/estudios-complementarios/${estudioId}/informes/${informeId}/rectificar/`,
    payload
  );
  return response.data;
};

/** Descarga protegida vía blob (sin /media/). */
export async function triggerBlobDownload(
  blob: Blob,
  filename: string
): Promise<void> {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename || 'archivo';
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
