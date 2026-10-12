import {
  cultivosCodigosAutoPreselect,
  cultivosCodigosDeMateriales,
  syncMicroItemsConMateriales,
} from './limsMaterialesMicro';

describe('limsMaterialesMicro', () => {
  const sangre = { codigo: 'SANGRE', cultivo_micro_codigo: 'HEMOCULTIVO' };
  const orina = { codigo: 'ORINA', cultivo_micro_codigo: 'UROCULTIVO' };
  const lcr = { codigo: 'LCR', cultivo_micro_codigo: 'LCR' };

  it('permitidos incluye urocultivo y LCR cuando ambos materiales están', () => {
    expect(cultivosCodigosDeMateriales([sangre, orina, lcr]).sort()).toEqual(
      ['HEMOCULTIVO', 'LCR', 'UROCULTIVO'].sort()
    );
  });

  it('auto-preselect no fuerza hemocultivo; sí urocultivo y LCR', () => {
    expect(cultivosCodigosAutoPreselect([sangre, orina, lcr]).sort()).toEqual(
      ['LCR', 'UROCULTIVO'].sort()
    );
  });

  it('al agregar LCR no elimina urocultivo ya marcado', () => {
    const prev = [
      { cultivo_codigo: 'UROCULTIVO' },
      { cultivo_codigo: 'LCR' },
    ];
    const next = syncMicroItemsConMateriales(prev, {
      permitidos: cultivosCodigosDeMateriales([orina, lcr]),
      autoPreselect: cultivosCodigosAutoPreselect([orina, lcr]),
      buildItem: (c) => ({ cultivo_codigo: c }),
    });
    const codes = next.map((i) => i.cultivo_codigo).sort();
    expect(codes).toEqual(['LCR', 'UROCULTIVO']);
  });

  it('regresión: LCR + orina agrega ambos cultivos aunque prev solo tenía LCR', () => {
    const next = syncMicroItemsConMateriales([{ cultivo_codigo: 'LCR' }], {
      permitidos: cultivosCodigosDeMateriales([sangre, orina, lcr]),
      autoPreselect: cultivosCodigosAutoPreselect([sangre, orina, lcr]),
      buildItem: (c) => ({ cultivo_codigo: c }),
    });
    expect(next.map((i) => i.cultivo_codigo).sort()).toEqual(['LCR', 'UROCULTIVO']);
    expect(next.map((i) => i.cultivo_codigo)).not.toContain('HEMOCULTIVO');
  });

  it('al quitar orina elimina urocultivo', () => {
    const next = syncMicroItemsConMateriales(
      [{ cultivo_codigo: 'UROCULTIVO' }, { cultivo_codigo: 'LCR' }],
      {
        permitidos: cultivosCodigosDeMateriales([lcr]),
        autoPreselect: cultivosCodigosAutoPreselect([lcr]),
        buildItem: (c) => ({ cultivo_codigo: c }),
      }
    );
    expect(next.map((i) => i.cultivo_codigo)).toEqual(['LCR']);
  });
});
