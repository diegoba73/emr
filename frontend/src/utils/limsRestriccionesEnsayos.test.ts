import {
  CODIGO_PROBNP,
  MENSAJE_PROBNP_FRECUENCIA,
  mensajeBloqueoExamen,
  puedeOmitirRestriccionFrecuenciaEnsayos,
} from './limsRestriccionesEnsayos';

describe('limsRestriccionesEnsayos', () => {
  it('solo laboratorio/bioquímico omiten el tope', () => {
    expect(puedeOmitirRestriccionFrecuenciaEnsayos('laboratorio')).toBe(true);
    expect(puedeOmitirRestriccionFrecuenciaEnsayos('BIOQUIMICO')).toBe(true);
    expect(puedeOmitirRestriccionFrecuenciaEnsayos('admin')).toBe(false);
    expect(puedeOmitirRestriccionFrecuenciaEnsayos('medico')).toBe(false);
  });

  it('devuelve mensaje si el ensayo está bloqueado', () => {
    expect(
      mensajeBloqueoExamen(CODIGO_PROBNP, {
        PROBNP: { bloqueado: true, mensaje: MENSAJE_PROBNP_FRECUENCIA },
      })
    ).toBe(MENSAJE_PROBNP_FRECUENCIA);
    expect(mensajeBloqueoExamen(CODIGO_PROBNP, { PROBNP: { bloqueado: false } })).toBeNull();
    expect(mensajeBloqueoExamen('GLU', { PROBNP: { bloqueado: true } })).toBeNull();
  });
});
