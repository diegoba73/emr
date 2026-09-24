import React from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import CargaResultadosLims from './CargaResultadosLims';
import { getIqcPrecheck, getTiposExamenMap, postCargarResultados } from '../../services/limsApi';
import { RESULTADO_NO_CALCULABLE } from '../../utils/calculosDerivados';
import type { LimsTipoExamen, SolicitudExamenLims } from '../../types/lims';

jest.mock('../../services/limsApi');
jest.mock('./AnalisisLongitudinalPanel', () => () => null);
jest.mock('./useHistorialAnalitos', () => ({
  useHistorialAnalitos: () => ({
    previosPorTipo: new Map(),
    loading: false,
    error: '',
    actualizar: jest.fn(),
  }),
}));

it.each([false, true])('corrige TG guardado sin restaurar LDL anterior (catálogo tardío: %s)', async (catalogoTardio) => {
  jest.clearAllMocks();
  const codigos = ['COL_TOT', 'HDL', 'TG', 'LDL', 'COL_RESID'];
  const valores = ['101', '33', '99', '48', '20'];
  const catalog = new Map<number, LimsTipoExamen>(
    codigos.map((codigo, i) => [
      i + 1,
      {
        id: i + 1,
        codigo,
        nombre: codigo,
        tipo_muestra_requerida: 1,
        requiere_muestra: false,
        modo_entrada: i >= 3 ? 'CALCULADO' : 'ESTANDAR',
      },
    ])
  );
  const orden = {
    id: 1,
    numero: 'T-1',
    paciente: 1,
    medico_interno: null,
    origen_solicitud: 'AMBULATORIO_CEHTA',
    fecha_solicitud: '2026-09-21',
    estado: 'LISTO_PARA_VALIDAR',
    observaciones: '',
    paneles_resumen: [],
    resultados: codigos.map((codigo, i) => ({
      id: i + 1,
      tipo_examen: i + 1,
      tipo_examen_codigo: codigo,
      tipo_examen_nombre: codigo,
      valor_obtenido: valores[i],
      valor_numerico: valores[i],
    })),
  } as unknown as SolicitudExamenLims;

  let resolverCatalogo!: (value: Map<number, LimsTipoExamen>) => void;
  const catalogoPendiente = new Promise<Map<number, LimsTipoExamen>>((resolve) => {
    resolverCatalogo = resolve;
  });
  (getTiposExamenMap as jest.Mock).mockReturnValue(catalogoPendiente);
  (getIqcPrecheck as jest.Mock).mockResolvedValue({ aplicable: false, ok: true });
  (postCargarResultados as jest.Mock).mockResolvedValue(orden);

  render(<CargaResultadosLims orden={orden} muestras={[]} canOperate onGuardado={jest.fn()} />);

  if (!catalogoTardio) {
    await act(async () => { resolverCatalogo(catalog); });
  }

  // El formulario también permite editar mientras espera el catálogo.
  await waitFor(() => {
    expect(getTiposExamenMap).toHaveBeenCalled();
    expect(screen.getAllByText('Calculado')).toHaveLength(2);
    expect(screen.getByDisplayValue('99')).toBeInTheDocument();
    expect(screen.getByText('48')).toBeInTheDocument();
  });

  const tgInput = screen.getByDisplayValue('99');
  await act(async () => {
    fireEvent.change(tgInput, { target: { value: '400' } });
  });
  expect(screen.getAllByText(RESULTADO_NO_CALCULABLE)).toHaveLength(2);
  if (catalogoTardio) {
    await act(async () => { resolverCatalogo(catalog); });
  }

  await waitFor(() => {
    expect(screen.getByDisplayValue('400')).toBeInTheDocument();
    expect(screen.getAllByText(RESULTADO_NO_CALCULABLE)).toHaveLength(2);
    expect(screen.queryByText('48')).not.toBeInTheDocument();
  });

  fireEvent.click(screen.getByRole('button', { name: /guardar avance/i }));
  await waitFor(() => expect(postCargarResultados).toHaveBeenCalled());
  const payload = (postCargarResultados as jest.Mock).mock.calls[0][1];
  expect(payload).toEqual(
    expect.arrayContaining([
      expect.objectContaining({ id: 3, valor: '400', valor_numerico: 400 }),
      expect.objectContaining({ id: 4, valor: RESULTADO_NO_CALCULABLE, valor_numerico: null }),
    ])
  );

  await act(async () => {
    fireEvent.change(screen.getByDisplayValue('400'), { target: { value: '150' } });
  });
  await waitFor(() => {
    expect(screen.queryByText(RESULTADO_NO_CALCULABLE)).not.toBeInTheDocument();
    expect(screen.getByText('38')).toBeInTheDocument();
  });
});
