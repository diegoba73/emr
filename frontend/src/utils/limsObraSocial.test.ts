import {
  origenRequiereAutorizacionObraSocial,
  ordenPuedeValidarObraSocial,
} from './limsObraSocial';

describe('origenRequiereAutorizacionObraSocial', () => {
  it('exige autorización en ambulatorio y receta externa', () => {
    expect(origenRequiereAutorizacionObraSocial('AMBULATORIO_CEHTA')).toBe(true);
    expect(origenRequiereAutorizacionObraSocial('AMBULATORIO_ICPL')).toBe(true);
    expect(origenRequiereAutorizacionObraSocial('EXTERNO_CEHTA')).toBe(true);
    expect(origenRequiereAutorizacionObraSocial('EXTERNO_ICPL')).toBe(true);
  });

  it('no exige autorización en internación ni guardia', () => {
    expect(origenRequiereAutorizacionObraSocial('INTERNACION_UCO')).toBe(false);
    expect(origenRequiereAutorizacionObraSocial('INTERNACION_UCE')).toBe(false);
    expect(origenRequiereAutorizacionObraSocial('GUARDIA')).toBe(false);
  });
});

describe('ordenPuedeValidarObraSocial', () => {
  it('bloquea ambulatorio sin Autorizado', () => {
    expect(
      ordenPuedeValidarObraSocial({
        origen_solicitud: 'AMBULATORIO_CEHTA',
        estado_obra_social: '',
      })
    ).toBe(false);
    expect(
      ordenPuedeValidarObraSocial({
        origen_solicitud: 'EXTERNO_ICPL',
        estado_obra_social: 'FALTA_AUTORIZACION',
      })
    ).toBe(false);
    expect(
      ordenPuedeValidarObraSocial({
        origen_solicitud: 'AMBULATORIO_ICPL',
        estado_obra_social: 'DEBE_ABONAR',
      })
    ).toBe(false);
  });

  it('permite ambulatorio Autorizado', () => {
    expect(
      ordenPuedeValidarObraSocial({
        origen_solicitud: 'AMBULATORIO_CEHTA',
        estado_obra_social: 'AUTORIZADO',
      })
    ).toBe(true);
  });

  it('permite internación y guardia sin cargar obra social', () => {
    expect(
      ordenPuedeValidarObraSocial({
        origen_solicitud: 'INTERNACION_UCO',
        estado_obra_social: '',
      })
    ).toBe(true);
    expect(
      ordenPuedeValidarObraSocial({
        origen_solicitud: 'GUARDIA',
        estado_obra_social: 'DEBE_ORDEN',
      })
    ).toBe(true);
  });

  it('respeta flags del API si vienen', () => {
    expect(
      ordenPuedeValidarObraSocial({
        origen_solicitud: 'AMBULATORIO_CEHTA',
        estado_obra_social: '',
        obra_social_permite_validar: true,
      })
    ).toBe(true);
    expect(
      ordenPuedeValidarObraSocial({
        origen_solicitud: 'GUARDIA',
        estado_obra_social: 'AUTORIZADO',
        obra_social_permite_validar: false,
      })
    ).toBe(false);
  });
});
