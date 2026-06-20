import {
  ESTADOS_MICRO_CERRADOS,
  canAccessMicrobiologia,
  canDownloadInformeLimsPdf,
  canMarcarMicroEstudioInformado,
  canOperateMicrobiologia,
  canOperateMicroEstudioTecnico,
  isMicroEstudioCerrado,
} from './limsAccess';
import type { User } from '../types';

const labUser: User = {
  id: 1,
  username: 'lab',
  email: 'lab@test.com',
  first_name: 'Lab',
  last_name: 'User',
  rol: 'LABORATORIO',
  is_active: true,
  is_superuser: false,
};

describe('isMicroEstudioCerrado', () => {
  it.each(['CANCELADO', 'VALIDADO', 'INFORMADO'] as const)(
    'returns true for %s',
    (estado) => {
      expect(isMicroEstudioCerrado(estado)).toBe(true);
    }
  );

  it('returns false for EN_PROCESO-like open states', () => {
    expect(isMicroEstudioCerrado('EN_PROCESO')).toBe(false);
    expect(isMicroEstudioCerrado('SEMBRADO')).toBe(false);
    expect(isMicroEstudioCerrado('LISTO_PARA_VALIDAR')).toBe(false);
  });

  it('exports closed states constant', () => {
    expect(ESTADOS_MICRO_CERRADOS).toEqual(['CANCELADO', 'VALIDADO', 'INFORMADO']);
  });
});

describe('canOperateMicroEstudioTecnico', () => {
  it('blocks lab user on closed study', () => {
    expect(canOperateMicroEstudioTecnico(labUser, 'VALIDADO')).toBe(false);
  });

  it('allows lab user on open study', () => {
    expect(canOperateMicroEstudioTecnico(labUser, 'SEMBRADO')).toBe(true);
  });
});

describe('canMarcarMicroEstudioInformado', () => {
  it('allows marcar informado only from VALIDADO', () => {
    expect(canMarcarMicroEstudioInformado(labUser, 'VALIDADO')).toBe(true);
    expect(canMarcarMicroEstudioInformado(labUser, 'INFORMADO')).toBe(false);
    expect(canMarcarMicroEstudioInformado(labUser, 'SEMBRADO')).toBe(false);
  });
});

const medUser: User = { ...labUser, id: 2, username: 'med', rol: 'MEDICO' };
const pacUser: User = { ...labUser, id: 3, username: 'pac', rol: 'PACIENTE' };

describe('micro LIMS role matrix', () => {
  it('lab can access and operate open study', () => {
    expect(canAccessMicrobiologia(labUser)).toBe(true);
    expect(canOperateMicrobiologia(labUser)).toBe(true);
    expect(canOperateMicroEstudioTecnico(labUser, 'SEMBRADO')).toBe(true);
  });

  it('medico can access but not operate', () => {
    expect(canAccessMicrobiologia(medUser)).toBe(true);
    expect(canOperateMicrobiologia(medUser)).toBe(false);
    expect(canOperateMicroEstudioTecnico(medUser, 'SEMBRADO')).toBe(false);
  });

  it('paciente cannot access micro', () => {
    expect(canAccessMicrobiologia(pacUser)).toBe(false);
    expect(canOperateMicrobiologia(pacUser)).toBe(false);
  });
});

const adminUser: User = { ...labUser, id: 10, username: 'admin', rol: 'ADMIN', is_superuser: true };
const secUser: User = { ...labUser, id: 11, username: 'sec', rol: 'SECRETARIA' };
const enfUser: User = { ...labUser, id: 12, username: 'enf', rol: 'ENFERMERIA' };

describe('canDownloadInformeLimsPdf', () => {
  it('admin y laboratorio pueden descargar', () => {
    expect(canDownloadInformeLimsPdf(adminUser)).toBe(true);
    expect(canDownloadInformeLimsPdf(labUser)).toBe(true);
  });

  it('médico puede descargar si accede al módulo', () => {
    expect(canDownloadInformeLimsPdf(medUser)).toBe(true);
  });

  it('paciente, secretaría y enfermería no', () => {
    expect(canDownloadInformeLimsPdf(pacUser)).toBe(false);
    expect(canDownloadInformeLimsPdf(secUser)).toBe(false);
    expect(canDownloadInformeLimsPdf(enfUser)).toBe(false);
    expect(canDownloadInformeLimsPdf(null)).toBe(false);
  });
});
