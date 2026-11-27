import {
  CODIGO_PROBNP,
  MENSAJE_PROBNP_FRECUENCIA,
  collectAvisosFrecuencia,
  formatAvisosFrecuenciaConfirmacion,
  mensajeAvisoExamen,
  mensajeBloqueoExamen,
  puedeOmitirRestriccionFrecuenciaEnsayos,
} from './limsRestriccionesEnsayos';

describe('limsRestriccionesEnsayos', () => {
  it('admin, laboratorio y bioquímico omiten el tope', () => {
    expect(puedeOmitirRestriccionFrecuenciaEnsayos('laboratorio')).toBe(true);
    expect(puedeOmitirRestriccionFrecuenciaEnsayos('BIOQUIMICO')).toBe(true);
    expect(puedeOmitirRestriccionFrecuenciaEnsayos('admin')).toBe(true);
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

  it('aviso soft no bloquea pero expone mensaje', () => {
    const mapa = {
      PAN_IONO: {
        bloqueado: false,
        aviso: true,
        mensaje: 'SEROS solo cubre ionograma una vez al año.',
      },
    };
    expect(mensajeBloqueoExamen('PAN_IONO', mapa)).toBeNull();
    expect(mensajeAvisoExamen('PAN_IONO', mapa)).toContain('SEROS');
  });

  it('collectAvisosFrecuencia dedupea panel + componentes', () => {
    const mapa = {
      PAN_IONO: { bloqueado: false, aviso: true, mensaje: 'aviso iono' },
      NA: { bloqueado: false, aviso: true, mensaje: 'aviso iono' },
      HBA1C: { bloqueado: false, aviso: true, mensaje: 'aviso hba1c' },
    };
    const avisos = collectAvisosFrecuencia(
      [
        {
          codigo: 'PAN_IONO',
          nombre: 'Ionograma',
          componentes: [{ codigo: 'NA', nombre: 'Sodio' }],
        },
        { codigo: 'HBA1C', nombre: 'HbA1c' },
      ],
      mapa
    );
    expect(avisos.map((a) => a.codigo)).toEqual(['HBA1C', 'PAN_IONO']);
    expect(formatAvisosFrecuenciaConfirmacion(avisos)).toContain('¿Enviar el pedido');
  });
});
