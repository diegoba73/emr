import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

const mockTomar = jest.fn();
const mockImprimir = jest.fn();
const mockGetZpl = jest.fn();

jest.mock('../../services/limsApi', () => ({
  postMuestraTomar: (...args: unknown[]) => mockTomar(...args),
  postMuestraRecibir: jest.fn(),
  postMuestraRechazar: jest.fn(),
  postMuestraConservar: jest.fn(),
  postMuestraDescartar: jest.fn(),
  postMuestraCancelar: jest.fn(),
  postMuestraImprimirEtiqueta: (...args: unknown[]) => mockImprimir(...args),
  getMuestraEtiquetaZpl: (...args: unknown[]) => mockGetZpl(...args),
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
import MuestraAcciones from './MuestraAcciones';

const mockToast = toast as unknown as { success: jest.Mock; error: jest.Mock };

const baseMuestra: MuestraTransaccional = {
  id: 42,
  codigo_barra: 'LAB-2026-00001-01',
  solicitud: 1,
  paciente: 1,
  tipo_muestra: 1,
  tipo_contenedor: 1,
  estado: 'TOMADA',
  fecha_toma: '2026-09-07T14:05:00Z',
  lugar_extraccion: 'GUARDIA',
  ubicacion_actual: '',
};

describe('MuestraAcciones etiquetas ZPL', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockGetZpl.mockResolvedValue({
      muestra_id: 42,
      profile: '3nstar_ldt114_203_40x23',
      width_mm: 40,
      height_mm: 23,
      lines: [
        'LAB-2026-00001-01',
        'PEREZ J. | DNI 23123456',
        'GUARDIA',
        '07/09 14:05 | EDTA',
      ],
      zpl: '^XA^XZ',
      printable: true,
      validation_errors: [],
    });
    mockImprimir.mockResolvedValue({ muestra_id: 42, profile: 'x', resultado: 'ok' });
    mockTomar.mockResolvedValue({ ...baseMuestra, estado: 'TOMADA' });
  });

  it('muestra botones de etiqueta para operador', () => {
    render(<MuestraAcciones muestra={baseMuestra} canOperate onUpdated={jest.fn()} />);
    expect(screen.getByRole('button', { name: 'Vista previa etiqueta' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Imprimir etiqueta' })).toBeInTheDocument();
  });

  it('no muestra acciones si canOperate es false', () => {
    const { container } = render(
      <MuestraAcciones muestra={baseMuestra} canOperate={false} onUpdated={jest.fn()} />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('preview usa líneas del backend', async () => {
    render(<MuestraAcciones muestra={baseMuestra} canOperate onUpdated={jest.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: 'Vista previa etiqueta' }));
    await waitFor(() => {
      expect(screen.getByText('PEREZ J. | DNI 23123456')).toBeInTheDocument();
    });
    expect(screen.getByText(/Etiqueta 40 × 23 mm/)).toBeInTheDocument();
    expect(mockGetZpl).toHaveBeenCalledWith(42);
  });

  it('imprime con snackbar y bloquea doble submit', async () => {
    let resolvePrint: (v: unknown) => void = () => undefined;
    mockImprimir.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolvePrint = resolve;
        })
    );
    render(<MuestraAcciones muestra={baseMuestra} canOperate onUpdated={jest.fn()} />);
    const btn = screen.getByRole('button', { name: 'Imprimir etiqueta' });
    fireEvent.click(btn);
    fireEvent.click(btn);
    await waitFor(() => expect(mockImprimir).toHaveBeenCalledTimes(1));
    resolvePrint({ muestra_id: 42, profile: 'x', resultado: 'ok' });
    await waitFor(() => {
      expect(mockToast.success).toHaveBeenCalledWith('Etiqueta enviada a impresión');
    });
  });

  it('503 impresora no configurada', async () => {
    mockImprimir.mockRejectedValue({
      response: { status: 503, data: { error: 'Impresora de etiquetas no configurada' } },
    });
    render(<MuestraAcciones muestra={baseMuestra} canOperate onUpdated={jest.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: 'Imprimir etiqueta' }));
    await waitFor(() => {
      expect(mockToast.error).toHaveBeenCalledWith('Impresora de etiquetas no configurada');
    });
    const msg = String(mockToast.error.mock.calls[0][0]);
    expect(msg.toLowerCase()).not.toContain('zpl');
    expect(msg).not.toContain('PEREZ');
  });

  it('timeout ambiguo', async () => {
    mockImprimir.mockRejectedValue({
      response: {
        status: 503,
        data: {
          error: 'No se pudo confirmar la impresión. Verifique la impresora antes de reimprimir.',
        },
      },
    });
    render(<MuestraAcciones muestra={baseMuestra} canOperate onUpdated={jest.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: 'Imprimir etiqueta' }));
    await waitFor(() => {
      expect(mockToast.error).toHaveBeenCalledWith(
        'No se pudo confirmar la impresión. Verifique la impresora antes de reimprimir.'
      );
    });
  });

  it('error de red sin response → incertidumbre', async () => {
    mockImprimir.mockRejectedValue({ message: 'Network Error' });
    render(<MuestraAcciones muestra={baseMuestra} canOperate onUpdated={jest.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: 'Imprimir etiqueta' }));
    await waitFor(() => {
      expect(mockToast.error).toHaveBeenCalledWith(
        'No se pudo confirmar la impresión. Verifique la impresora antes de reimprimir.'
      );
    });
    const msg = String(mockToast.error.mock.calls[0][0]);
    expect(msg.toLowerCase()).not.toContain('intentá');
    expect(mockImprimir).toHaveBeenCalledTimes(1);
  });

  it('toma solicita lugar de extracción', async () => {
    const pendiente: MuestraTransaccional = { ...baseMuestra, estado: 'PENDIENTE_TOMA' };
    const onUpdated = jest.fn();
    render(<MuestraAcciones muestra={pendiente} canOperate onUpdated={onUpdated} />);
    fireEvent.click(screen.getByRole('button', { name: 'Tomar' }));
    const input = screen.getByLabelText('Lugar de extracción');
    fireEvent.change(input, { target: { value: 'GUARDIA' } });
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar toma' }));
    await waitFor(() => {
      expect(mockTomar).toHaveBeenCalledWith(42, { lugar_extraccion: 'GUARDIA' });
    });
    expect(onUpdated).toHaveBeenCalled();
  });
});
