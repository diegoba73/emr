import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ResultadosOrdenLista from './ResultadosOrdenLista';
import type { ResultadoExamenLims } from '../../types/lims';

jest.mock('./TendenciaAnalitoDialog', () => ({
  __esModule: true,
  default: ({ open, tipoExamenNombre }: { open: boolean; tipoExamenNombre: string }) =>
    open ? <div data-testid="tendencia-dialog">{tipoExamenNombre}</div> : null,
}));

const resultado: ResultadoExamenLims = {
  id: 1,
  solicitud: 42,
  tipo_examen: 7,
  tipo_examen_codigo: 'TROP',
  tipo_examen_nombre: 'Troponina I',
  valor_obtenido: '28',
  valor_numerico: 28,
  unidad: 'ng/L',
  es_patologico: true,
  es_critico: false,
};

it('muestra botón de tendencia y abre el dialog', async () => {
  render(<ResultadosOrdenLista resultados={[resultado]} modo="clinico" estadoOrden="FINALIZADO" />);
  const btn = screen.getByRole('button', { name: /Ver tendencia de Troponina I/i });
  await userEvent.click(btn);
  expect(screen.getByTestId('tendencia-dialog')).toHaveTextContent('Troponina I');
});

it('sin solicitud no muestra botón de tendencia', () => {
  const sinSol = { ...resultado, solicitud: 0 as unknown as number };
  // fuerza ausencia: solicitud falsy
  render(
    <ResultadosOrdenLista
      resultados={[{ ...sinSol, solicitud: undefined as unknown as number }]}
      modo="laboratorio"
    />
  );
  expect(screen.queryByRole('button', { name: /Ver tendencia/i })).not.toBeInTheDocument();
});
