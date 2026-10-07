import { api } from './apiService';
import type { PacienteAfiliacion } from '../types';

export async function listPacienteAfiliaciones(
  pacienteId: number
): Promise<PacienteAfiliacion[]> {
  const { data } = await api.get<PacienteAfiliacion[]>(
    `/pacientes/${pacienteId}/afiliaciones/`
  );
  return data;
}

export async function createPacienteAfiliacion(
  pacienteId: number,
  body: {
    obra_social: string;
    numero_afiliado?: string;
    es_principal?: boolean;
  }
): Promise<PacienteAfiliacion> {
  const { data } = await api.post<PacienteAfiliacion>(
    `/pacientes/${pacienteId}/afiliaciones/crear/`,
    body
  );
  return data;
}

export async function updatePacienteAfiliacion(
  pacienteId: number,
  afiliacionId: number,
  body: Partial<{
    obra_social: string;
    numero_afiliado: string;
    es_principal: boolean;
    activo: boolean;
  }>
): Promise<PacienteAfiliacion> {
  const { data } = await api.patch<PacienteAfiliacion>(
    `/pacientes/${pacienteId}/afiliaciones/${afiliacionId}/`,
    body
  );
  return data;
}

export async function deletePacienteAfiliacion(
  pacienteId: number,
  afiliacionId: number
): Promise<void> {
  await api.delete(`/pacientes/${pacienteId}/afiliaciones/${afiliacionId}/eliminar/`);
}
