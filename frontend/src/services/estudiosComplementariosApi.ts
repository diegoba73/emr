import { apiClient as api } from './apiClient';
import type {
  AgregarArchivoEstudioPayload,
  ArchivoEstudioComplementario,
  CreateEstudioComplementarioPayload,
  EstudioComplementario,
  InformeEstudioComplementario,
  UpdateEstudioComplementarioPayload,
} from '../types/estudios';
import type { ApiResponse } from '../types';

export interface ListEstudiosParams {
  paciente?: number;
  paciente_id?: number;
  estado?: string;
  modalidad?: string;
  page?: number;
}

function unwrapList<T>(data: T[] | ApiResponse<T>): T[] {
  if (Array.isArray(data)) {
    return data;
  }
  return data.results ?? [];
}

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
