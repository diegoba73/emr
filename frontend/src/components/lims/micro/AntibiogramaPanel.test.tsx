import React from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import type { Antibiograma } from '../../../types/lims';
import AntibiogramaPanel from './AntibiogramaPanel';

const mockCancelarAntibiograma = jest.fn();

jest.mock('../../../services/limsApi', () => ({
  cancelarAntibiograma: (...args: unknown[]) => mockCancelarAntibiograma(...args),
  completarAntibiograma: jest.fn(),
  createAntibiograma: jest.fn(),
  createResultadoAntibiotico: jest.fn(),
  formatDrfError: (e: unknown) => String(e),
}));

jest.mock('react-hot-toast', () => ({
  __esModule: true,
  default: { success: jest.fn(), error: jest.fn() },
}));

const antibiogramaAbierto: Antibiograma = {
  id: 7,
  aislado: 1,
  estado: 'EN_PROCESO',
  metodo: 'disco',
};

describe('AntibiogramaPanel', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockCancelarAntibiograma.mockResolvedValue({});
  });

  it('abre modal MUI al cancelar y llama API con motivo', async () => {
    const onRefresh = jest.fn();
    render(
      <AntibiogramaPanel
        aislados={[]}
        antibiogramas={[antibiogramaAbierto]}
        resultados={[]}
        antibioticos={[]}
        canOperate
        onRefresh={onRefresh}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }));
    const dialog = screen.getByRole('dialog');
    fireEvent.change(within(dialog).getByRole('textbox'), {
      target: { value: 'Contaminación' },
    });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Cancelar antibiograma' }));

    await waitFor(() => {
      expect(mockCancelarAntibiograma).toHaveBeenCalledWith(7, 'Contaminación');
    });
    expect(onRefresh).toHaveBeenCalled();
  });

  it('no llama API si se cierra el modal sin confirmar', async () => {
    render(
      <AntibiogramaPanel
        aislados={[]}
        antibiogramas={[antibiogramaAbierto]}
        resultados={[]}
        antibioticos={[]}
        canOperate
        onRefresh={jest.fn()}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }));
    const dialog = screen.getByRole('dialog');
    fireEvent.click(within(dialog).getByRole('button', { name: 'Cancelar' }));

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
    expect(mockCancelarAntibiograma).not.toHaveBeenCalled();
  });

  it('no muestra acción cancelar si canOperate es false', () => {
    render(
      <AntibiogramaPanel
        aislados={[]}
        antibiogramas={[antibiogramaAbierto]}
        resultados={[]}
        antibioticos={[]}
        canOperate={false}
        onRefresh={jest.fn()}
      />
    );

    expect(screen.queryByRole('button', { name: 'Cancelar' })).not.toBeInTheDocument();
  });
});
