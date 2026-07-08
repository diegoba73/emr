import type { Turno } from '../types';
import { isTurnoEstudio } from './recursosEstudio';

/** Tipos de turno visibles en la agenda institucional. */
export type TurnoAgendaKind = 'consulta' | 'estudio' | 'procedimiento' | 'cirugia';

export interface TurnoKindMeta {
  label: string;
  shortLabel: string;
  /** Color fijo en calendario (si no usa color por estado). */
  calendarColor?: string;
  /** Si true, el calendario usa el color del estado (RESERVADO, CONFIRMADO, …). */
  useEstadoColor?: boolean;
}

export const TURNO_KIND_META: Record<TurnoAgendaKind, TurnoKindMeta> = {
  consulta: {
    label: 'Consulta médica',
    shortLabel: 'Consulta',
    useEstadoColor: true,
  },
  estudio: {
    label: 'Estudio complementario',
    shortLabel: 'Estudio',
    useEstadoColor: true,
  },
  procedimiento: {
    label: 'Procedimiento / sala',
    shortLabel: 'Proced.',
    useEstadoColor: true,
  },
  cirugia: {
    label: 'Cirugía',
    shortLabel: 'Cirugía',
    useEstadoColor: true,
  },
};

type TurnoKindInput = Pick<Turno, 'estudio_complementario' | 'recurso' | 'motivo_reserva' | 'medico'>;

export function getTurnoAgendaKind(turno: TurnoKindInput): TurnoAgendaKind {
  if (isTurnoEstudio(turno)) return 'estudio';
  const tipo = turno.recurso?.tipo_recurso;
  if (tipo === 'CONSULTORIO') return 'consulta';
  if (tipo === 'QUIROFANO') return 'cirugia';
  if (tipo === 'SALA_PROCEDIMIENTO' || tipo === 'SALA_HEMODINAMIA') return 'procedimiento';
  return 'consulta';
}

export function getTurnoKindMeta(turno: TurnoKindInput): TurnoKindMeta {
  return TURNO_KIND_META[getTurnoAgendaKind(turno)];
}

export function formatTurnoCalendarTitle(
  turno: TurnoKindInput & {
    paciente?: { nombre?: string; apellido?: string } | null;
    medico?: { nombre?: string; apellido?: string } | null;
    motivo_reserva?: string;
  }
): string {
  const kind = getTurnoAgendaKind(turno);
  const meta = TURNO_KIND_META[kind];
  const pacienteNombre = turno.paciente
    ? turno.paciente.apellido
      ? `${turno.paciente.apellido}, ${turno.paciente.nombre || ''}`.trim()
      : turno.paciente.nombre || 'Sin nombre'
    : null;

  if (kind === 'estudio' && pacienteNombre) {
    const estudioLabel =
      turno.estudio_complementario?.tipo_estudio_nombre ||
      turno.motivo_reserva?.replace(/^Estudio:\s*/i, '') ||
      'Estudio';
    const sala = turno.recurso?.nombre ? ` · ${turno.recurso.nombre}` : '';
    return `${meta.shortLabel}: ${pacienteNombre} — ${estudioLabel}${sala}`;
  }

  if (pacienteNombre && turno.medico) {
    const medicoNombre = turno.medico.apellido
      ? `Dr. ${turno.medico.apellido}`
      : turno.medico.nombre
        ? `Dr. ${turno.medico.nombre}`
        : 'Sin médico';
    return `${meta.shortLabel}: ${pacienteNombre} (${medicoNombre})`;
  }

  if (pacienteNombre) {
    return `${meta.shortLabel}: ${pacienteNombre}`;
  }

  if (turno.medico) {
    const medicoNombre = turno.medico.apellido
      ? `Dr. ${turno.medico.apellido}`
      : turno.medico.nombre
        ? `Dr. ${turno.medico.nombre}`
        : 'Sin médico';
    return `${meta.shortLabel}: Disponible (${medicoNombre})`;
  }

  return meta.shortLabel;
}
