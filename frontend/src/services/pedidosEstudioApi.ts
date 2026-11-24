import { apiClient } from './apiClient';

export type PedidoEstudioEstado = 'PENDIENTE' | 'AGENDADO' | 'CANCELADO';
export type PedidoEstudioCanal = 'MOVIL' | 'PORTAL';

export interface PedidoEstudioPaciente {
  id: number;
  paciente: number;
  paciente_nombre: string;
  estado: PedidoEstudioEstado;
  origen_canal: PedidoEstudioCanal;
  notas: string;
  turno: number | null;
  estudio: number | null;
  foto_nombre: string | null;
  download_foto_url: string | null;
  created_at: string;
  agendado_en: string | null;
}

export interface MedicoTipoEstudioRow {
  id: number;
  medico: number;
  medico_nombre: string;
  tipo_estudio: number;
  tipo_estudio_nombre: string;
}

export interface TipoEstudioSalaRow {
  id: number;
  tipo_estudio: number;
  tipo_estudio_nombre: string;
  recurso: number;
  recurso_nombre: string;
}

const BASE = '/estudios-complementarios';

function pages<T>(data: T[] | { results: T[] }): T[] {
  return Array.isArray(data) ? data : data.results || [];
}

export async function listPedidosEstudio(params?: {
  estado?: PedidoEstudioEstado;
}): Promise<PedidoEstudioPaciente[]> {
  const { data } = await apiClient.get(`${BASE}/pedidos/`, { params });
  return pages(data);
}

/** Deshabilitado: estudios solo los agenda secretaría (presencial / teléfono). */
export async function createPedidoEstudioPaciente(_payload: {
  foto: File;
  notas?: string;
  origen_canal?: PedidoEstudioCanal;
}): Promise<PedidoEstudioPaciente> {
  throw Object.assign(
    new Error(
      'Los turnos de estudio solo los agenda secretaría (presencial o por teléfono).'
    ),
    { response: { status: 403, data: { detail: 'Los turnos de estudio solo los agenda secretaría.' } } }
  );
}

export async function agendarPedidoEstudio(
  id: number,
  payload: {
    tipo_estudio: number;
    medico_id: number;
    inicio: string;
    horario_id?: number;
  }
): Promise<PedidoEstudioPaciente> {
  const { data } = await apiClient.post(`${BASE}/pedidos/${id}/agendar/`, payload);
  return data;
}

export function pedidoFotoDownloadPath(id: number): string {
  return `${BASE}/pedidos/${id}/download-foto/`;
}

export async function listMedicoTipos(medicoId?: number): Promise<MedicoTipoEstudioRow[]> {
  const { data } = await apiClient.get(`${BASE}/medico-tipos/`, {
    params: medicoId ? { medico: medicoId } : undefined,
  });
  return pages(data);
}

export async function createMedicoTipo(medico: number, tipo_estudio: number): Promise<MedicoTipoEstudioRow> {
  const { data } = await apiClient.post(`${BASE}/medico-tipos/`, { medico, tipo_estudio });
  return data;
}

export async function deleteMedicoTipo(id: number): Promise<void> {
  await apiClient.delete(`${BASE}/medico-tipos/${id}/`);
}

export async function listTipoSalas(tipoEstudioId?: number): Promise<TipoEstudioSalaRow[]> {
  const { data } = await apiClient.get(`${BASE}/tipo-salas/`, {
    params: tipoEstudioId ? { tipo_estudio: tipoEstudioId } : undefined,
  });
  return pages(data);
}

export async function createTipoSala(tipo_estudio: number, recurso: number): Promise<TipoEstudioSalaRow> {
  const { data } = await apiClient.post(`${BASE}/tipo-salas/`, { tipo_estudio, recurso });
  return data;
}

export async function deleteTipoSala(id: number): Promise<void> {
  await apiClient.delete(`${BASE}/tipo-salas/${id}/`);
}
