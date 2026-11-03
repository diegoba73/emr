import { mergeProgramacionRows, rowFromTurno, kindLabel } from './programacionTurnosRows';
import type { Turno } from '../types';
import type { EstudioComplementario } from '../types/estudios';

describe('programacionTurnosRows', () => {
  it('clasifica consulta y estudio desde turno', () => {
    const consulta = rowFromTurno({
      id: 1,
      fecha_hora_inicio: '2026-10-20T10:00:00',
      estado: 'CONFIRMADO',
      recurso: { id: 1, nombre: 'C1', tipo_recurso: 'CONSULTORIO' },
      paciente: { id: 1, nombre: 'Ana', apellido: 'Lopez' },
      medico: { id: 2, nombre: 'Juan', apellido: 'Perez' },
    } as Turno);
    expect(consulta.kind).toBe('CONSULTA');
    expect(kindLabel(consulta.kind)).toBe('Consulta médica');

    const estudio = rowFromTurno({
      id: 2,
      fecha_hora_inicio: '2026-10-20T11:00:00',
      estado: 'CONFIRMADO',
      estudio_complementario: {
        id: 9,
        estado: 'CONFIRMADO',
        tipo_actividad: 'ESTUDIO',
        tipo_estudio_nombre: 'Eco',
      },
      paciente: { id: 1, nombre: 'Ana', apellido: 'Lopez' },
    } as Turno);
    expect(estudio.kind).toBe('ESTUDIO');
  });

  it('merge evita duplicar estudio ya vinculado a turno', () => {
    const turnos = [
      {
        id: 5,
        fecha_hora_inicio: '2026-10-20T09:00:00',
        estado: 'CONFIRMADO',
        estudio_complementario: { id: 99, estado: 'CONFIRMADO', tipo_actividad: 'ESTUDIO' },
        paciente: { id: 1, nombre: 'A', apellido: 'B' },
      } as Turno,
    ];
    const estudios = [
      {
        id: 99,
        paciente_id: 1,
        estado: 'CONFIRMADO',
        tipo_actividad: 'ESTUDIO',
        turno_id: 5,
        turno_fecha_hora_inicio: '2026-10-20T09:00:00',
      } as EstudioComplementario,
    ];
    const rows = mergeProgramacionRows(turnos, estudios, '');
    expect(rows).toHaveLength(1);
    expect(rows[0].estudioId).toBe(99);
  });

  it('filtro CONSULTA excluye estudios sueltos', () => {
    const rows = mergeProgramacionRows(
      [],
      [
        {
          id: 1,
          paciente_id: 1,
          estado: 'SOLICITADO',
          tipo_actividad: 'ESTUDIO',
        } as EstudioComplementario,
      ],
      'CONSULTA'
    );
    expect(rows).toHaveLength(0);
  });
});
