import { esTipoMuestraSangrePedido } from './limsMuestraSangre';

describe('esTipoMuestraSangrePedido', () => {
  it('acepta suero, edta, heparina, citrato y variantes', () => {
    expect(esTipoMuestraSangrePedido('SUERO')).toBe(true);
    expect(esTipoMuestraSangrePedido('SANGRE_EDTA')).toBe(true);
    expect(esTipoMuestraSangrePedido('PLASMA_EDTA')).toBe(true);
    expect(esTipoMuestraSangrePedido('PLASMA_CITRATO')).toBe(true);
    expect(esTipoMuestraSangrePedido('SANGRE_HEPARINA_ART')).toBe(true);
    expect(esTipoMuestraSangrePedido('SANGRE_SECA_EN_PAPEL_FILTRO')).toBe(true);
    expect(esTipoMuestraSangrePedido('SANGRE_2')).toBe(true);
    expect(esTipoMuestraSangrePedido('SUERO_Y_ORINA_24_H')).toBe(true);
  });

  it('rechaza materiales que no son sangre', () => {
    expect(esTipoMuestraSangrePedido('ORINA')).toBe(false);
    expect(esTipoMuestraSangrePedido('ORINA_24_H')).toBe(false);
    expect(esTipoMuestraSangrePedido('LCR')).toBe(false);
    expect(esTipoMuestraSangrePedido('ESPUTO')).toBe(false);
    expect(esTipoMuestraSangrePedido('MATERIA_FECAL')).toBe(false);
    expect(esTipoMuestraSangrePedido('PLASMA_SEMINAL')).toBe(false);
    expect(esTipoMuestraSangrePedido('MEDULA_OSEA_EDTA')).toBe(false);
    expect(esTipoMuestraSangrePedido('LIQ_PLEURAL')).toBe(false);
    expect(esTipoMuestraSangrePedido('')).toBe(false);
  });
});
