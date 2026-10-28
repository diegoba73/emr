import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import TendenciaAnalitoDialog from './TendenciaAnalitoDialog';
import { getHistorialAnalitos } from '../../services/limsApi';

jest.mock('../../services/limsApi', () => ({
  getHistorialAnalitos: jest.fn(),
}));

const getHist = getHistorialAnalitos as jest.Mock;

describe('TendenciaAnalitoDialog', () => {
  beforeEach(() => {
    getHist.mockReset();
  });

  it('carga historial y muestra gráfica con ≥2 puntos numéricos', async () => {
    getHist.mockResolvedValue({
      solicitud_id: 9,
      paciente_id: 1,
      limit: 50,
      analitos: [
        {
          tipo_examen_id: 7,
          tipo_examen_codigo: 'TROP',
          tipo_examen_nombre: 'Troponina',
          previos: [
            {
              resultado_id: 1,
              valor: '10',
              valor_numerico: '10',
              unidad: 'ng/L',
              fecha: '2026-01-01T10:00:00Z',
              solicitud_id: 1,
              solicitud_numero: 'LAB-1',
            },
            {
              resultado_id: 2,
              valor: '20',
              valor_numerico: '20',
              unidad: 'ng/L',
              fecha: '2026-02-01T10:00:00Z',
              solicitud_id: 2,
              solicitud_numero: 'LAB-2',
            },
          ],
        },
      ],
    });

    render(
      <TendenciaAnalitoDialog
        open
        onClose={jest.fn()}
        solicitudId={9}
        tipoExamenId={7}
        tipoExamenNombre="Troponina"
        tipoExamenCodigo="TROP"
        actual={{
          valor: '35',
          valor_numerico: 35,
          unidad: 'ng/L',
          fecha: '2026-03-01T10:00:00Z',
          solicitudNumero: 'LAB-9',
          rango_min: 0,
          rango_max: 14,
        }}
      />
    );

    expect(screen.getByText(/Tendencia · Troponina/)).toBeInTheDocument();
    await waitFor(() => expect(getHist).toHaveBeenCalledWith(9, 50));
    await waitFor(() => expect(screen.getByRole('img', { name: /Tendencia/i })).toBeInTheDocument());
    expect(screen.getByText('LAB-1')).toBeInTheDocument();
    expect(screen.getByText('LAB-9')).toBeInTheDocument();
    expect(screen.getAllByText((_, node) => (node?.textContent || '').includes('35 ng/L')).length).toBeGreaterThan(0);
  });

  it('sin numéricos suficientes muestra aviso y tabla', async () => {
    getHist.mockResolvedValue({
      solicitud_id: 9,
      paciente_id: 1,
      limit: 50,
      analitos: [
        {
          tipo_examen_id: 7,
          tipo_examen_codigo: 'HIV',
          tipo_examen_nombre: 'HIV',
          previos: [
            {
              resultado_id: 1,
              valor: 'Negativo',
              valor_numerico: null,
              unidad: null,
              fecha: '2026-01-01T10:00:00Z',
              solicitud_id: 1,
              solicitud_numero: 'LAB-1',
            },
          ],
        },
      ],
    });

    render(
      <TendenciaAnalitoDialog
        open
        onClose={jest.fn()}
        solicitudId={9}
        tipoExamenId={7}
        tipoExamenNombre="HIV"
        actual={{ valor: 'Positivo', valor_numerico: null }}
      />
    );

    await waitFor(() =>
      expect(screen.getByText(/no tiene valores numéricos suficientes/i)).toBeInTheDocument()
    );
    expect(screen.getByText('Negativo')).toBeInTheDocument();
    expect(screen.queryByRole('img', { name: /Tendencia/i })).not.toBeInTheDocument();
  });

  it('cerrar dispara onClose', async () => {
    getHist.mockResolvedValue({
      solicitud_id: 9,
      paciente_id: 1,
      limit: 50,
      analitos: [],
    });
    const onClose = jest.fn();
    render(
      <TendenciaAnalitoDialog
        open
        onClose={onClose}
        solicitudId={9}
        tipoExamenId={7}
        tipoExamenNombre="Troponina"
      />
    );
    await userEvent.click(screen.getByRole('button', { name: 'Cerrar' }));
    expect(onClose).toHaveBeenCalled();
  });
});
