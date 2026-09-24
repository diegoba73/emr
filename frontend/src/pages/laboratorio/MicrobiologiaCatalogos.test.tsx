import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import MicrobiologiaCatalogos from './MicrobiologiaCatalogos';

const mockListMedios = jest.fn();
const mockListMicros = jest.fn();
const mockListAbs = jest.fn();
const mockListFrases = jest.fn();
const mockCreateMedio = jest.fn();
const mockUpdateMedio = jest.fn();

jest.mock('../../services/limsApi', () => ({
  listMediosCultivo: (...args: unknown[]) => mockListMedios(...args),
  listMicroorganismos: (...args: unknown[]) => mockListMicros(...args),
  listAntibioticos: (...args: unknown[]) => mockListAbs(...args),
  listFrasesRapidasMicro: (...args: unknown[]) => mockListFrases(...args),
  createMedioCultivo: (...args: unknown[]) => mockCreateMedio(...args),
  createMicroorganismo: jest.fn(),
  createAntibiotico: jest.fn(),
  createFraseRapidaMicro: jest.fn(),
  updateMedioCultivo: (...args: unknown[]) => mockUpdateMedio(...args),
  updateMicroorganismo: jest.fn(),
  updateAntibiotico: jest.fn(),
  updateFraseRapidaMicro: jest.fn(),
}));

jest.mock('../../contexts/DataContext', () => ({
  useData: () => ({
    currentUser: { rol: 'LABORATORIO', username: 'lab1', is_superuser: false },
  }),
}));

jest.mock('react-hot-toast', () => ({
  __esModule: true,
  default: { error: jest.fn(), success: jest.fn() },
}));

describe('MicrobiologiaCatalogos', () => {
  beforeEach(() => {
    mockListMedios.mockResolvedValue([
      { id: 1, codigo: 'AGS', nombre: 'Agar sangre', tipo: 'solido', activo: true },
    ]);
    mockListMicros.mockResolvedValue([]);
    mockListAbs.mockResolvedValue([]);
    mockListFrases.mockResolvedValue([]);
    mockCreateMedio.mockResolvedValue({ id: 2, codigo: 'MCA', nombre: 'MacConkey', activo: true });
    mockUpdateMedio.mockResolvedValue({ id: 1, codigo: 'AGS', nombre: 'Agar sangre', activo: false });
  });

  it('laboratorio puede agregar, editar y eliminar un medio', async () => {
    render(
      <MemoryRouter>
        <MicrobiologiaCatalogos />
      </MemoryRouter>
    );

    expect(await screen.findByRole('button', { name: /nuevo medio/i })).toBeInTheDocument();
    expect(await screen.findByLabelText('Editar Agar sangre')).toBeInTheDocument();
    expect(screen.getByLabelText('Eliminar Agar sangre')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /nuevo medio/i }));
    expect(await screen.findByRole('heading', { name: /nuevo medio/i })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/^código/i), { target: { value: 'MCA' } });
    fireEvent.change(screen.getByLabelText(/^nombre/i), { target: { value: 'MacConkey' } });
    fireEvent.click(screen.getByRole('button', { name: /guardar/i }));

    await waitFor(() => {
      expect(mockCreateMedio).toHaveBeenCalledWith(
        expect.objectContaining({ codigo: 'MCA', nombre: 'MacConkey', activo: true })
      );
    });

    fireEvent.click(screen.getByLabelText('Eliminar Agar sangre'));
    expect(await screen.findByRole('heading', { name: /eliminar medio/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /^eliminar$/i }));

    await waitFor(() => {
      expect(mockUpdateMedio).toHaveBeenCalledWith(1, { activo: false });
    });
  });
});
