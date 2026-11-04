import { api } from './apiService';

export type EstadoProblemaClinico = 'ACTIVO' | 'RESUELTO';

export interface ProblemaClinico {
  id: number;
  texto: string;
  diagnostico_cie_id?: number | null;
  diagnostico_cie_codigo?: string | null;
  diagnostico_cie_descripcion?: string | null;
  display: string;
  estado: EstadoProblemaClinico;
  es_principal: boolean;
  notas: string;
  creado_en?: string;
  actualizado_en?: string;
  resuelto_en?: string | null;
}

export async function listProblemasClinicos(
  pacienteId: number,
  params?: { estado?: EstadoProblemaClinico }
): Promise<ProblemaClinico[]> {
  const { data } = await api.get<ProblemaClinico[]>(
    `/pacientes/${pacienteId}/problemas-clinicos/`,
    { params }
  );
  return data;
}

export async function createProblemaClinico(
  pacienteId: number,
  body: {
    texto: string;
    diagnostico_cie_id?: number | null;
    es_principal?: boolean;
    notas?: string;
  }
): Promise<ProblemaClinico> {
  const { data } = await api.post<ProblemaClinico>(
    `/pacientes/${pacienteId}/problemas-clinicos/crear/`,
    body
  );
  return data;
}

/** Crea o actualiza el principal vigente (sin acumular problemas). */
export async function establecerProblemaPrincipal(
  pacienteId: number,
  body: {
    texto: string;
    diagnostico_cie_id?: number | null;
    notas?: string;
  }
): Promise<ProblemaClinico> {
  const { data } = await api.post<ProblemaClinico>(
    `/pacientes/${pacienteId}/problemas-clinicos/establecer-principal/`,
    body
  );
  return data;
}

export async function updateProblemaClinico(
  pacienteId: number,
  problemaId: number,
  body: Partial<{
    texto: string;
    diagnostico_cie_id: number | null;
    es_principal: boolean;
    estado: EstadoProblemaClinico;
    notas: string;
  }>
): Promise<ProblemaClinico> {
  const { data } = await api.patch<ProblemaClinico>(
    `/pacientes/${pacienteId}/problemas-clinicos/${problemaId}/`,
    body
  );
  return data;
}

export async function resolverProblemaClinico(
  pacienteId: number,
  problemaId: number
): Promise<ProblemaClinico> {
  const { data } = await api.post<ProblemaClinico>(
    `/pacientes/${pacienteId}/problemas-clinicos/${problemaId}/resolver/`
  );
  return data;
}
