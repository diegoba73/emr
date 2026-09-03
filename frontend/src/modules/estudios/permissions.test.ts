import { canAccessEstudiosModule } from './permissions';
import type { User } from '../../types';

const user = (partial: Partial<User>): User =>
  ({
    id: 1,
    username: 'u',
    email: 'u@test.com',
    first_name: '',
    last_name: '',
    rol: 'MEDICO',
    is_staff: false,
    is_superuser: false,
    ...partial,
  }) as User;

describe('canAccessEstudiosModule', () => {
  it('permite médico, secretaría, enfermería, paciente y admin', () => {
    expect(canAccessEstudiosModule(user({ rol: 'MEDICO' }))).toBe(true);
    expect(canAccessEstudiosModule(user({ rol: 'SECRETARIA' }))).toBe(true);
    expect(canAccessEstudiosModule(user({ rol: 'ENFERMERIA' }))).toBe(true);
    expect(canAccessEstudiosModule(user({ rol: 'PACIENTE' }))).toBe(true);
    expect(canAccessEstudiosModule(user({ rol: 'ADMIN' }))).toBe(true);
  });

  it('bloquea laboratorio y bioquímico (usan LIMS)', () => {
    expect(canAccessEstudiosModule(user({ rol: 'LABORATORIO' }))).toBe(false);
    expect(canAccessEstudiosModule(user({ rol: 'BIOQUIMICO' }))).toBe(false);
    expect(canAccessEstudiosModule(user({ rol: 'BIOQUIMICO', is_staff: true }))).toBe(false);
    expect(canAccessEstudiosModule(null)).toBe(false);
  });
});
