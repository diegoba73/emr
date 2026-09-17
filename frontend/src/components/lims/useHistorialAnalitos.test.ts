import { act, renderHook, waitFor } from '@testing-library/react';
import { getHistorialAnalitos } from '../../services/limsApi';
import { useHistorialAnalitos } from './useHistorialAnalitos';

jest.mock('../../services/limsApi', () => ({ getHistorialAnalitos: jest.fn() }));
const get = getHistorialAnalitos as jest.Mock;
const response = { analitos: [{ tipo_examen_id: 7, previos: [{ resultado_id: 1, valor: '75' }] }] };
beforeEach(() => jest.resetAllMocks());

it('muestra el fallo y permite reintentar sin confundirlo con ausencia de historial', async () => {
  get.mockRejectedValueOnce(new Error('503')).mockResolvedValueOnce(response);
  const { result } = renderHook(() => useHistorialAnalitos(10, '7'));
  await waitFor(() => expect(result.current.error).toContain('No se pudo consultar'));
  act(() => result.current.actualizar());
  await waitFor(() => expect(result.current.previosPorTipo.get(7)?.[0].valor).toBe('75'));
  expect(result.current.error).toBe('');
});

it('consulta de nuevo al agregar un ensayo a la misma orden', async () => {
  get.mockResolvedValue(response);
  const { result, rerender } = renderHook(({ tipos }) => useHistorialAnalitos(10, tipos),
    { initialProps: { tipos: '7' } });
  await waitFor(() => expect(result.current.loading).toBe(false));
  rerender({ tipos: '7,8' });
  await waitFor(() => expect(get).toHaveBeenCalledTimes(2));
  await waitFor(() => expect(result.current.loading).toBe(false));
});

it('descarta respuestas de otra orden para no mezclar pacientes', async () => {
  let resolveOld: (value: unknown) => void = () => {};
  get.mockImplementationOnce(() => new Promise((resolve) => { resolveOld = resolve; }));
  get.mockResolvedValueOnce({ analitos: [] });
  const { result, rerender } = renderHook(({ id }) => useHistorialAnalitos(id, '7'),
    { initialProps: { id: 10 } });
  rerender({ id: 11 });
  await waitFor(() => expect(result.current.loading).toBe(false));
  await act(async () => resolveOld(response));
  expect(result.current.previosPorTipo.size).toBe(0);
  expect(result.current.error).toBe('');
});
