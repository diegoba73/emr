import type { User } from '../types';
import {
  getAppSegmentTitle,
  getHomeNavLabel,
  getSolicitudesModuleLabel,
  isPacienteRole,
} from './navLabels';

function user(rol: User['rol']): User {
  return {
    id: 1,
    username: 'u',
    email: 'u@test.com',
    first_name: 'U',
    last_name: 'T',
    is_active: true,
    is_superuser: false,
    is_staff: false,
    rol,
  };
}

describe('navLabels', () => {
  it('home siempre es Inicio', () => {
    expect(getHomeNavLabel()).toBe('Inicio');
  });

  it('paciente ve Análisis Clínico en solicitudes', () => {
    expect(getSolicitudesModuleLabel(user('PACIENTE'))).toBe('Análisis Clínico');
    expect(getSolicitudesModuleLabel(user('MEDICO'))).toBe('Laboratorio');
  });

  it('títulos de segmento adaptados para paciente', () => {
    expect(getAppSegmentTitle('/dashboard', user('PACIENTE'))).toBe('Inicio');
    expect(getAppSegmentTitle('/solicitudes', user('PACIENTE'))).toBe('Análisis Clínico');
    expect(getAppSegmentTitle('/atenciones', user('PACIENTE'))).toBe('Mis consultas');
    expect(getAppSegmentTitle('/solicitudes', user('MEDICO'))).toBe('Laboratorio');
  });

  it('isPacienteRole', () => {
    expect(isPacienteRole(user('PACIENTE'))).toBe(true);
    expect(isPacienteRole(user('MEDICO'))).toBe(false);
  });
});
