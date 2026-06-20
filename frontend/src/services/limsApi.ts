import { AxiosError } from 'axios';
import { apiClient } from './apiClient';
import { triggerBlobDownload } from './estudiosComplementariosApi';
import {
  assertValidSolicitudId,
  informeLimsPdfFilename,
} from '../utils/limsDownload';
import type {
  CargarResultadoPayload,
  LimsPanelExamen,
  LimsTipoContenedor,
  LimsTipoExamen,
  LimsTipoMuestra,
  MuestraTransaccional,
  Paginated,
  SolicitudExamenLims,
} from '../types/lims';

const LAB = '/lab';

/** Extrae mensaje legible de respuestas DRF (400/403/…). Sin registrar datos sensibles. */
export function formatDrfError(error: unknown): string {
  if (!error || typeof error !== 'object') return 'Error desconocido';
  const ax = error as AxiosError<{ detail?: string; error?: string; message?: string } | Record<string, unknown>>;
  const status = ax.response?.status;
  const data = ax.response?.data;
  if (data && typeof data === 'object') {
    const o = data as Record<string, unknown>;
    if (typeof o.detail === 'string') return o.detail;
    if (typeof o.error === 'string') return o.error;
    if (typeof o.message === 'string') return o.message;
    const parts: string[] = [];
    for (const [k, v] of Object.entries(o)) {
      if (k === 'detail' || k === 'error') continue;
      if (Array.isArray(v)) parts.push(`${k}: ${v.join(' ')}`);
      else if (typeof v === 'string') parts.push(`${k}: ${v}`);
    }
    if (parts.length) return parts.join(' · ');
  }
  if (ax.message) return ax.message;
  return status ? `Error HTTP ${status}` : 'Error de red o servidor';
}

/** Mensajes HTTP LIMS sin exponer cuerpo de respuesta (B2-C). */
export function formatLimsHttpError(error: unknown, context?: 'cargar_resultados'): string {
  const ax = error as AxiosError;
  const status = ax.response?.status;
  if (status === 403) {
    return context === 'cargar_resultados'
      ? 'No tenés permisos para cargar resultados.'
      : 'No tenés permisos para esta operación.';
  }
  if (status === 404) {
    return 'No se encontró la solicitud o no tenés acceso.';
  }
  if (status === 500) {
    return 'Error interno del servidor. Intente más tarde.';
  }
  return formatDrfError(error);
}

function pathFromDrfNext(nextUrl: string): string {
  const base = apiClient.defaults.baseURL || '';
  try {
    const u = new URL(nextUrl, base || undefined);
    const p = u.pathname + u.search;
    return p.startsWith('/api/') ? p.slice(4) : p.startsWith('/') ? p : `/${p}`;
  } catch {
    return nextUrl.startsWith('/api') ? nextUrl.replace(/^\/api/, '') : nextUrl;
  }
}

export async function getPaginatedAll<T>(
  initialPath: string,
  params?: Record<string, string | number | undefined>
): Promise<T[]> {
  const qs = new URLSearchParams();
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== '') qs.append(k, String(v));
    }
  }
  const q = qs.toString();
  let path: string | null = `${initialPath}${q ? `?${q}` : ''}`;
  const out: T[] = [];
  while (path) {
    const res = await apiClient.get<Paginated<T> | T[]>(path);
    const body = res.data;
    if (Array.isArray(body)) {
      out.push(...body);
      break;
    }
    if (body?.results) out.push(...body.results);
    const next = body?.next;
    if (!next) break;
    try {
      path = pathFromDrfNext(next);
    } catch {
      break;
    }
  }
  return out;
}

// --- Solicitudes LIMS ---

export async function listSolicitudesExamen(params?: {
  estado?: string;
  numero?: string;
  paciente?: number;
}): Promise<SolicitudExamenLims[]> {
  return getPaginatedAll<SolicitudExamenLims>(`${LAB}/solicitudes/`, {
    ...params,
    page_size: 200,
  });
}

export async function getSolicitudExamen(id: number): Promise<SolicitudExamenLims> {
  const { data } = await apiClient.get<SolicitudExamenLims>(`${LAB}/solicitudes/${id}/`);
  return data;
}

export async function postTomarMuestraOrden(id: number): Promise<SolicitudExamenLims> {
  const { data } = await apiClient.post<SolicitudExamenLims>(`${LAB}/solicitudes/${id}/tomar-muestra/`, {});
  return data;
}

export async function postCargarResultados(
  id: number,
  resultados: CargarResultadoPayload[]
): Promise<SolicitudExamenLims> {
  const { data } = await apiClient.post<SolicitudExamenLims>(`${LAB}/solicitudes/${id}/cargar-resultados/`, {
    resultados,
  });
  return data;
}

/** Catálogo tipos examen indexado por id (carga de resultados B2-C). */
export async function getTiposExamenMap(): Promise<Map<number, LimsTipoExamen>> {
  const list = await listTiposExamenLims();
  return new Map(list.map((t) => [t.id, t]));
}

export async function postValidarOrden(id: number): Promise<SolicitudExamenLims> {
  const { data } = await apiClient.post<SolicitudExamenLims>(`${LAB}/solicitudes/${id}/validar/`, {});
  return data;
}

export async function postMarcarEntregado(id: number): Promise<SolicitudExamenLims> {
  const { data } = await apiClient.post<SolicitudExamenLims>(`${LAB}/solicitudes/${id}/marcar-entregado/`, {});
  return data;
}

export async function postCancelarOrden(id: number): Promise<SolicitudExamenLims> {
  const { data } = await apiClient.post<SolicitudExamenLims>(`${LAB}/solicitudes/${id}/cancelar/`, {});
  return data;
}

/** PDF LIMS básico (PDF-1): blob protegido, sin /media/. */
export async function getInformeLimsPdfBlob(solicitudId: number): Promise<Blob> {
  assertValidSolicitudId(solicitudId);
  const { data } = await apiClient.get<Blob>(`${LAB}/solicitudes/${solicitudId}/informe-pdf/`, {
    responseType: 'blob',
  });
  return data;
}

/** Descarga informe PDF LIMS con filename seguro y revocación de URL temporal. */
export async function downloadInformeLimsPdf(solicitudId: number): Promise<void> {
  const blob = await getInformeLimsPdfBlob(solicitudId);
  await triggerBlobDownload(blob, informeLimsPdfFilename(solicitudId));
}

// --- Muestras transaccionales ---

export async function listMuestrasPorSolicitud(
  solicitudId: number,
  numeroSolicitud?: string | null
): Promise<MuestraTransaccional[]> {
  const params: Record<string, string | number | undefined> = { page_size: 200, solicitud: solicitudId };
  if (numeroSolicitud) params.search = numeroSolicitud;
  return getPaginatedAll<MuestraTransaccional>(`${LAB}/muestras-transaccionales/`, params);
}

export async function createMuestra(payload: {
  solicitud_id: number;
  tipo_muestra_id: number;
  tipo_contenedor_id?: number | null;
  observaciones?: string;
}): Promise<MuestraTransaccional> {
  const { data } = await apiClient.post<MuestraTransaccional>(`${LAB}/muestras-transaccionales/`, payload);
  return data;
}

export async function postMuestraTomar(id: number, body: { observaciones?: string } = {}): Promise<MuestraTransaccional> {
  const { data } = await apiClient.post<MuestraTransaccional>(`${LAB}/muestras-transaccionales/${id}/tomar/`, body);
  return data;
}

export async function postMuestraRecibir(
  id: number,
  body: { observaciones?: string; ubicacion_actual?: string } = {}
): Promise<MuestraTransaccional> {
  const { data } = await apiClient.post<MuestraTransaccional>(`${LAB}/muestras-transaccionales/${id}/recibir/`, body);
  return data;
}

export async function postMuestraRechazar(
  id: number,
  body: { motivo_rechazo: string; observaciones?: string }
): Promise<MuestraTransaccional> {
  const { data } = await apiClient.post<MuestraTransaccional>(`${LAB}/muestras-transaccionales/${id}/rechazar/`, body);
  return data;
}

export async function postMuestraConservar(
  id: number,
  body: { ubicacion_actual?: string; observaciones?: string } = {}
): Promise<MuestraTransaccional> {
  const { data } = await apiClient.post<MuestraTransaccional>(`${LAB}/muestras-transaccionales/${id}/conservar/`, body);
  return data;
}

export async function postMuestraDescartar(id: number, body: { observaciones?: string } = {}): Promise<MuestraTransaccional> {
  const { data } = await apiClient.post<MuestraTransaccional>(`${LAB}/muestras-transaccionales/${id}/descartar/`, body);
  return data;
}

export async function postMuestraCancelar(
  id: number,
  body: { motivo?: string; observaciones?: string } = {}
): Promise<MuestraTransaccional> {
  const { data } = await apiClient.post<MuestraTransaccional>(`${LAB}/muestras-transaccionales/${id}/cancelar/`, body);
  return data;
}

// --- Catálogos ---

export async function listTiposExamenLims(): Promise<LimsTipoExamen[]> {
  return getPaginatedAll<LimsTipoExamen>(`${LAB}/examenes/`, { page_size: 500 });
}

export async function listTiposMuestraLims(): Promise<LimsTipoMuestra[]> {
  return getPaginatedAll<LimsTipoMuestra>(`${LAB}/muestras/`, { page_size: 500 });
}

export async function listPanelesLims(): Promise<LimsPanelExamen[]> {
  return getPaginatedAll<LimsPanelExamen>(`${LAB}/paneles/`, { page_size: 200 });
}

export async function listContenedoresLims(): Promise<LimsTipoContenedor[]> {
  return getPaginatedAll<LimsTipoContenedor>(`${LAB}/contenedores/`, { page_size: 200 });
}

export * from './limsMicroApi';
