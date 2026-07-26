import { calcChcmGdl, calcVcmFl } from './hemogramaIndices';

describe('hemogramaIndices', () => {
  it('calcula VCM y CHCM', () => {
    expect(calcVcmFl(28, 3.5)).toBe(80);
    expect(calcChcmGdl(8, 28)).toBe(28.6);
  });

  it('devuelve null con denominador inválido', () => {
    expect(calcVcmFl(28, 0)).toBeNull();
    expect(calcChcmGdl(8, 0)).toBeNull();
  });
});
