import type { Turno } from '../types';
import { apiClient } from './apiClient';
export type TipoAgenda = 'CONSULTA' | 'ESTUDIO';
export interface HorarioMedico {
  id: number; medico: number; dia_semana: number; hora_inicio: string; hora_fin: string;
  tipo: TipoAgenda; recurso: number | null; activo: boolean; duracion_slot_min: number;
}
export interface SlotMedico { horario_id: number; inicio: string; fin: string; duracion_min: number; tipo: TipoAgenda }
export const getHorarios = async (): Promise<HorarioMedico[]> => {
  let url: string | null = '/disponibilidades/';
  const rows: HorarioMedico[] = [];
  while (url) {
    const { data }: { data: any } = await apiClient.get(url);
    rows.push(...(Array.isArray(data) ? data : data.results));
    // El paginador puede retornar URL absoluta detrás del proxy.
    url = data.next ? `/disponibilidades/?${String(data.next).split('?')[1]}` : null;
  }
  return rows;
};
export const saveHorario = async (horario: Omit<HorarioMedico, 'id'>) => (await apiClient.post('/disponibilidades/', horario)).data;
export const updateHorario = async (id: number, horario: Omit<HorarioMedico, 'id'>) => (await apiClient.patch(`/disponibilidades/${id}/`, horario)).data;
export const deleteHorario = async (id: number) => apiClient.delete(`/disponibilidades/${id}/`);
export const getSlotsMedico = async (medico: number, fecha: string, tipo: TipoAgenda): Promise<SlotMedico[]> =>
  (await apiClient.get(`/medicos/${medico}/slots/`, { params: { fecha, tipo } })).data.slots;
export const reservarHorario = async (slot: SlotMedico, motivo: string) =>
  (await apiClient.post('/turnos/reservar-horario/', { horario_id: slot.horario_id, inicio: slot.inicio, motivo })).data;

export const getMisTurnos = async (): Promise<Turno[]> => {
  let url: string | null = '/turnos/';
  const rows: Turno[] = [];
  while (url) {
    const { data }: { data: any } = await apiClient.get(url);
    rows.push(...(Array.isArray(data) ? data : data.results));
    url = data.next ? `/turnos/?${String(data.next).split('?')[1]}` : null;
  }
  return rows;
};
