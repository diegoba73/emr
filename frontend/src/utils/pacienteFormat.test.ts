import { formatPacienteObraSocial } from './pacienteFormat';
import type { Paciente } from '../types';

function pac(partial: Partial<Paciente>): Paciente {
  return {
    id: 1,
    nombre: 'Ana',
    apellido: 'Pérez',
    dni: '123',
    fecha_nacimiento: '1990-01-01',
    created_at: '',
    updated_at: '',
    ...partial,
  } as Paciente;
}

describe('formatPacienteObraSocial', () => {
  it('combina obra social y afiliado', () => {
    expect(
      formatPacienteObraSocial(pac({ obra_social: 'OSDE', numero_afiliado: '99' }))
    ).toBe('OSDE · Afiliado 99');
  });

  it('obra social sola', () => {
    expect(formatPacienteObraSocial(pac({ obra_social: 'PAMI' }))).toBe('PAMI');
  });

  it('vacío si no hay datos', () => {
    expect(formatPacienteObraSocial(pac({}))).toBe('');
    expect(formatPacienteObraSocial(null)).toBe('');
  });
});
