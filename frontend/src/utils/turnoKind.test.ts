import { estudioNombreDeTurno, formatTurnoCalendarTitle } from './turnoKind';
import type { Turno } from '../types';

describe('estudioNombreDeTurno', () => {
  it('prioriza tipo_estudio_nombre del estudio vinculado', () => {
    const turno = {
      motivo_reserva: 'Estudio: Otro',
      estudio_complementario: {
        id: 1,
        estado: 'CONFIRMADO',
        tipo_estudio_nombre: 'RX Tórax',
      },
      recurso: { id: 1, nombre: 'Sala 1', tipo_recurso: 'SALA_PROCEDIMIENTO' },
    } as Turno;
    expect(estudioNombreDeTurno(turno)).toBe('RX Tórax');
  });

  it('usa motivo_reserva si no hay tipo en el nested', () => {
    const turno = {
      motivo_reserva: 'Estudio: Eco abdominal',
      estudio_complementario: { id: 2, estado: 'CONFIRMADO' },
      recurso: { id: 1, nombre: 'Sala 1', tipo_recurso: 'SALA_PROCEDIMIENTO' },
    } as Turno;
    expect(estudioNombreDeTurno(turno)).toBe('Eco abdominal');
  });

  it('aparece en el título del calendario', () => {
    const turno = {
      motivo_reserva: 'Estudio: Mamografía',
      paciente: { nombre: 'Ana', apellido: 'Pérez' },
      estudio_complementario: {
        id: 3,
        estado: 'CONFIRMADO',
        tipo_actividad: 'ESTUDIO',
        tipo_estudio_nombre: 'Mamografía',
      },
      recurso: { id: 1, nombre: 'Sala A', tipo_recurso: 'SALA_PROCEDIMIENTO' },
    } as Turno;
    expect(formatTurnoCalendarTitle(turno)).toContain('Mamografía');
  });
});
