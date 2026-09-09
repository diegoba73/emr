import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

const mockEtiqueta = jest.fn();
const mockTalon = jest.fn();

jest.mock('../../../services/limsMicroApi', () => ({
  downloadEtiquetasEstudioMicro: (...args: any[]) => mockEtiqueta(...args),
  printTalonEstudioMicro: (...args: any[]) => mockTalon(...args),
}));

jest.mock('react-hot-toast', () => ({
  __esModule: true,
  default: { success: jest.fn(), error: jest.fn() },
}));

import ImprimirPedidoMicroDialog from './ImprimirPedidoMicroDialog';

describe('ImprimirPedidoMicroDialog', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockEtiqueta.mockResolvedValue(undefined);
    mockTalon.mockResolvedValue(undefined);
  });

  it('talon no llama imprimir-etiquetas', async () => {
    const onEtiquetasOk = jest.fn();
    render(
      <ImprimirPedidoMicroDialog
        open
        estudioId={7}
        estudioNumero="LAB-2026-00099"
        onClose={jest.fn()}
        onEtiquetasOk={onEtiquetasOk}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: 'Imprimir talón' }));
    await waitFor(() => {
      expect(mockTalon).toHaveBeenCalledWith(7);
    });
    expect(mockEtiqueta).not.toHaveBeenCalled();
    expect(onEtiquetasOk).not.toHaveBeenCalled();
  });

  it('etiqueta llama download etiquetas y onEtiquetasOk', async () => {
    const onEtiquetasOk = jest.fn();
    const onClose = jest.fn();
    render(
      <ImprimirPedidoMicroDialog
        open
        estudioId={7}
        onClose={onClose}
        onEtiquetasOk={onEtiquetasOk}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: 'Imprimir etiqueta' }));
    await waitFor(() => {
      expect(mockEtiqueta).toHaveBeenCalledWith(7);
    });
    expect(onEtiquetasOk).toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
    expect(mockTalon).not.toHaveBeenCalled();
  });
});
