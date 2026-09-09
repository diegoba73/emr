import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

const mockList = jest.fn();
const mockGetZpl = jest.fn();
const mockImprimir = jest.fn();
const mockTalon = jest.fn();

jest.mock('../../services/limsApi', () => ({
  listMuestrasPorSolicitud: (...args: unknown[]) => mockList(...args),
  getMuestraEtiquetaZpl: (...args: unknown[]) => mockGetZpl(...args),
  postMuestraImprimirEtiqueta: (...args: unknown[]) => mockImprimir(...args),
  printTalonOrden: (...args: unknown[]) => mockTalon(...args),
}));

jest.mock('react-hot-toast', () => ({
  __esModule: true,
  default: {
    success: jest.fn(),
    error: jest.fn(),
  },
}));

import toast from 'react-hot-toast';
import type { MuestraTransaccional } from '../../types/lims';
import EtiquetasMuestrasZplOrdenDialog from './EtiquetasMuestrasZplOrdenDialog';

const mockToast = toast as unknown as { success: jest.Mock; error: jest.Mock };

const pendiente: MuestraTransaccional = {
  id: 10,
  codigo_barra: 'LAB-2026-00018-01',
  solicitud: 18,
  paciente: 1,
  tipo_muestra: 1,
  tipo_contenedor: 1,
  estado: 'PENDIENTE_TOMA',
  lugar_extraccion: null,
};

const zplOk = {
  muestra_id: 10,
  profile: '3nstar_ldt114_203_40x23',
  width_mm: 40,
  height_mm: 23,
  lines: ['LAB-2026-00018-01', 'SEPULVEDA R. | DNI 21021465', 'INTERNACION UCO', '08/09 00:00 | HEP'],
  zpl: '^XA^XZ',
  printable: true,
  validation_errors: [] as string[],
};

describe('EtiquetasMuestrasZplOrdenDialog', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockList.mockResolvedValue([pendiente]);
    mockGetZpl.mockResolvedValue(zplOk);
    mockImprimir.mockResolvedValue({ muestra_id: 10, profile: 'x', resultado: 'ok' });
    mockTalon.mockResolvedValue(undefined);
  });

  it('lista preview por muestra sin tomar', async () => {
    render(
      <EtiquetasMuestrasZplOrdenDialog
        open
        solicitudId={18}
        solicitudNumero="LAB-2026-00018"
        onClose={jest.fn()}
      />
    );
    await waitFor(() => {
      expect(screen.getByText(/LAB-2026-00018-01 · pendiente de recepción/i)).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: 'Imprimir etiqueta' })).toBeInTheDocument();
    expect(mockGetZpl).toHaveBeenCalledWith(10);
  });

  it('imprimir solo llama imprimir-etiqueta (no toma)', async () => {
    render(
      <EtiquetasMuestrasZplOrdenDialog open solicitudId={18} onClose={jest.fn()} />
    );
    await waitFor(() => screen.getByRole('button', { name: 'Imprimir etiqueta' }));
    fireEvent.click(screen.getByRole('button', { name: 'Imprimir etiqueta' }));
    await waitFor(() => {
      expect(mockImprimir).toHaveBeenCalledWith(10);
    });
    expect(mockToast.success).toHaveBeenCalled();
  });

  it('lock anti doble click por fila', async () => {
    let resolvePrint: (v: unknown) => void = () => undefined;
    mockImprimir.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolvePrint = resolve;
        })
    );
    render(
      <EtiquetasMuestrasZplOrdenDialog open solicitudId={18} onClose={jest.fn()} />
    );
    await waitFor(() => screen.getByRole('button', { name: 'Imprimir etiqueta' }));
    const btn = screen.getByRole('button', { name: 'Imprimir etiqueta' });
    fireEvent.click(btn);
    fireEvent.click(btn);
    await waitFor(() => expect(mockImprimir).toHaveBeenCalledTimes(1));
    resolvePrint({ ok: true });
  });

  it('imprimir talón no llama ZPL ni toma', async () => {
    render(
      <EtiquetasMuestrasZplOrdenDialog
        open
        solicitudId={18}
        solicitudNumero="LAB-2026-00018"
        onClose={jest.fn()}
      />
    );
    await waitFor(() => screen.getByRole('button', { name: 'Imprimir talón' }));
    fireEvent.click(screen.getByRole('button', { name: 'Imprimir talón' }));
    await waitFor(() => {
      expect(mockTalon).toHaveBeenCalledWith(18);
    });
    expect(mockImprimir).not.toHaveBeenCalled();
  });
});
