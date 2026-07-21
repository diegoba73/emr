import { AxiosError } from 'axios';
import { apiClient } from './apiClient';
import { triggerBlobDownload } from './estudiosComplementariosApi';
import {
  assertValidSolicitudId,
  informeLimsPdfFilename,
} from '../utils/limsDownload';
import type {
  AnalisisLongitudinalOrden,
  CargarResultadoPayload,
  LimsPanelExamen,
  LimsTipoContenedor,
  LimsTipoExamen,
  TipoExamenLimsWriteBody,
  LimsTipoMuestra,
  MuestraTransaccional,
  MuestraLookupLims,
  Paginated,
  OrigenSolicitudLims,
  EnviarInformeOrdenResponse,
  SolicitudExamenLims,
} from '../types/lims';
import type { TuboOrdenPreview } from '../utils/limsTubosOrden';

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
  search?: string;
  /** YYYY-MM-DD — fecha de creación de la orden. */
  fecha?: string;
  /** YYYY-MM-DD — día en que se tomó la muestra (bandeja diaria de laboratorio). */
  fecha_muestra?: string;
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

export async function postTomarMuestraOrden(
  id: number,
  body: {
    muestras?: Array<{
      tipo_muestra_id: number;
      tipo_contenedor_id?: number | null;
      observaciones?: string;
    }>;
  } = {}
): Promise<SolicitudExamenLims> {
  const { data } = await apiClient.post<SolicitudExamenLims>(`${LAB}/solicitudes/${id}/tomar-muestra/`, body);
  return data;
}

export async function getTubosPreviewOrden(solicitudId: number): Promise<TuboOrdenPreview[]> {
  const { data } = await apiClient.get<{ tubos: TuboOrdenPreview[] }>(
    `${LAB}/solicitudes/${solicitudId}/tubos-preview/`
  );
  return data.tubos || [];
}

export async function postCargarResultados(
  id: number,
  resultados: CargarResultadoPayload[],
  options?: { observaciones?: string; informar_parcial?: boolean; orden_grupos_informe?: string[] }
): Promise<SolicitudExamenLims> {
  const body: {
    resultados: CargarResultadoPayload[];
    observaciones?: string;
    informar_parcial?: boolean;
    orden_grupos_informe?: string[];
  } = { resultados };
  if (options?.observaciones !== undefined) {
    body.observaciones = options.observaciones;
  }
  if (options?.informar_parcial) {
    body.informar_parcial = true;
  }
  if (options?.orden_grupos_informe !== undefined) {
    body.orden_grupos_informe = options.orden_grupos_informe;
  }
  const { data } = await apiClient.post<SolicitudExamenLims>(`${LAB}/solicitudes/${id}/cargar-resultados/`, body);
  return data;
}

export async function patchOrdenInformeOrden(
  id: number,
  orden_grupos_informe: string[]
): Promise<SolicitudExamenLims> {
  const { data } = await apiClient.patch<SolicitudExamenLims>(
    `${LAB}/solicitudes/${id}/orden-informe/`,
    { orden_grupos_informe }
  );
  return data;
}

export async function getAnalisisLongitudinal(id: number): Promise<AnalisisLongitudinalOrden> {
  const { data } = await apiClient.get<AnalisisLongitudinalOrden>(
    `${LAB}/solicitudes/${id}/analisis-longitudinal/`
  );
  return data;
}

/** Catálogo tipos examen indexado por id (carga de resultados B2-C). */
export async function getTiposExamenMap(): Promise<Map<number, LimsTipoExamen>> {
  const list = await listTiposExamenLims({ activo: true });
  return new Map(list.map((t) => [t.id, t]));
}

export async function postEnviarInformeOrden(
  id: number,
  body: { email?: boolean; whatsapp?: boolean }
): Promise<EnviarInformeOrdenResponse> {
  const { data } = await apiClient.post<EnviarInformeOrdenResponse>(
    `${LAB}/solicitudes/${id}/enviar-informe/`,
    body,
    { timeout: 45_000 }
  );
  return data;
}

/** Validar y liberar informe (bioquímico / admin). Bloquea resultados. */
export async function postValidarSolicitud(
  id: number,
  options?: { confirmar_criticos?: boolean }
): Promise<SolicitudExamenLims> {
  const body: { confirmar_criticos?: boolean } = {};
  if (options?.confirmar_criticos) {
    body.confirmar_criticos = true;
  }
  const { data } = await apiClient.post<SolicitudExamenLims>(
    `${LAB}/solicitudes/${id}/validar/`,
    body
  );
  return data;
}

/** @deprecated Usar postValidarSolicitud */
export async function postFinalizarOrden(
  id: number,
  options?: { confirmar_criticos?: boolean }
): Promise<SolicitudExamenLims> {
  return postValidarSolicitud(id, options);
}

/** @deprecated Usar postValidarSolicitud */
export async function postValidarOrden(
  id: number,
  options?: { confirmar_criticos?: boolean }
): Promise<SolicitudExamenLims> {
  return postValidarSolicitud(id, options);
}

export interface CreateSolicitudExamenLimsPayload {
  paciente_id: number;
  medico_id?: number;
  medico_externo_nombre?: string;
  consulta_hc_id?: number;
  origen_solicitud?: OrigenSolicitudLims;
  examenes_ids?: number[];
  paneles_ids?: number[];
  observaciones?: string;
}

export async function createSolicitudExamenLims(
  body: CreateSolicitudExamenLimsPayload
): Promise<SolicitudExamenLims> {
  const { data } = await apiClient.post<SolicitudExamenLims>(`${LAB}/solicitudes/`, body);
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

export async function getMuestraPorCodigo(codigo: string): Promise<MuestraLookupLims> {
  const encoded = encodeURIComponent(codigo.trim());
  const { data } = await apiClient.get<MuestraLookupLims>(
    `${LAB}/muestras-transaccionales/por-codigo/${encoded}/`
  );
  return data;
}

export async function postRecibirMuestraPorCodigo(body: {
  codigo_barra: string;
  ubicacion_actual?: string;
  observaciones?: string;
}): Promise<MuestraLookupLims & {
  extraccion_completa?: boolean;
  tubos_pendientes_extraccion?: Array<{
    id: number;
    codigo_barra: string | null;
    tipo_contenedor_codigo?: string | null;
    tipo_contenedor_nombre?: string | null;
  }>;
}> {
  const { data } = await apiClient.post(
    `${LAB}/muestras-transaccionales/recibir-por-codigo/`,
    body
  );
  return data;
}

export async function postTomarMuestraPorCodigo(body: {
  codigo_barra: string;
  observaciones?: string;
}): Promise<MuestraLookupLims & {
  extraccion_completa?: boolean;
  tubos_pendientes_extraccion?: Array<{
    id: number;
    codigo_barra: string | null;
    tipo_contenedor_codigo?: string | null;
    tipo_contenedor_nombre?: string | null;
  }>;
}> {
  const { data } = await apiClient.post(
    `${LAB}/muestras-transaccionales/tomar-por-codigo/`,
    body
  );
  return data;
}

export async function getEtiquetaMuestraPdfBlob(muestraId: number): Promise<Blob> {
  const { data } = await apiClient.get<Blob>(`${LAB}/muestras-transaccionales/${muestraId}/etiqueta/`, {
    responseType: 'blob',
  });
  return data;
}

export async function downloadEtiquetaMuestra(muestraId: number, codigoBarra?: string | null): Promise<void> {
  const blob = await getEtiquetaMuestraPdfBlob(muestraId);
  const safe = (codigoBarra || String(muestraId)).replace(/\//g, '-');
  await triggerBlobDownload(blob, `etiqueta-muestra-${safe}.pdf`);
}

export async function getEtiquetasOrdenMuestrasPdfBlob(solicitudId: number): Promise<Blob> {
  assertValidSolicitudId(solicitudId);
  const { data } = await apiClient.get<Blob>(`${LAB}/solicitudes/${solicitudId}/etiquetas-muestras/`, {
    responseType: 'blob',
  });
  return data;
}

export async function downloadEtiquetasOrdenMuestras(
  solicitudId: number,
  numeroOrden?: string | null
): Promise<void> {
  const blob = await getEtiquetasOrdenMuestrasPdfBlob(solicitudId);
  const ref = (numeroOrden || String(solicitudId)).replace(/\//g, '-');
  await triggerBlobDownload(blob, `etiquetas-orden-${ref}.pdf`);
}

// --- Catálogos ---

export async function listTiposExamenLims(params?: {
  activo?: boolean;
  search?: string;
}): Promise<LimsTipoExamen[]> {
  const query: Record<string, string | number | undefined> = { page_size: 500 };
  if (params?.activo !== undefined) query.activo = params.activo ? 'true' : 'false';
  if (params?.search) query.search = params.search;
  return getPaginatedAll<LimsTipoExamen>(`${LAB}/examenes/`, query);
}

export function sanitizeTipoExamenWriteBody(body: TipoExamenLimsWriteBody): TipoExamenLimsWriteBody {
  const out: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(body)) {
    if (value === undefined) continue;
    out[key] = value;
  }
  for (const key of ['metodo', 'unidad_default', 'abreviatura', 'rango_referencia_texto'] as const) {
    if (out[key] === null) delete out[key];
  }
  const modo = out.modo_entrada;
  if (modo && modo !== 'ESTANDAR') {
    if (out.multiplicador_clinico === '' || out.multiplicador_clinico === null) {
      out.multiplicador_clinico = 1;
    }
  }
  return out as TipoExamenLimsWriteBody;
}

export async function createTipoExamenLims(
  body: TipoExamenLimsWriteBody & { codigo: string; nombre: string; tipo_muestra_requerida: number }
): Promise<LimsTipoExamen> {
  const { data } = await apiClient.post<LimsTipoExamen>(
    `${LAB}/examenes/`,
    sanitizeTipoExamenWriteBody(body)
  );
  return data;
}

export async function patchTipoExamenLims(
  id: number,
  body: TipoExamenLimsWriteBody
): Promise<LimsTipoExamen> {
  const { data } = await apiClient.patch<LimsTipoExamen>(
    `${LAB}/examenes/${id}/`,
    sanitizeTipoExamenWriteBody(body)
  );
  return data;
}

export async function listTiposMuestraLims(params?: {
  activo?: boolean;
  search?: string;
}): Promise<LimsTipoMuestra[]> {
  const query: Record<string, string | number | undefined> = { page_size: 500 };
  if (params?.activo !== undefined) query.activo = params.activo ? 'true' : 'false';
  if (params?.search) query.search = params.search;
  return getPaginatedAll<LimsTipoMuestra>(`${LAB}/muestras/`, query);
}

export async function createTipoMuestraLims(body: {
  codigo: string;
  nombre: string;
  color_tubo?: string;
  activo?: boolean;
}): Promise<LimsTipoMuestra> {
  const { data } = await apiClient.post<LimsTipoMuestra>(`${LAB}/muestras/`, body);
  return data;
}

export async function patchTipoMuestraLims(
  id: number,
  body: Partial<Pick<LimsTipoMuestra, 'nombre' | 'color_tubo' | 'activo'>>
): Promise<LimsTipoMuestra> {
  const { data } = await apiClient.patch<LimsTipoMuestra>(`${LAB}/muestras/${id}/`, body);
  return data;
}

export async function listPanelesLims(): Promise<LimsPanelExamen[]> {
  return getPaginatedAll<LimsPanelExamen>(`${LAB}/paneles/`, { page_size: 200 });
}

export async function listContenedoresLims(): Promise<LimsTipoContenedor[]> {
  return getPaginatedAll<LimsTipoContenedor>(`${LAB}/contenedores/`, { page_size: 200 });
}

export * from './limsMicroApi';
