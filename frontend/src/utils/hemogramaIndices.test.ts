import { calcChcmGdl, calcHcmPg, calcVcmFl } from './hemogramaIndices';

describe('hemogramaIndices', () => {
  it('calcula VCM, HCM y CHCM con 2 decimales (PDF ICPL)', () => {
    expect(calcVcmFl(36, 3.81)).toBe(94.49);
    expect(calcHcmPg(11.5, 3.81)).toBe(30.18);
    expect(calcChcmGdl(11.5, 36)).toBe(31.94);
  });

  it('devuelve null con denominador 0', () => {
    expect(calcVcmFl(28, 0)).toBeNull();
    expect(calcHcmPg(8, 0)).toBeNull();
    expect(calcChcmGdl(8, 0)).toBeNull();
  });
});
