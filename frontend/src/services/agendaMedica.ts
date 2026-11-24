import type { Turno } from '../types';
import { apiClient } from './apiClient';
export type TipoAgenda = 'CONSULTA' | 'ESTUDIO';
export interface HorarioMedico {
  id: number; medico: number; dia_semana: number; hora_inicio: string; hora_fin: string;
  tipo: TipoAgenda; recurso: number | null; activo: boolean; duracion_slot_min: number;
}
export interface SlotMedico {
  horario_id: number;
  inicio: string;
  fin: string;
  duracion_min: number;
  tipo: TipoAgenda;
  recurso_id?: number | null;
  recurso_nombre?: string | null;
}
export interface DiaDisponible {
  fecha: string;
  cantidad_slots: number;
}
export interface DiaSemanaConfig {
  dia_semana: number;
  activo: boolean;
  hora_inicio?: string | null;
  hora_fin?: string | null;
  recurso?: number | null;
}
export interface ConfigurarSemanaPayload {
  medico: number;
  tipo: TipoAgenda;
  duracion_slot_min?: number;
  dias: DiaSemanaConfig[];
}
export interface ConfigurarSemanaResult {
  medico: number;
  tipo: TipoAgenda;
  duracion_slot_min: number;
  horarios: HorarioMedico[];
}
export const getHorarios = async (params?: {
  medico?: number;
  tipo?: TipoAgenda;
  activo?: boolean;
}): Promise<HorarioMedico[]> => {
  const query = new URLSearchParams();
  if (params?.medico != null) query.set('medico', String(params.medico));
  if (params?.tipo) query.set('tipo', params.tipo);
  if (params?.activo != null) query.set('activo', params.activo ? 'true' : 'false');
  const qs = query.toString();
  let url: string | null = qs ? `/disponibilidades/?${qs}` : '/disponibilidades/';
  const rows: HorarioMedico[] = [];
  while (url) {
    const response = await apiClient.get<HorarioMedico[] | { results: HorarioMedico[]; next?: string | null }>(
      url
    );
    const data = response.data;
    rows.push(...(Array.isArray(data) ? data : data.results));
    // El paginador puede retornar URL absoluta detrás del proxy.
    const nextRaw = Array.isArray(data) ? null : data.next;
    const nextQs: string = nextRaw ? String(nextRaw).split('?')[1] || '' : '';
    url = nextQs ? `/disponibilidades/?${nextQs}` : null;
  }
  return rows;
};
export const saveHorario = async (horario: Omit<HorarioMedico, 'id'>) => (await apiClient.post('/disponibilidades/', horario)).data;
export const updateHorario = async (id: number, horario: Omit<HorarioMedico, 'id'>) => (await apiClient.patch(`/disponibilidades/${id}/`, horario)).data;
export const deleteHorario = async (id: number) => apiClient.delete(`/disponibilidades/${id}/`);
export const configurarSemana = async (payload: ConfigurarSemanaPayload): Promise<ConfigurarSemanaResult> =>
  (await apiClient.post('/disponibilidades/configurar-semana/', payload)).data;
export const getSlotsMedico = async (
  medico: number,
  fecha: string,
  tipo: TipoAgenda,
  opts?: { tipo_estudio?: number },
): Promise<SlotMedico[]> =>
  (
    await apiClient.get(`/medicos/${medico}/slots/`, {
      params: { fecha, tipo, ...(opts?.tipo_estudio ? { tipo_estudio: opts.tipo_estudio } : {}) },
    })
  ).data.slots;

/** Slots de reprogramación resueltos desde el turno (médico/tipo/salas del servidor). */
export const getSlotsReprogramacionTurno = async (
  turnoId: number,
  fecha: string,
): Promise<{ slots: SlotMedico[]; detail?: string | null; tipo_estudio_id?: number | null }> => {
  const { data } = await apiClient.get(`/turnos/${turnoId}/slots-reprogramacion/`, {
    params: { fecha },
  });
  return {
    slots: data.slots || [],
    detail: data.detail || null,
    tipo_estudio_id: data.tipo_estudio_id ?? null,
  };
};
export const getDiasDisponibles = async (
  medico: number,
  desde: string,
  hasta: string,
  tipo: TipoAgenda,
): Promise<DiaDisponible[]> =>
  (await apiClient.get(`/medicos/${medico}/dias-disponibles/`, { params: { desde, hasta, tipo } })).data.dias;
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

export interface TurnoAfectadoFeriado {
  id: number;
  estado: string;
  fecha_hora_inicio: string | null;
  paciente_id: number | null;
  paciente_nombre: string | null;
  medico_id: number | null;
  medico_nombre: string | null;
}

export interface Feriado {
  id: number;
  fecha: string;
  nombre: string;
  activo: boolean;
  creado_en?: string;
  actualizado_en?: string;
  pendientes_count: number;
  turnos_afectados?: TurnoAfectadoFeriado[];
}

export interface TurnosPendientesFeriado {
  feriado_id: number;
  fecha: string;
  nombre: string;
  activo: boolean;
  turnos: TurnoAfectadoFeriado[];
  count: number;
}

export const getFeriados = async (): Promise<Feriado[]> => {
  let url: string | null = '/feriados/';
  const rows: Feriado[] = [];
  while (url) {
    const { data }: { data: any } = await apiClient.get(url);
    rows.push(...(Array.isArray(data) ? data : data.results));
    url = data.next ? `/feriados/?${String(data.next).split('?')[1]}` : null;
  }
  return rows;
};

export const createFeriado = async (payload: {
  fecha: string;
  nombre: string;
  activo?: boolean;
}): Promise<Feriado> => (await apiClient.post('/feriados/', payload)).data;

export const updateFeriado = async (
  id: number,
  payload: Partial<Pick<Feriado, 'fecha' | 'nombre' | 'activo'>>,
): Promise<Feriado> => (await apiClient.patch(`/feriados/${id}/`, payload)).data;

export const deleteFeriado = async (id: number) => apiClient.delete(`/feriados/${id}/`);

export const getTurnosPendientesFeriado = async (id: number): Promise<TurnosPendientesFeriado> =>
  (await apiClient.get(`/feriados/${id}/turnos-pendientes/`)).data;

export type MotivoLicencia =
  | 'LICENCIA_MEDICA'
  | 'CONGRESO'
  | 'ESTUDIO'
  | 'PERSONAL'
  | 'OTRO';

export const MOTIVO_LICENCIA_OPTIONS: { value: MotivoLicencia; label: string }[] = [
  { value: 'LICENCIA_MEDICA', label: 'Licencia médica' },
  { value: 'CONGRESO', label: 'Congreso' },
  { value: 'ESTUDIO', label: 'Estudio' },
  { value: 'PERSONAL', label: 'Asuntos personales' },
  { value: 'OTRO', label: 'Otro' },
];

export interface LicenciaMedico {
  id: number;
  medico: number;
  medico_nombre?: string | null;
  fecha_inicio: string;
  fecha_fin: string;
  motivo: MotivoLicencia;
  motivo_display?: string;
  detalle: string;
  activo: boolean;
  creado_en?: string;
  actualizado_en?: string;
  pendientes_count: number;
  turnos_afectados?: TurnoAfectadoFeriado[];
}

export interface TurnosPendientesLicencia {
  licencia_id: number;
  medico_id: number;
  fecha_inicio: string;
  fecha_fin: string;
  motivo: string;
  activo: boolean;
  turnos: TurnoAfectadoFeriado[];
  count: number;
}

export const getLicenciasMedico = async (medicoId?: number): Promise<LicenciaMedico[]> => {
  let url: string | null = medicoId
    ? `/licencias-medico/?medico=${medicoId}`
    : '/licencias-medico/';
  const rows: LicenciaMedico[] = [];
  while (url) {
    const { data }: { data: any } = await apiClient.get(url);
    rows.push(...(Array.isArray(data) ? data : data.results));
    url = data.next ? `/licencias-medico/?${String(data.next).split('?')[1]}` : null;
  }
  return rows;
};

export const createLicenciaMedico = async (payload: {
  medico: number;
  fecha_inicio: string;
  fecha_fin: string;
  motivo: MotivoLicencia;
  detalle?: string;
  activo?: boolean;
}): Promise<LicenciaMedico> => (await apiClient.post('/licencias-medico/', payload)).data;

export const updateLicenciaMedico = async (
  id: number,
  payload: Partial<{
    fecha_inicio: string;
    fecha_fin: string;
    motivo: MotivoLicencia;
    detalle: string;
    activo: boolean;
  }>,
): Promise<LicenciaMedico> => (await apiClient.patch(`/licencias-medico/${id}/`, payload)).data;

export const deleteLicenciaMedico = async (id: number) =>
  apiClient.delete(`/licencias-medico/${id}/`);

export const getTurnosPendientesLicencia = async (id: number): Promise<TurnosPendientesLicencia> =>
  (await apiClient.get(`/licencias-medico/${id}/turnos-pendientes/`)).data;
