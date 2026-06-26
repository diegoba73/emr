import { getSafeApiErrorMessage, getSafeClinicalActionMessage, CLINICAL_ACTION_ERRORS } from './apiError';

describe('getSafeApiErrorMessage', () => {
  it('devuelve mensaje genérico para 403 sin PHI', () => {
    const err = { response: { status: 403, data: { detail: 'Paciente Juan Pérez DNI 12345' } } };
    expect(getSafeApiErrorMessage(err)).toBe('No tiene permisos para realizar esta acción.');
  });

  it('devuelve mensaje para 404', () => {
    expect(getSafeApiErrorMessage({ response: { status: 404 } })).toBe(
      'El recurso solicitado no está disponible.'
    );
  });

  it('usa fallback para otros errores', () => {
    expect(getSafeApiErrorMessage({}, 'Fallo')).toBe('Fallo');
  });
});

describe('getSafeClinicalActionMessage', () => {
  it('no expone detail del backend en mensajes visibles', () => {
    const err = {
      response: { status: 500, data: { detail: 'Paciente Juan Pérez DNI 12345' } },
    };
    expect(
      getSafeClinicalActionMessage(err, CLINICAL_ACTION_ERRORS.turnoIniciarAtencion)
    ).toBe(CLINICAL_ACTION_ERRORS.turnoIniciarAtencion);
  });

  it('respeta 403 sin parsear response.data', () => {
    const err = { response: { status: 403, data: { detail: 'dato sensible' } } };
    expect(getSafeClinicalActionMessage(err, CLINICAL_ACTION_ERRORS.turnoGuardar)).toBe(
      'No tiene permisos para realizar esta acción.'
    );
  });

  it('devuelve mensaje seguro para acciones LIMS sin exponer detail', () => {
    const err = {
      response: { status: 500, data: { detail: 'Paciente Juan Pérez DNI 12345' } },
    };
    expect(
      getSafeClinicalActionMessage(err, CLINICAL_ACTION_ERRORS.limsCancelarEstudioMicro)
    ).toBe(CLINICAL_ACTION_ERRORS.limsCancelarEstudioMicro);
  });
});
