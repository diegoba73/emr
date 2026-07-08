import type { Turno, User } from '../types';
import {
  canEditTurno,
  medicoEsDuenoTurno,
  pacientePuedeMutarTurno,
} from './turnoPermissions';

function user(overrides: Partial<User> & Pick<User, 'rol'>): User {
  return {
    id: 1,
    username: 'u',
    email: 'u@test.com',
    first_name: 'U',
    last_name: 'Test',
    is_active: true,
    is_superuser: false,
    is_staff: false,
    ...overrides,
  };
}

function turno(overrides: Partial<Turno> = {}): Turno {
  return {
    id: 1,
    fecha_hora_inicio: '2026-07-10T10:00:00',
    estado: 'RESERVADO',
    ...overrides,
  };
}

describe('medicoEsDuenoTurno', () => {
  const medicoUser = user({ rol: 'MEDICO', medico: { id: 10 } as User['medico'] });

  it('true si el médico está asignado al turno de consulta', () => {
    expect(
      medicoEsDuenoTurno(
        medicoUser,
        turno({ medico_id: 10, medico: { id: 10 } as Turno['medico'] }),
      ),
    ).toBe(true);
  });

  it('true si es médico solicitante del estudio sin médico en turno', () => {
    expect(
      medicoEsDuenoTurno(
        medicoUser,
        turno({
          medico_id: undefined,
          recurso: { tipo_recurso: 'SALA_PROCEDIMIENTO' } as Turno['recurso'],
          motivo_reserva: 'Estudio: RX',
          estudio_complementario: { id: 5, estado: 'CONFIRMADO', medico_solicitante_id: 10 },
        }),
      ),
    ).toBe(true);
  });

  it('true para turno de estudio sin médico (vínculo validado en backend)', () => {
    expect(
      medicoEsDuenoTurno(
        medicoUser,
        turno({
          recurso: { tipo_recurso: 'SALA_PROCEDIMIENTO' } as Turno['recurso'],
          motivo_reserva: 'Estudio: Eco',
          estudio_complementario: { id: 6, estado: 'CONFIRMADO' },
        }),
      ),
    ).toBe(true);
  });

  it('false para turno de otro médico', () => {
    expect(
      medicoEsDuenoTurno(
        medicoUser,
        turno({ medico_id: 99, medico: { id: 99 } as Turno['medico'] }),
      ),
    ).toBe(false);
  });
});

describe('pacientePuedeMutarTurno', () => {
  const pacienteUser = user({ rol: 'PACIENTE', paciente: { id: 20 } as User['paciente'] });

  it('permite editar turno propio activo', () => {
    expect(
      pacientePuedeMutarTurno(
        pacienteUser,
        turno({ paciente_id: 20, estado: 'RESERVADO' }),
      ),
    ).toBe(true);
  });

  it('bloquea turno REALIZADO', () => {
    expect(
      pacientePuedeMutarTurno(
        pacienteUser,
        turno({ paciente_id: 20, estado: 'REALIZADO' }),
      ),
    ).toBe(false);
  });

  it('bloquea turno CANCELADO', () => {
    expect(
      pacientePuedeMutarTurno(
        pacienteUser,
        turno({ paciente_id: 20, estado: 'CANCELADO' }),
      ),
    ).toBe(false);
  });

  it('bloquea si hay atención clínica iniciada', () => {
    expect(
      pacientePuedeMutarTurno(
        pacienteUser,
        turno({
          paciente_id: 20,
          estado: 'CONFIRMADO',
          atencion: {
            id: 1,
            fecha_admision: '2026-07-10T09:00:00',
            tipo_atencion: 'CONSULTORIO',
          },
        }),
      ),
    ).toBe(false);
  });
});

describe('canEditTurno — médico y estudio', () => {
  const medicoUser = user({ rol: 'MEDICO', medico: { id: 10 } as User['medico'] });

  it('permite editar turno de estudio donde es solicitante', () => {
    expect(
      canEditTurno(
        medicoUser,
        turno({
          recurso: { tipo_recurso: 'SALA_PROCEDIMIENTO' } as Turno['recurso'],
          motivo_reserva: 'Estudio: RX',
          estudio_complementario: { id: 1, estado: 'CONFIRMADO', medico_solicitante_id: 10 },
        }),
      ),
    ).toBe(true);
  });

  it('deniega turno de consulta ajeno', () => {
    expect(
      canEditTurno(
        medicoUser,
        turno({ medico_id: 99, medico: { id: 99 } as Turno['medico'] }),
      ),
    ).toBe(false);
  });
});
