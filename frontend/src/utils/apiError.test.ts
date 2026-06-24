import { getSafeApiErrorMessage } from './apiError';

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
