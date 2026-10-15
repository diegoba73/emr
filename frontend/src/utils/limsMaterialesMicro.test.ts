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

  it('auto-preselect no marca ningún cultivo al elegir materiales', () => {
    expect(cultivosCodigosAutoPreselect([sangre, orina, lcr])).toEqual([]);
    expect(cultivosCodigosAutoPreselect([orina])).toEqual([]);
  });

  it('al agregar orina no auto-marca urocultivo', () => {
    const next = syncMicroItemsConMateriales([], {
      permitidos: cultivosCodigosDeMateriales([orina]),
      autoPreselect: cultivosCodigosAutoPreselect([orina]),
      buildItem: (c) => ({ cultivo_codigo: c }),
    });
    expect(next).toEqual([]);
  });

  it('conserva cultivos que el operador ya marcó al sumar otro material', () => {
    const prev = [{ cultivo_codigo: 'UROCULTIVO' }];
    const next = syncMicroItemsConMateriales(prev, {
      permitidos: cultivosCodigosDeMateriales([orina, lcr]),
      autoPreselect: cultivosCodigosAutoPreselect([orina, lcr]),
      buildItem: (c) => ({ cultivo_codigo: c }),
    });
    expect(next.map((i) => i.cultivo_codigo)).toEqual(['UROCULTIVO']);
    expect(next.map((i) => i.cultivo_codigo)).not.toContain('LCR');
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
