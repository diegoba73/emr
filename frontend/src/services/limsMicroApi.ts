/**
 * API microbiología LIMS — /lab/microbiologia/...
 */
import { apiClient } from './apiClient';
import { triggerBlobDownload } from './estudiosComplementariosApi';
import type {
  AisladoMicrobiologico,
  Antibiograma,
  Antibiotico,
  EnviarInformeMicroResponse,
  EstudioMicrobiologia,
  IdentificacionMicroorganismo,
  InformeMicrobiologia,
  LecturaCultivo,
  MedioCultivo,
  Microorganismo,
  ResultadoAntibiotico,
  SiembraMicrobiologia,
  TipoCultivoMicrobiologia,
  TipoEstudioMicrobiologia,
  TipoMuestraMicrobiologia,
} from '../types/lims';
import { informeMicroPdfFilename } from '../utils/limsDownload';
import { getPaginatedAll } from './limsApi';

const MICRO = '/lab/microbiologia';

export const listTiposCultivoMicro = (params?: { search?: string }) =>
  getPaginatedAll<TipoCultivoMicrobiologia>(`${MICRO}/tipos-cultivo/`, {
    page_size: 200,
    ...params,
  });
export const listTiposMuestraMicro = (params?: { search?: string }) =>
  getPaginatedAll<TipoMuestraMicrobiologia>(`${MICRO}/tipos-muestra/`, {
    page_size: 200,
    ...params,
  });

// --- Medios ---
export const listMediosCultivo = (params?: { search?: string }) =>
  getPaginatedAll<MedioCultivo>(`${MICRO}/medios/`, { page_size: 500, ...params });
export const createMedioCultivo = (body: Partial<MedioCultivo>) =>
  apiClient.post<MedioCultivo>(`${MICRO}/medios/`, body).then((r) => r.data);
export const updateMedioCultivo = (id: number, body: Partial<MedioCultivo>) =>
  apiClient.patch<MedioCultivo>(`${MICRO}/medios/${id}/`, body).then((r) => r.data);

// --- Estudios ---
export const listEstudiosMicrobiologia = (params?: {
  search?: string;
  estado?: string;
  sin_etiquetas?: boolean;
  esperando_recepcion?: boolean;
}) => {
  const q: Record<string, string | number | undefined> = { page_size: 80 };
  if (params?.search) q.search = params.search;
  if (params?.estado) q.estado = params.estado;
  if (params?.sin_etiquetas) q.sin_etiquetas = '1';
  if (params?.esperando_recepcion) q.esperando_recepcion = '1';
  return getPaginatedAll<EstudioMicrobiologia>(`${MICRO}/estudios/`, q);
};
export const getEstudioMicrobiologia = (id: number) =>
  apiClient.get<EstudioMicrobiologia>(`${MICRO}/estudios/${id}/`).then((r) => r.data);

export async function getEstudioMicroPorCodigo(codigo: string): Promise<EstudioMicrobiologia> {
  const encoded = encodeURIComponent(codigo.trim());
  const { data } = await apiClient.get<EstudioMicrobiologia>(
    `${MICRO}/estudios/por-codigo/${encoded}/`
  );
  return data;
}

export async function postRecibirEstudioMicroPorCodigo(body: {
  codigo_barra: string;
}): Promise<EstudioMicrobiologia> {
  const { data } = await apiClient.post<EstudioMicrobiologia>(
    `${MICRO}/estudios/recibir-por-codigo/`,
    body
  );
  return data;
}

export const createEstudioMicrobiologia = (body: {
  paciente_id?: number;
  medico_id?: number | null;
  medico_externo_nombre?: string;
  consulta_hc_id?: number | null;
  origen_solicitud?: string;
  tipo_cultivo_id?: number;
  tipo_muestra_micro_id?: number;
  /** @deprecated alias de tipo_muestra_micro_id */
  tipo_muestra_id?: number;
  solicitud_id?: number;
  muestra_id?: number;
  tipo_estudio?: TipoEstudioMicrobiologia | string;
  observaciones?: string;
}) => apiClient.post<EstudioMicrobiologia>(`${MICRO}/estudios/`, body).then((r) => r.data);

export const createEstudiosMicrobiologiaBatch = (body: {
  paciente_id: number;
  medico_id?: number | null;
  medico_externo_nombre?: string;
  consulta_hc_id?: number | null;
  origen_solicitud?: string;
  observaciones?: string;
  items: Array<{ tipo_cultivo_id: number; tipo_muestra_micro_id: number }>;
}) =>
  apiClient
    .post<EstudioMicrobiologia[]>(`${MICRO}/estudios/batch/`, body)
    .then((r) => r.data);

export async function downloadEtiquetasEstudioMicro(estudioId: number): Promise<void> {
  const res = await apiClient.post(
    `${MICRO}/estudios/${estudioId}/imprimir-etiquetas/`,
    {},
    { responseType: 'blob' }
  );
  const blob = new Blob([res.data], { type: 'application/pdf' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `etiquetas-micro-${estudioId}.pdf`;
  a.click();
  window.URL.revokeObjectURL(url);
}

export async function downloadEtiquetasEstudiosMicroBatch(estudioIds: number[]): Promise<void> {
  const res = await apiClient.post(
    `${MICRO}/estudios/imprimir-etiquetas/`,
    { estudio_ids: estudioIds },
    { responseType: 'blob' }
  );
  const blob = new Blob([res.data], { type: 'application/pdf' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `etiquetas-micro-batch.pdf`;
  a.click();
  window.URL.revokeObjectURL(url);
}

export const updateEstudioMicrobiologia = (
  id: number,
  body: { tipo_estudio?: string; observaciones?: string }
) => apiClient.patch<EstudioMicrobiologia>(`${MICRO}/estudios/${id}/`, body).then((r) => r.data);
export const iniciarEstudioMicrobiologia = (id: number) =>
  apiClient.post<EstudioMicrobiologia>(`${MICRO}/estudios/${id}/iniciar/`, {}).then((r) => r.data);
export const cancelarEstudioMicrobiologia = (id: number, motivo: string) =>
  apiClient.post<EstudioMicrobiologia>(`${MICRO}/estudios/${id}/cancelar/`, { motivo }).then((r) => r.data);
export const marcarEstudioMicrobiologiaInformado = (id: number) =>
  apiClient.post<EstudioMicrobiologia>(`${MICRO}/estudios/${id}/marcar-informado/`, {}).then((r) => r.data);

// --- Siembras ---
export const listSiembrasMicrobiologia = (params?: { estudio_id?: number }) =>
  getPaginatedAll<SiembraMicrobiologia>(`${MICRO}/siembras/`, { page_size: 500, ...params });
export const createSiembraMicrobiologia = (body: {
  estudio_id: number;
  medio_id: number;
  fecha_siembra?: string | null;
  condicion_incubacion?: string;
  temperatura_c?: number | string | null;
  atmosfera?: string;
  observaciones?: string;
}) => apiClient.post<SiembraMicrobiologia>(`${MICRO}/siembras/`, body).then((r) => r.data);
export const updateSiembraMicrobiologia = (
  id: number,
  body: Partial<Pick<SiembraMicrobiologia, 'condicion_incubacion' | 'temperatura_c' | 'atmosfera' | 'observaciones'>>
) => apiClient.patch<SiembraMicrobiologia>(`${MICRO}/siembras/${id}/`, body).then((r) => r.data);

// --- Lecturas ---
export const listLecturasCultivo = (params?: { estudio_id?: number }) =>
  getPaginatedAll<LecturaCultivo>(`${MICRO}/lecturas/`, { page_size: 500, ...params });
export const createLecturaCultivo = (body: {
  siembra_id: number;
  fecha_lectura?: string | null;
  horas_incubacion?: number | null;
  crecimiento?: string;
  descripcion_colonias?: string;
  tincion_gram?: string;
  observaciones?: string;
  es_preliminar?: boolean;
}) => apiClient.post<LecturaCultivo>(`${MICRO}/lecturas/`, body).then((r) => r.data);
export const updateLecturaCultivo = (
  id: number,
  body: Partial<
    Pick<
      LecturaCultivo,
      'horas_incubacion' | 'crecimiento' | 'descripcion_colonias' | 'tincion_gram' | 'observaciones' | 'es_preliminar'
    >
  >
) => apiClient.patch<LecturaCultivo>(`${MICRO}/lecturas/${id}/`, body).then((r) => r.data);

// --- Microorganismos ---
export const listMicroorganismos = (params?: { search?: string }) =>
  getPaginatedAll<Microorganismo>(`${MICRO}/microorganismos/`, { page_size: 500, ...params });
export const createMicroorganismo = (body: Partial<Microorganismo>) =>
  apiClient.post<Microorganismo>(`${MICRO}/microorganismos/`, body).then((r) => r.data);
export const updateMicroorganismo = (id: number, body: Partial<Microorganismo>) =>
  apiClient.patch<Microorganismo>(`${MICRO}/microorganismos/${id}/`, body).then((r) => r.data);

// --- Aislados ---
export const listAisladosMicrobiologicos = (params?: { estudio_id?: number }) =>
  getPaginatedAll<AisladoMicrobiologico>(`${MICRO}/aislados/`, { page_size: 500, ...params });
export const createAisladoMicrobiologico = (body: {
  estudio_id: number;
  lectura_id: number;
  microorganismo_id?: number | null;
  descripcion?: string;
  cantidad?: string;
  significancia?: string;
  requiere_antibiograma?: boolean;
  observaciones?: string;
}) => apiClient.post<AisladoMicrobiologico>(`${MICRO}/aislados/`, body).then((r) => r.data);
export const updateAisladoMicrobiologico = (
  id: number,
  body: Partial<
    Pick<AisladoMicrobiologico, 'descripcion' | 'cantidad' | 'significancia' | 'requiere_antibiograma' | 'observaciones'>
  >
) => apiClient.patch<AisladoMicrobiologico>(`${MICRO}/aislados/${id}/`, body).then((r) => r.data);
export const descartarAisladoMicrobiologico = (id: number, motivo: string) =>
  apiClient.post<AisladoMicrobiologico>(`${MICRO}/aislados/${id}/descartar/`, { motivo }).then((r) => r.data);

// --- Identificaciones ---
export const listIdentificacionesMicroorganismo = (params?: { estudio_id?: number }) =>
  getPaginatedAll<IdentificacionMicroorganismo>(`${MICRO}/identificaciones/`, {
    page_size: 500,
    ...params,
  });
export const getIdentificacionMicroorganismo = (id: number) =>
  apiClient.get<IdentificacionMicroorganismo>(`${MICRO}/identificaciones/${id}/`).then((r) => r.data);
export const createIdentificacionMicroorganismo = (body: {
  aislado_id: number;
  microorganismo_id: number;
  metodo?: string;
  resultado?: string;
  confianza?: number | string | null;
  fecha?: string | null;
  observaciones?: string;
}) => apiClient.post<IdentificacionMicroorganismo>(`${MICRO}/identificaciones/`, body).then((r) => r.data);

// --- Antibióticos ---
export const listAntibioticos = (params?: { search?: string }) =>
  getPaginatedAll<Antibiotico>(`${MICRO}/antibioticos/`, { page_size: 500, ...params });
export const createAntibiotico = (body: Partial<Antibiotico>) =>
  apiClient.post<Antibiotico>(`${MICRO}/antibioticos/`, body).then((r) => r.data);
export const updateAntibiotico = (id: number, body: Partial<Antibiotico>) =>
  apiClient.patch<Antibiotico>(`${MICRO}/antibioticos/${id}/`, body).then((r) => r.data);

// --- Antibiogramas ---
export const listAntibiogramas = (params?: { estudio_id?: number }) =>
  getPaginatedAll<Antibiograma>(`${MICRO}/antibiogramas/`, { page_size: 500, ...params });
export const createAntibiograma = (body: {
  aislado_id: number;
  metodo?: string;
  fecha_inicio?: string | null;
  observaciones?: string;
}) => apiClient.post<Antibiograma>(`${MICRO}/antibiogramas/`, body).then((r) => r.data);
export const updateAntibiograma = (id: number, body: { metodo?: string; observaciones?: string }) =>
  apiClient.patch<Antibiograma>(`${MICRO}/antibiogramas/${id}/`, body).then((r) => r.data);
export const completarAntibiograma = (id: number) =>
  apiClient.post<Antibiograma>(`${MICRO}/antibiogramas/${id}/completar/`, {}).then((r) => r.data);
export const cancelarAntibiograma = (id: number, motivo: string) =>
  apiClient.post<Antibiograma>(`${MICRO}/antibiogramas/${id}/cancelar/`, { motivo }).then((r) => r.data);

// --- Resultados antibiótico ---
export const listResultadosAntibiotico = (params?: { estudio_id?: number }) =>
  getPaginatedAll<ResultadoAntibiotico>(`${MICRO}/resultados-antibiotico/`, {
    page_size: 1000,
    ...params,
  });
export const createResultadoAntibiotico = (body: {
  antibiograma_id: number;
  antibiotico_id: number;
  halo_mm?: number | string | null;
  mic?: string;
  interpretacion: string;
  observaciones?: string;
}) => apiClient.post<ResultadoAntibiotico>(`${MICRO}/resultados-antibiotico/`, body).then((r) => r.data);
export const updateResultadoAntibiotico = (
  id: number,
  body: Partial<Pick<ResultadoAntibiotico, 'halo_mm' | 'mic' | 'interpretacion' | 'observaciones'>>
) => apiClient.patch<ResultadoAntibiotico>(`${MICRO}/resultados-antibiotico/${id}/`, body).then((r) => r.data);

// --- Informes ---
export const listInformesMicrobiologia = (params?: { estudio_id?: number }) =>
  getPaginatedAll<InformeMicrobiologia>(`${MICRO}/informes/`, { page_size: 500, ...params });
export const createInformeMicrobiologia = (body: {
  estudio_id: number;
  tipo: 'PRELIMINAR' | 'FINAL';
  texto?: string;
  observaciones?: string;
  reemplaza_a_id?: number | null;
}) => apiClient.post<InformeMicrobiologia>(`${MICRO}/informes/`, body).then((r) => r.data);
export const updateInformeMicrobiologia = (
  id: number,
  body: { texto?: string; observaciones?: string; version?: number }
) => apiClient.patch<InformeMicrobiologia>(`${MICRO}/informes/${id}/`, body).then((r) => r.data);
export const emitirInformeMicrobiologia = (id: number, body: { texto?: string } = {}) =>
  apiClient.post<InformeMicrobiologia>(`${MICRO}/informes/${id}/emitir/`, body).then((r) => r.data);
export const validarInformeMicrobiologia = (id: number) =>
  apiClient.post<InformeMicrobiologia>(`${MICRO}/informes/${id}/validar/`, {}).then((r) => r.data);
export const anularInformeMicrobiologia = (id: number, motivo: string) =>
  apiClient.post<InformeMicrobiologia>(`${MICRO}/informes/${id}/anular/`, { motivo }).then((r) => r.data);

export async function downloadInformeMicroPdf(estudioId: number): Promise<void> {
  const { data } = await apiClient.get(`${MICRO}/estudios/${estudioId}/informe-pdf/`, {
    responseType: 'blob',
    timeout: 60_000,
  });
  await triggerBlobDownload(data as Blob, informeMicroPdfFilename(estudioId));
}

export async function postEnviarInformeMicro(
  estudioId: number,
  body: {
    email?: boolean;
    whatsapp?: boolean;
    email_medico?: boolean;
    whatsapp_medico?: boolean;
  }
): Promise<EnviarInformeMicroResponse> {
  const { data } = await apiClient.post<EnviarInformeMicroResponse>(
    `${MICRO}/estudios/${estudioId}/enviar-informe/`,
    body,
    { timeout: 45_000 }
  );
  return data;
}
