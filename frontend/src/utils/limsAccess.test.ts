import {
  ESTADOS_MICRO_CERRADOS,
  canAccessMicrobiologia,
  canAccessMicrobiologiaLectura,
  canDownloadInformeClinicoPdf,
  canDownloadInformeLimsPdf,
  canDownloadInformeMicroPdf,
  canEnviarInformeLims,
  canEnviarInformeMicro,
  canMarcarMicroEstudioInformado,
  canOperateInformeMicro,
  canOperateMicrobiologia,
  canOperateMicroEstudioTecnico,
  canSeeInformeMicro,
  canSeeResultadosClinicos,
  canValidarOrdenLims,
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

const bioUser: User = {
  ...labUser,
  id: 20,
  username: 'bio',
  rol: 'BIOQUIMICO',
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

  it('medico cannot access LIMS/micro (usa portal /solicitudes)', () => {
    expect(canAccessMicrobiologia(medUser)).toBe(false);
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

describe('canDownloadInformeLimsPdf / canEnviarInformeLims', () => {
  it('admin, laboratorio y bioquímico solo tras FINALIZADO', () => {
    expect(canDownloadInformeLimsPdf(adminUser, 'LISTO_PARA_VALIDAR')).toBe(false);
    expect(canDownloadInformeLimsPdf(labUser, 'EN_PROCESO')).toBe(false);
    expect(canDownloadInformeLimsPdf(bioUser, 'INFORMADO_PARCIAL')).toBe(false);
    expect(canDownloadInformeLimsPdf(adminUser, 'FINALIZADO')).toBe(true);
    expect(canDownloadInformeLimsPdf(labUser, 'FINALIZADO')).toBe(true);
    expect(canDownloadInformeLimsPdf(bioUser, 'FINALIZADO')).toBe(true);
    expect(canEnviarInformeLims(labUser, 'LISTO_PARA_VALIDAR')).toBe(false);
    expect(canEnviarInformeLims(labUser, 'FINALIZADO')).toBe(true);
    expect(canEnviarInformeLims(secUser, 'EN_PROCESO')).toBe(false);
    expect(canEnviarInformeLims(secUser, 'FINALIZADO')).toBe(true);
    expect(canEnviarInformeLims(enfUser, 'FINALIZADO')).toBe(false);
  });

  it('médico, secretaría y enfermería no descargan desde módulo LIMS', () => {
    expect(canDownloadInformeLimsPdf(medUser)).toBe(false);
    expect(canDownloadInformeLimsPdf(secUser, 'FINALIZADO')).toBe(false);
    expect(canDownloadInformeLimsPdf(enfUser, 'FINALIZADO')).toBe(false);
  });

  it('paciente no puede descargar desde módulo LIMS', () => {
    expect(canDownloadInformeLimsPdf(pacUser)).toBe(false);
    expect(canDownloadInformeLimsPdf(null)).toBe(false);
  });
});

describe('canOperateInformeMicro / canSeeInformeMicro / canDownloadInformeMicroPdf', () => {
  it('solo bioquímico y admin operan informes', () => {
    expect(canOperateInformeMicro(bioUser)).toBe(true);
    expect(canOperateInformeMicro(adminUser)).toBe(true);
    expect(canOperateInformeMicro(labUser)).toBe(false);
    expect(canOperateInformeMicro(medUser)).toBe(false);
  });

  it('lab y médico no ven contenido hasta VALIDADO', () => {
    expect(canSeeInformeMicro(labUser, 'EMITIDO')).toBe(false);
    expect(canSeeInformeMicro(medUser, 'BORRADOR')).toBe(false);
    expect(canSeeInformeMicro(labUser, 'VALIDADO')).toBe(true);
    expect(canSeeInformeMicro(medUser, 'VALIDADO')).toBe(true);
    expect(canSeeInformeMicro(bioUser, 'BORRADOR')).toBe(true);
  });

  it('PDF: bio puede con emitido; lab/médico solo validado', () => {
    expect(canDownloadInformeMicroPdf(bioUser, 'LISTO_PARA_VALIDAR')).toBe(true);
    expect(canDownloadInformeMicroPdf(labUser, 'LISTO_PARA_VALIDAR')).toBe(false);
    expect(canDownloadInformeMicroPdf(medUser, 'LISTO_PARA_VALIDAR')).toBe(false);
    expect(canDownloadInformeMicroPdf(labUser, 'VALIDADO')).toBe(true);
    expect(canDownloadInformeMicroPdf(medUser, 'VALIDADO')).toBe(true);
  });

  it('enviar solo tras VALIDADO/INFORMADO', () => {
    expect(canEnviarInformeMicro(labUser, 'LISTO_PARA_VALIDAR')).toBe(false);
    expect(canEnviarInformeMicro(labUser, 'VALIDADO')).toBe(true);
    expect(canEnviarInformeMicro(secUser, 'VALIDADO')).toBe(true);
    expect(canEnviarInformeMicro(enfUser, 'VALIDADO')).toBe(false);
  });
});

describe('canSeeResultadosClinicos / canDownloadInformeClinicoPdf', () => {
  it('operadores LIMS ven resultados aunque no esté finalizada', () => {
    expect(canSeeResultadosClinicos(labUser, 'EN_PROCESO')).toBe(true);
    expect(canSeeResultadosClinicos(bioUser, 'LISTO_PARA_VALIDAR')).toBe(true);
    expect(canSeeResultadosClinicos(adminUser, 'PENDIENTE')).toBe(true);
  });

  it('médico/secretaría ven resultados en cualquier estado; PDF solo FINALIZADO', () => {
    expect(canSeeResultadosClinicos(medUser, 'EN_PROCESO')).toBe(true);
    expect(canSeeResultadosClinicos(medUser, 'INFORMADO_PARCIAL')).toBe(true);
    expect(canSeeResultadosClinicos(medUser, 'FINALIZADO')).toBe(true);
    expect(canSeeResultadosClinicos(secUser, 'EN_PROCESO')).toBe(true);
    expect(canSeeResultadosClinicos(secUser, 'FINALIZADO')).toBe(true);

    expect(canDownloadInformeClinicoPdf(medUser, 'INFORMADO_PARCIAL')).toBe(false);
    expect(canDownloadInformeClinicoPdf(medUser, 'FINALIZADO')).toBe(true);
    expect(canDownloadInformeClinicoPdf(secUser, 'FINALIZADO')).toBe(true);
    expect(canDownloadInformeClinicoPdf(pacUser, 'EN_PROCESO')).toBe(false);
  });
});

describe('canAccessMicrobiologiaLectura', () => {
  it('permite médico, operadores LIMS, secretaría y enfermería', () => {
    expect(canAccessMicrobiologiaLectura(labUser)).toBe(true);
    expect(canAccessMicrobiologiaLectura(medUser)).toBe(true);
    expect(canAccessMicrobiologiaLectura(secUser)).toBe(true);
    expect(canAccessMicrobiologiaLectura(enfUser)).toBe(true);
    expect(canAccessMicrobiologia(medUser)).toBe(false);
  });

  it('niega paciente', () => {
    expect(canAccessMicrobiologiaLectura(pacUser)).toBe(false);
  });
});
