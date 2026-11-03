import type { Turno } from '../types';
import type { EstudioComplementario } from '../types/estudios';
import { getTurnoAgendaKind } from './turnoKind';
import { formatPacienteNombre } from './pacienteFormat';

export type ProgramacionTipoFiltro =
  | ''
  | 'CONSULTA'
  | 'ESTUDIO'
  | 'PROCEDIMIENTO'
  | 'CIRUGIA';

export type ProgramacionRowKind = 'CONSULTA' | 'ESTUDIO' | 'PROCEDIMIENTO' | 'CIRUGIA';

export interface ProgramacionRow {
  key: string;
  kind: ProgramacionRowKind;
  pacienteNombre: string;
  medicoNombre: string;
  prestacion: string;
  fechaInicio: string | null;
  estadoLabel: string;
  estudioId?: number;
  turnoId?: number;
}

function labelMedicoTurno(t: Turno): string {
  const m = t.medico;
  if (!m) return '—';
  const ap = (m.apellido || '').trim();
  const no = (m.nombre || '').trim();
  if (ap && no) return `${ap}, ${no}`;
  return ap || no || '—';
}

function kindFromTurno(t: Turno): ProgramacionRowKind {
  const ec = t.estudio_complementario as
    | { tipo_actividad?: string; practica?: string; tipo_estudio_nombre?: string | null }
    | null
    | undefined;
  if (ec?.tipo_actividad === 'PROCEDIMIENTO') return 'PROCEDIMIENTO';
  if (ec?.tipo_actividad === 'CIRUGIA') return 'CIRUGIA';
  if (ec?.tipo_actividad === 'ESTUDIO' || ec) return 'ESTUDIO';
  const agenda = getTurnoAgendaKind(t);
  if (agenda === 'cirugia') return 'CIRUGIA';
  if (agenda === 'procedimiento') return 'PROCEDIMIENTO';
  if (agenda === 'estudio') return 'ESTUDIO';
  return 'CONSULTA';
}

function prestacionFromTurno(t: Turno): string {
  const ec = t.estudio_complementario as
    | {
        tipo_estudio_nombre?: string | null;
        practica?: string;
        procedimiento_catalogo_nombre?: string | null;
      }
    | null
    | undefined;
  if (ec?.tipo_estudio_nombre) return ec.tipo_estudio_nombre;
  if (ec?.procedimiento_catalogo_nombre) return ec.procedimiento_catalogo_nombre;
  if (ec?.practica) return ec.practica;
  return t.motivo_reserva || t.motivo_consulta || 'Consulta médica';
}

export function rowFromTurno(t: Turno): ProgramacionRow {
  const kind = kindFromTurno(t);
  const pac = t.paciente
    ? formatPacienteNombre(t.paciente) || '—'
    : '—';
  return {
    key: `t-${t.id}`,
    kind,
    pacienteNombre: pac,
    medicoNombre: labelMedicoTurno(t),
    prestacion: prestacionFromTurno(t),
    fechaInicio: t.fecha_hora_inicio || null,
    estadoLabel: t.estado || '—',
    estudioId: t.estudio_complementario?.id,
    turnoId: t.id,
  };
}

function kindFromEstudio(e: EstudioComplementario): ProgramacionRowKind {
  if (e.tipo_actividad === 'PROCEDIMIENTO') return 'PROCEDIMIENTO';
  if (e.tipo_actividad === 'CIRUGIA') return 'CIRUGIA';
  return 'ESTUDIO';
}

function prestacionFromEstudio(e: EstudioComplementario): string {
  if (e.tipo_actividad === 'CIRUGIA') {
    const parts = [
      e.cirugia_especialidad_snapshot || e.cirugia_especialidad_nombre,
      e.cirugia_procedimiento_snapshot || e.cirugia_procedimiento_nombre,
    ].filter(Boolean);
    return parts.join(' · ') || 'Cirugía';
  }
  if (e.tipo_actividad === 'PROCEDIMIENTO') {
    return e.procedimiento_catalogo_nombre || 'Procedimiento';
  }
  return e.tipo_estudio_nombre || e.practica || 'Estudio';
}

export function rowFromEstudio(e: EstudioComplementario): ProgramacionRow {
  return {
    key: `e-${e.id}`,
    kind: kindFromEstudio(e),
    pacienteNombre: e.paciente_nombre || `Paciente #${e.paciente_id}`,
    medicoNombre: e.medico_solicitante_nombre || '—',
    prestacion: prestacionFromEstudio(e),
    fechaInicio: e.turno_fecha_hora_inicio || e.fecha_solicitud || null,
    estadoLabel: e.estado || '—',
    estudioId: e.id,
    turnoId: e.turno_id || undefined,
  };
}

export function kindLabel(kind: ProgramacionRowKind): string {
  switch (kind) {
    case 'CONSULTA':
      return 'Consulta médica';
    case 'PROCEDIMIENTO':
      return 'Procedimiento';
    case 'CIRUGIA':
      return 'Cirugía';
    default:
      return 'Estudio';
  }
}

/** Une turnos (consultas) + estudios sin duplicar estudios ya vinculados a un turno. */
export function mergeProgramacionRows(
  turnos: Turno[],
  estudios: EstudioComplementario[],
  filtroTipo: ProgramacionTipoFiltro
): ProgramacionRow[] {
  const estudioIdsEnTurnos = new Set<number>();
  const rows: ProgramacionRow[] = [];

  for (const t of turnos) {
    const row = rowFromTurno(t);
    if (filtroTipo && row.kind !== filtroTipo) continue;
    if (row.estudioId) estudioIdsEnTurnos.add(row.estudioId);
    rows.push(row);
  }

  for (const e of estudios) {
    if (e.turno_id && estudioIdsEnTurnos.has(e.id)) continue;
    // Si ya hay turno en la lista, el estudio se representó vía turno
    if (e.turno_id && turnos.some((t) => t.id === e.turno_id)) continue;
    const row = rowFromEstudio(e);
    if (filtroTipo === 'CONSULTA') continue;
    if (filtroTipo && row.kind !== filtroTipo) continue;
    rows.push(row);
  }

  rows.sort((a, b) => {
    const ta = a.fechaInicio ? new Date(a.fechaInicio).getTime() : 0;
    const tb = b.fechaInicio ? new Date(b.fechaInicio).getTime() : 0;
    return tb - ta;
  });
  return rows;
}

export function fechaLocalHoy(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
