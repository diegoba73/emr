import type { User } from '../types';
import {
  canAccessArchivosMedicos,
  canAccessAtenciones,
  canAccessAuditoria,
  canAccessPacientes,
  canAccessSolicitudes,
  canCreatePaciente,
  canDownloadArchivoMedico,
  canWriteArchivoMedico,
  canAccessLims,
  canValidateLims,
  canAccessMicrobiologia,
  canValidateMicrobiologia,
  canOperateAtenciones,
} from './permissions';

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

describe('canAccessPacientes', () => {
  it('permite roles clínicos/administrativos y paciente', () => {
    expect(canAccessPacientes(user({ rol: 'ADMIN' }))).toBe(true);
    expect(canAccessPacientes(user({ rol: 'SECRETARIA' }))).toBe(true);
    expect(canAccessPacientes(user({ rol: 'ENFERMERIA' }))).toBe(true);
    expect(canAccessPacientes(user({ rol: 'MEDICO' }))).toBe(true);
    expect(canAccessPacientes(user({ rol: 'PACIENTE' }))).toBe(true);
  });

  it('bloquea laboratorio y sin rol', () => {
    expect(canAccessPacientes(user({ rol: 'LABORATORIO' }))).toBe(false);
    expect(canAccessPacientes(null)).toBe(false);
  });

  it('permite staff aunque rol no sea admin', () => {
    expect(canAccessPacientes(user({ rol: 'MEDICO', is_staff: true }))).toBe(true);
  });
});

describe('canCreatePaciente', () => {
  it('permite admin, secretaría, enfermería y médico', () => {
    expect(canCreatePaciente(user({ rol: 'ADMIN' }))).toBe(true);
    expect(canCreatePaciente(user({ rol: 'SECRETARIA' }))).toBe(true);
    expect(canCreatePaciente(user({ rol: 'ENFERMERIA' }))).toBe(true);
    expect(canCreatePaciente(user({ rol: 'MEDICO' }))).toBe(true);
  });

  it('no permite paciente ni laboratorio', () => {
    expect(canCreatePaciente(user({ rol: 'PACIENTE' }))).toBe(false);
    expect(canCreatePaciente(user({ rol: 'LABORATORIO' }))).toBe(false);
  });
});

describe('canAccessSolicitudes', () => {
  it('permite admin, secretaría, médico y paciente', () => {
    expect(canAccessSolicitudes(user({ rol: 'ADMIN' }))).toBe(true);
    expect(canAccessSolicitudes(user({ rol: 'SECRETARIA' }))).toBe(true);
    expect(canAccessSolicitudes(user({ rol: 'MEDICO' }))).toBe(true);
    expect(canAccessSolicitudes(user({ rol: 'PACIENTE' }))).toBe(true);
  });

  it('bloquea enfermería, laboratorio y anónimo', () => {
    expect(canAccessSolicitudes(user({ rol: 'ENFERMERIA' }))).toBe(false);
    expect(canAccessSolicitudes(user({ rol: 'LABORATORIO' }))).toBe(false);
    expect(canAccessSolicitudes(null)).toBe(false);
  });
});

describe('canAccessArchivosMedicos', () => {
  it('permite admin, médico y paciente', () => {
    expect(canAccessArchivosMedicos(user({ rol: 'ADMIN' }))).toBe(true);
    expect(canAccessArchivosMedicos(user({ rol: 'MEDICO' }))).toBe(true);
    expect(canAccessArchivosMedicos(user({ rol: 'PACIENTE' }))).toBe(true);
  });

  it('bloquea secretaría, enfermería y laboratorio', () => {
    expect(canAccessArchivosMedicos(user({ rol: 'SECRETARIA' }))).toBe(false);
    expect(canAccessArchivosMedicos(user({ rol: 'ENFERMERIA' }))).toBe(false);
    expect(canAccessArchivosMedicos(user({ rol: 'LABORATORIO' }))).toBe(false);
  });
});

describe('canWriteArchivoMedico / canDownloadArchivoMedico', () => {
  it('escritura solo admin, médico y paciente', () => {
    expect(canWriteArchivoMedico(user({ rol: 'SECRETARIA' }))).toBe(false);
    expect(canWriteArchivoMedico(user({ rol: 'MEDICO' }))).toBe(true);
    expect(canDownloadArchivoMedico(user({ rol: 'MEDICO' }))).toBe(true);
  });
});

describe('LIMS permissions (re-export)', () => {
  const lab = user({ rol: 'LABORATORIO' });
  const med = user({ rol: 'MEDICO' });
  const pac = user({ rol: 'PACIENTE' });
  const sec = user({ rol: 'SECRETARIA' });
  const enf = user({ rol: 'ENFERMERIA' });
  const adm = user({ rol: 'ADMIN', is_superuser: true });

  it('LIMS rutas: admin/laboratorio/médico', () => {
    expect(canAccessLims(adm)).toBe(true);
    expect(canAccessLims(lab)).toBe(true);
    expect(canAccessLims(med)).toBe(true);
    expect(canAccessLims(pac)).toBe(false);
    expect(canAccessLims(sec)).toBe(false);
    expect(canAccessLims(enf)).toBe(false);
  });

  it('validar LIMS solo admin/superuser', () => {
    expect(canValidateLims(adm)).toBe(true);
    expect(canValidateLims(lab)).toBe(false);
    expect(canValidateLims(med)).toBe(false);
  });

  it('microbiología alinea con LIMS lectura', () => {
    expect(canAccessMicrobiologia(lab)).toBe(true);
    expect(canAccessMicrobiologia(pac)).toBe(false);
    expect(canValidateMicrobiologia(lab)).toBe(false);
    expect(canValidateMicrobiologia(adm)).toBe(true);
  });
});

describe('canAccessAuditoria', () => {
  it('permite superuser, staff y rol admin', () => {
    expect(canAccessAuditoria(user({ rol: 'ADMIN', is_superuser: true }))).toBe(true);
    expect(canAccessAuditoria(user({ rol: 'MEDICO', is_staff: true }))).toBe(true);
    expect(canAccessAuditoria(user({ rol: 'ADMIN' }))).toBe(true);
  });

  it('bloquea médico y laboratorio sin staff', () => {
    expect(canAccessAuditoria(user({ rol: 'MEDICO' }))).toBe(false);
    expect(canAccessAuditoria(user({ rol: 'LABORATORIO' }))).toBe(false);
  });
});

describe('canAccessAtenciones / canOperateAtenciones (QA-ROLE-01)', () => {
  it('permite admin, médico, enfermería y paciente', () => {
    expect(canAccessAtenciones(user({ rol: 'ADMIN' }))).toBe(true);
    expect(canAccessAtenciones(user({ rol: 'MEDICO' }))).toBe(true);
    expect(canAccessAtenciones(user({ rol: 'ENFERMERIA' }))).toBe(true);
    expect(canAccessAtenciones(user({ rol: 'PACIENTE' }))).toBe(true);
  });

  it('bloquea secretaría, laboratorio y anónimo', () => {
    expect(canAccessAtenciones(user({ rol: 'SECRETARIA' }))).toBe(false);
    expect(canAccessAtenciones(user({ rol: 'LABORATORIO' }))).toBe(false);
    expect(canAccessAtenciones(null)).toBe(false);
  });

  it('operación solo admin/staff y médico', () => {
    expect(canOperateAtenciones(user({ rol: 'MEDICO' }))).toBe(true);
    expect(canOperateAtenciones(user({ rol: 'ENFERMERIA' }))).toBe(false);
    expect(canOperateAtenciones(user({ rol: 'PACIENTE' }))).toBe(false);
    expect(canOperateAtenciones(user({ rol: 'SECRETARIA' }))).toBe(false);
  });
});
