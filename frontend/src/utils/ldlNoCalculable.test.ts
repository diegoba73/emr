import type { LimsTipoExamen, ResultadoExamenLims } from '../types/lims';
import { RESULTADO_NO_CALCULABLE } from './calculosDerivados';
import { applyAutofillVcmChcm, buildCargarResultadoPayload, draftValorClinicoNumerico, normalizeDraftRow } from './limsCargaMuestra';

const codigos = ['COL_TOT', 'HDL', 'TG', 'LDL', 'COL_RESID'];
const resultados = codigos.map((codigo, index) => ({
  id: index + 1, tipo_examen: index + 1, tipo_examen_codigo: codigo,
  valor_obtenido: '', valor_numerico: null,
})) as ResultadoExamenLims[];
const catalog = new Map(codigos.map((codigo, index) => [index + 1, {
  id: index + 1, codigo, nombre: codigo, modo_entrada: index >= 3 ? 'CALCULADO' : 'ESTANDAR',
}] as [number, LimsTipoExamen]));

it.each(['400', '401', '600'])('quita LDL/residual previos al corregir TG a %s y los recupera con datos calculables', (tg) => {
  let draft = Object.fromEntries(resultados.map((r) => [r.id, normalizeDraftRow()]));
  draft[1] = normalizeDraftRow({ valor: '101' });
  draft[2] = normalizeDraftRow({ valor: '33' });
  draft[3] = normalizeDraftRow({ valor: '99' });
  draft = applyAutofillVcmChcm(resultados, draft, catalog, new Set());
  expect(draft[4].valor_numerico).toBe('48');
  draft[3] = normalizeDraftRow({ valor: tg });
  draft = applyAutofillVcmChcm(resultados, draft, catalog, new Set());
  for (const id of [4, 5]) {
    expect(draft[id].valor).toBe(RESULTADO_NO_CALCULABLE);
    expect(draft[id].valor_numerico).toBe('');
    const payload = buildCargarResultadoPayload(id, draft[id], catalog.get(id));
    expect(payload.valor).toBe(RESULTADO_NO_CALCULABLE);
    expect(payload.valor_numerico).toBeNull();
    expect(draftValorClinicoNumerico(resultados[id - 1], draft, catalog)).toBeNull();
  }
  draft[3] = normalizeDraftRow({ valor: '150' });
  draft = applyAutofillVcmChcm(resultados, draft, catalog, new Set());
  expect(draft[4].valor).toBe('38');
  expect(draft[4].valor_numerico).toBe('38');
  expect(draft[5].valor_numerico).toBe('30');
});
