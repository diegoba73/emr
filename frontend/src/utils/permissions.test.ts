import type { User } from '../types';
import {
  canAccessArchivosMedicos,
  canAccessAtenciones,
  canAccessAuditoria,
  canAccessPacientes,
  canAccessPaciente360,
  canAccessSolicitudes,
  canCreatePaciente,
  canDownloadArchivoMedico,
  canWriteArchivoMedico,
  canAccessLims,
  canValidateLims,
  canAccessMicrobiologia,
  canValidateMicrobiologia,
  canOperateAtenciones,
  isEmrStaffOrAdmin,
  isLaboratorioRole,
} from './permissions';
import { canViewTurnosAgenda, canMutateTurnosGlobally } from './turnoPermissions';

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
  it('permite roles clínicos/administrativos y médico en listado', () => {
    expect(canAccessPacientes(user({ rol: 'ADMIN' }))).toBe(true);
    expect(canAccessPacientes(user({ rol: 'SECRETARIA' }))).toBe(true);
    expect(canAccessPacientes(user({ rol: 'ENFERMERIA' }))).toBe(true);
    expect(canAccessPacientes(user({ rol: 'MEDICO' }))).toBe(true);
  });

  it('no permite paciente en listado /pacientes', () => {
    expect(canAccessPacientes(user({ rol: 'PACIENTE' }))).toBe(false);
  });

  it('permite paciente en vista 360 propia', () => {
    expect(canAccessPaciente360(user({ rol: 'PACIENTE' }))).toBe(true);
  });

  it('permite laboratorio y profesionales de estudio en listado operativo', () => {
    expect(canAccessPacientes(user({ rol: 'LABORATORIO' }))).toBe(true);
    expect(canAccessPacientes(user({ rol: 'RADIOLOGO' }))).toBe(true);
    expect(canAccessPacientes(user({ rol: 'KINESIOLOGO' }))).toBe(true);
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
  it('escritura solo admin y médico; paciente solo descarga', () => {
    expect(canWriteArchivoMedico(user({ rol: 'SECRETARIA' }))).toBe(false);
    expect(canWriteArchivoMedico(user({ rol: 'MEDICO' }))).toBe(true);
    expect(canWriteArchivoMedico(user({ rol: 'PACIENTE' }))).toBe(false);
    expect(canDownloadArchivoMedico(user({ rol: 'PACIENTE' }))).toBe(true);
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

  it('finalizar LIMS admin y laboratorio', () => {
    expect(canValidateLims(adm)).toBe(true);
    expect(canValidateLims(lab)).toBe(true);
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
    expect(canOperateAtenciones(user({ is_staff: true, rol: 'ENFERMERIA' }))).toBe(true);
    expect(canOperateAtenciones(user({ is_superuser: true, rol: 'PACIENTE' }))).toBe(true);
  });
});

/** laboratorio1 seed: rol LABORATORIO + is_staff (PERM-FE-LAB-01 / QA-SMOKE-02 N1). */
describe('laboratorio + is_staff — sin bypass EMR', () => {
  const labStaff = user({ rol: 'LABORATORIO', is_staff: true });

  it('identifica rol laboratorio', () => {
    expect(isLaboratorioRole(labStaff)).toBe(true);
    expect(isEmrStaffOrAdmin(labStaff)).toBe(false);
  });

  it('lectura operativa de pacientes y turnos; sin módulos clínicos EMR', () => {
    expect(canAccessPacientes(labStaff)).toBe(true);
    expect(canViewTurnosAgenda(labStaff)).toBe(true);
    expect(canMutateTurnosGlobally(labStaff)).toBe(false);
    expect(canAccessAtenciones(labStaff)).toBe(false);
    expect(canOperateAtenciones(labStaff)).toBe(false);
    expect(canAccessAuditoria(labStaff)).toBe(false);
    expect(canCreatePaciente(labStaff)).toBe(false);
    expect(canAccessSolicitudes(labStaff)).toBe(false);
    expect(canAccessArchivosMedicos(labStaff)).toBe(false);
  });

  it('conserva acceso LIMS', () => {
    expect(canAccessLims(labStaff)).toBe(true);
    expect(canAccessMicrobiologia(labStaff)).toBe(true);
    expect(canValidateLims(labStaff)).toBe(true);
    expect(canValidateMicrobiologia(labStaff)).toBe(false);
  });

  it('staff no laboratorio sigue con bypass EMR', () => {
    const enfStaff = user({ rol: 'ENFERMERIA', is_staff: true });
    expect(isEmrStaffOrAdmin(enfStaff)).toBe(true);
    expect(canAccessPacientes(enfStaff)).toBe(true);
    expect(canAccessAtenciones(enfStaff)).toBe(true);
    expect(canAccessAuditoria(enfStaff)).toBe(true);
  });
});
