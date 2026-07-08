import {
  addLocalDays,
  buildDiasLaboratorio,
  diasVisiblesParaIncluir,
  formatFechaLocal,
  labelDiaOrden,
  parseFechaLocal,
  startOfLocalDay,
} from './limsOrdenesFecha';

describe('limsOrdenesFecha', () => {
  const hoy = startOfLocalDay(new Date(2026, 5, 28));

  it('formatea y parsea fecha local', () => {
    expect(formatFechaLocal(hoy)).toBe('2026-06-28');
    expect(formatFechaLocal(parseFechaLocal('2026-06-27'))).toBe('2026-06-27');
  });

  it('etiqueta hoy y ayer', () => {
    expect(labelDiaOrden(hoy, hoy)).toBe('Hoy');
    expect(labelDiaOrden(addLocalDays(hoy, -1), hoy)).toBe('Ayer');
  });

  it('arma lista de días hacia atrás', () => {
    const dias = buildDiasLaboratorio(3, hoy);
    expect(dias).toHaveLength(3);
    expect(formatFechaLocal(dias[0])).toBe('2026-06-28');
    expect(formatFechaLocal(dias[2])).toBe('2026-06-26');
  });

  it('calcula pestañas para día antiguo', () => {
    const viejo = addLocalDays(hoy, -10);
    expect(diasVisiblesParaIncluir(viejo, 7, hoy)).toBe(11);
  });
});
