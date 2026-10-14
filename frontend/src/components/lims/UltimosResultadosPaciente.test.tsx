import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import UltimosResultadosPaciente from './UltimosResultadosPaciente';

const mockGet = jest.fn();

jest.mock('../../services/limsApi', () => ({
  getUltimosResultadosPaciente: (...args: unknown[]) => mockGet(...args),
}));

jest.mock('../../contexts/DataContext', () => ({
  useData: () => ({
    currentUser: { rol: 'MEDICO', username: 'med1', is_superuser: false },
  }),
}));

describe('UltimosResultadosPaciente', () => {
  beforeEach(() => {
    mockGet.mockResolvedValue({
      paciente_id: 7,
      dias: 7,
      limit: 200,
      total: 1,
      items: [
        {
          tipo_examen_id: 1,
          tipo_examen_codigo: 'GLU',
          tipo_examen_nombre: 'Glucosa',
          resultado_id: 10,
          valor: '128',
          unidad: 'mg/dL',
          fecha: '2026-10-01T12:00:00Z',
          solicitud_id: 42,
          solicitud_numero: 'LAB-2026-00042',
          tendencia: 'sube',
          valor_anterior: '110',
          fecha_anterior: '2026-09-01T12:00:00Z',
        },
      ],
    });
  });

  it('muestra últimos valores del paciente', async () => {
    render(
      <MemoryRouter>
        <UltimosResultadosPaciente pacienteId={7} compact={false} />
      </MemoryRouter>
    );

    expect(await screen.findByText('Glucosa')).toBeInTheDocument();
    expect(screen.getByText(/128/)).toBeInTheDocument();
    expect(screen.getByText(/Últimos resultados \(7 días\)/)).toBeInTheDocument();
    await waitFor(() =>
      expect(mockGet).toHaveBeenCalledWith(7, { dias: 7, limit: 200 })
    );
  });

  it('mensaje vacío si no hay historial', async () => {
    mockGet.mockResolvedValueOnce({
      paciente_id: 7,
      dias: 7,
      limit: 200,
      total: 0,
      items: [],
    });
    render(
      <MemoryRouter>
        <UltimosResultadosPaciente pacienteId={7} compact={false} />
      </MemoryRouter>
    );
    expect(
      await screen.findByText(/Sin resultados previos informados/i)
    ).toBeInTheDocument();
  });
});
