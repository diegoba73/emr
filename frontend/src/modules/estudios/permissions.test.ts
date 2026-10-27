import { canAccessEstudiosModule, canDownloadPdfInformeEstudio, canEnviarInformeEstudio } from './permissions';
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
  it('permite médico, secretaría institucional, enfermería, paciente y admin', () => {
    expect(canAccessEstudiosModule(user({ rol: 'MEDICO' }))).toBe(true);
    expect(canAccessEstudiosModule(user({ rol: 'SECRETARIA' }))).toBe(true);
    expect(canAccessEstudiosModule(user({ rol: 'ENFERMERIA' }))).toBe(true);
    expect(canAccessEstudiosModule(user({ rol: 'PACIENTE' }))).toBe(true);
    expect(canAccessEstudiosModule(user({ rol: 'ADMIN' }))).toBe(true);
  });

  it('bloquea secretaría laboratorio, laboratorio y bioquímico', () => {
    expect(canAccessEstudiosModule(user({ rol: 'SECRETARIA_LAB' }))).toBe(false);
    expect(canAccessEstudiosModule(user({ rol: 'LABORATORIO' }))).toBe(false);
    expect(canAccessEstudiosModule(user({ rol: 'BIOQUIMICO' }))).toBe(false);
    expect(canAccessEstudiosModule(user({ rol: 'BIOQUIMICO', is_staff: true }))).toBe(false);
    expect(canAccessEstudiosModule(null)).toBe(false);
  });
});


it('administrador puede descargar un informe borrador para revisión', () => {
  expect(canDownloadPdfInformeEstudio(
    user({ rol: 'ADMIN' }),
    { estado: 'REALIZADO' } as any,
    { estado: 'BORRADOR', es_vigente: true } as any
  )).toBe(true);
});


it('secretaría institucional opera el módulo: descarga/envío de informe validado vigente', () => {
  const secretaria = user({ rol: 'SECRETARIA' });
  for (const estado of ['VALIDADO', 'ENTREGADO', 'INFORMADO']) {
    const estudio = { estado } as any;
    const validado = { estado: 'VALIDADO', es_vigente: true } as any;
    expect(canDownloadPdfInformeEstudio(secretaria, estudio, validado)).toBe(true);
  }
  const validado = { estado: 'VALIDADO', es_vigente: true } as any;
  expect(canEnviarInformeEstudio(secretaria, { estado: 'VALIDADO' } as any, validado)).toBe(true);
  expect(canEnviarInformeEstudio(secretaria, { estado: 'ENTREGADO' } as any, validado)).toBe(true);
  expect(canEnviarInformeEstudio(secretaria, { estado: 'VALIDADO' } as any, { ...validado, es_vigente: false })).toBe(false);
  expect(canEnviarInformeEstudio(secretaria, { estado: 'VALIDADO' } as any, { ...validado, estado: 'BORRADOR' })).toBe(false);
  expect(canEnviarInformeEstudio(secretaria, { estado: 'INFORMADO' } as any, validado)).toBe(false);
});
