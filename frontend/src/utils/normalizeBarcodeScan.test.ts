import { normalizeBarcodeScan } from './normalizeBarcodeScan';

describe('normalizeBarcodeScan', () => {
  it('reemplaza apóstrofos de teclado ES por guiones', () => {
    expect(normalizeBarcodeScan("LAB'2026'00018'01")).toBe('LAB-2026-00018-01');
  });

  it('hace trim y conserva códigos ya correctos', () => {
    expect(normalizeBarcodeScan('  LAB-2026-00018-01  ')).toBe('LAB-2026-00018-01');
  });

  it('normaliza acentos tipográficos usados como guion', () => {
    expect(normalizeBarcodeScan("LAB´2026`00018'01")).toBe('LAB-2026-00018-01');
  });
});
