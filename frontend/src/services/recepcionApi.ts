import { apiClient as api } from './apiClient';
import { resolveApiBaseUrl } from './apiBaseUrl';
import type {
  CoberturaHoyPayload,
  CoberturaRecepcion,
  EsperaPacienteEstado,
  KioscoCheckinResult,
  KioscoConfig,
  LlegadaRecepcion,
  PantallaLlamadoItem,
  PantallaSalaPayload,
  PuestoRecepcion,
  ReglaRuteoRecepcion,
  TableroRecepcion,
} from '../types/recepcion';

export const listPuestosRecepcion = async (): Promise<PuestoRecepcion[]> => {
  const { data } = await api.get('/recepcion/puestos/', { params: { page_size: 100 } });
  return Array.isArray(data) ? data : data.results || [];
};

export const savePuestoRecepcion = async (
  payload: Partial<PuestoRecepcion> & { codigo: string; nombre: string },
  id?: number
): Promise<PuestoRecepcion> => {
  if (id) {
    const { data } = await api.patch(`/recepcion/puestos/${id}/`, payload);
    return data;
  }
  const { data } = await api.post('/recepcion/puestos/', payload);
  return data;
};

export const listReglasRecepcion = async (): Promise<ReglaRuteoRecepcion[]> => {
  const { data } = await api.get('/recepcion/reglas/', { params: { page_size: 200 } });
  return Array.isArray(data) ? data : data.results || [];
};

export const saveReglaRecepcion = async (
  payload: Partial<ReglaRuteoRecepcion> & { puesto: number },
  id?: number
): Promise<ReglaRuteoRecepcion> => {
  if (id) {
    const { data } = await api.patch(`/recepcion/reglas/${id}/`, payload);
    return data;
  }
  const { data } = await api.post('/recepcion/reglas/', payload);
  return data;
};

export const deleteReglaRecepcion = async (id: number): Promise<void> => {
  await api.delete(`/recepcion/reglas/${id}/`);
};

export const getTableroRecepcion = async (
  fecha?: string,
  puesto?: number | null
): Promise<TableroRecepcion> => {
  const params: Record<string, string | number> = {};
  if (fecha) params.fecha = fecha;
  if (puesto) params.puesto = puesto;
  const { data } = await api.get('/recepcion/llegadas/tablero/', { params });
  return data;
};

export const checkinTurnoRecepcion = async (
  turnoId: number,
  puestoId?: number | null
): Promise<LlegadaRecepcion> => {
  const { data } = await api.post('/recepcion/llegadas/checkin-turno/', {
    turno_id: turnoId,
    ...(puestoId ? { puesto_id: puestoId } : {}),
  });
  return data;
};

export const checkinWalkinRecepcion = async (payload: {
  paciente_id: number;
  tipo_actividad?: string;
  puesto_id?: number;
  notas?: string;
}): Promise<LlegadaRecepcion> => {
  const { data } = await api.post('/recepcion/llegadas/checkin-walkin/', payload);
  return data;
};

export const accionLlegada = async (
  id: number,
  accion: 'llamar' | 'derivar-espera' | 'en-atencion' | 'atendido' | 'no-asistio',
  body?: Record<string, unknown>
): Promise<LlegadaRecepcion> => {
  const { data } = await api.post(`/recepcion/llegadas/${id}/${accion}/`, body || {});
  return data;
};

/** Tras guardar/cerrar consulta: marca la llegada del turno como ATENDIDO. */
export const marcarAtendidoPorTurno = async (
  turnoId: number
): Promise<{ ok: boolean; actualizado: boolean }> => {
  const { data } = await api.post('/recepcion/llegadas/atendido-por-turno/', {
    turno_id: turnoId,
  });
  return data;
};

export const moverPuestoLlegada = async (
  id: number,
  puestoId: number
): Promise<LlegadaRecepcion> => {
  const { data } = await api.post(`/recepcion/llegadas/${id}/mover-puesto/`, {
    puesto_id: puestoId,
  });
  return data;
};

export const getPantallaLlamados = async (): Promise<PantallaLlamadoItem[]> => {
  const { data } = await api.get('/recepcion/pantalla-llamados/');
  return data.llamados || [];
};

export const getPantallaSala = async (): Promise<PantallaSalaPayload> => {
  const { data } = await api.get('/recepcion/pantalla-llamados/');
  const empty = {
    actual: null,
    llamando: [],
    otros_llamando: [],
    proximo: null,
    historial: [],
    pendientes: [],
  };
  return {
    mitad_recepcion: data.mitad_recepcion || empty,
    mitad_medico: data.mitad_medico || empty,
    llamados: data.llamados || [],
  };
};

export const kioscoCheckin = async (
  dni: string,
  apellido: string,
  tipoActividad: string
): Promise<KioscoCheckinResult> => {
  const { data } = await api.post('/recepcion/kiosco-checkin/', {
    dni,
    apellido,
    tipo_actividad: tipoActividad,
  });
  return data;
};

export const getKioscoConfig = async (): Promise<KioscoConfig> => {
  const { data } = await api.get('/recepcion/kiosco-config/');
  return data;
};

export const getCoberturaHoy = async (): Promise<CoberturaHoyPayload> => {
  const { data } = await api.get('/recepcion/cobertura-hoy/');
  return data;
};

export const putCoberturaHoy = async (payload: {
  puesto: number;
  tipos: string[];
  sede?: string | null;
}): Promise<CoberturaRecepcion> => {
  const { data } = await api.put('/recepcion/cobertura-hoy/', payload);
  return data;
};

export const getEsperaPaciente = async (token: string): Promise<EsperaPacienteEstado> => {
  const base = resolveApiBaseUrl().replace(/\/$/, '');
  const url = `${base}/recepcion/espera/${encodeURIComponent(token)}/`;
  const res = await fetch(url, { credentials: 'omit' });
  if (!res.ok) {
    throw new Error(`espera_http_${res.status}`);
  }
  return (await res.json()) as EsperaPacienteEstado;
};

export const postEsperaYaVoy = async (token: string): Promise<{ ok: boolean; estado_flujo: string }> => {
  const base = resolveApiBaseUrl().replace(/\/$/, '');
  const url = `${base}/recepcion/espera/${encodeURIComponent(token)}/ya-voy/`;
  const res = await fetch(url, {
    method: 'POST',
    credentials: 'omit',
    headers: { 'Content-Type': 'application/json' },
    body: '{}',
  });
  if (!res.ok) {
    throw new Error(`ya_voy_http_${res.status}`);
  }
  return (await res.json()) as { ok: boolean; estado_flujo: string };
};
