import {
  isCodigoMicrobiologia,
  isCodigoProtocoloLab,
  isCodigoTuboLab,
} from './limsCodigoBarras';

describe('limsCodigoBarras', () => {
  it('detecta protocolo y tubo LAB', () => {
    expect(isCodigoProtocoloLab('LAB-2026-00003')).toBe(true);
    expect(isCodigoTuboLab('LAB-2026-00003-01')).toBe(true);
    expect(isCodigoProtocoloLab('LAB-2026-00003-01')).toBe(false);
  });

  it('legacy micro / mue', () => {
    expect(isCodigoMicrobiologia('MICB-2026-000003')).toBe(true);
    expect(isCodigoMicrobiologia('MIC-2026-000003')).toBe(true);
    expect(isCodigoTuboLab('MUE-2026-000001')).toBe(true);
  });
});
