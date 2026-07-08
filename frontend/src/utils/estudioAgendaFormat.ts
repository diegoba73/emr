import type { Paciente } from '../types';
import type { EstudioComplementario } from '../types/estudios';

export function pacienteLabelFromList(
  pacienteId: number,
  pacientes: Paciente[]
): string {
  const p = pacientes.find((x) => x.id === pacienteId);
  if (!p) return `Pac. #${pacienteId}`;
  const nombre = `${p.apellido || ''}, ${p.nombre || ''}`.trim();
  return nombre || `Pac. #${pacienteId}`;
}

export function formatEstudioAgendaOption(
  estudio: EstudioComplementario,
  pacientes: Paciente[]
): string {
  const pac = pacienteLabelFromList(estudio.paciente_id, pacientes);
  return `#${estudio.id} · ${estudio.tipo_estudio_nombre || 'Estudio'} · ${pac}`;
}
