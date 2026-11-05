import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import ConsultaAmbulatoriaForm from './ConsultaAmbulatoriaForm';

const theme = createTheme();
const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
const mockMutateAsync = jest.fn().mockResolvedValue({ id: 1 });
const mockCloseAsync = jest.fn().mockResolvedValue({ id: 1 });
const mockMarcarAtendido = jest.fn().mockResolvedValue({ ok: true, actualizado: true });

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let mockAtencion: any = {
  id: 1,
  estado_clinico: 'ABIERTA',
  fecha_cierre: null,
  consulta_ambulatoria: null,
};

jest.mock('../../hooks', () => ({
  useAtencionQuery: () => ({
    data: mockAtencion,
    isLoading: false,
    isFetching: false,
  }),
  useSaveConsultaAmbulatoriaMutation: () => ({ mutateAsync: mockMutateAsync, isPending: false }),
  useCloseAtencionMutation: () => ({ mutateAsync: mockCloseAsync, isPending: false }),
}));

jest.mock('../../../../services/recepcionApi', () => ({
  marcarAtendidoPorTurno: (...args: unknown[]) => mockMarcarAtendido(...args),
}));

jest.mock('../../../../services/pacienteProblemas', () => ({
  establecerProblemaPrincipal: jest.fn().mockResolvedValue({}),
}));

jest.mock('../../consultaPedidosDraft', () => ({
  flushConsultaPedidosDrafts: jest.fn().mockResolvedValue(undefined),
}));

jest.mock('../AtencionPedidosSection', () => {
  const R = require('react');
  return {
    __esModule: true,
    default: () => R.createElement('div', { 'data-testid': 'pedidos-section' }, 'Pedidos mock'),
  };
});

jest.mock('../../../../components/clinical/SignosVitalesPanel', () => {
  const R = require('react');
  return {
    __esModule: true,
    default: () => R.createElement('div', { 'data-testid': 'signos-vitales' }, 'Signos mock'),
  };
});

function renderForm(props: Partial<React.ComponentProps<typeof ConsultaAmbulatoriaForm>> = {}) {
  return render(
    <QueryClientProvider client={client}>
      <ThemeProvider theme={theme}>
        <ConsultaAmbulatoriaForm atencionId={1} canEdit {...props} />
      </ThemeProvider>
    </QueryClientProvider>
  );
}

describe('ConsultaAmbulatoriaForm', () => {
  beforeEach(() => {
    mockMutateAsync.mockClear();
    mockCloseAsync.mockClear();
    mockMarcarAtendido.mockClear();
    sessionStorage.clear();
    mockAtencion = {
      id: 1,
      estado_clinico: 'ABIERTA',
      fecha_cierre: null,
      consulta_ambulatoria: null,
    };
  });

  it('muestra solo Detalle clínico y Pedidos y resultados', () => {
    renderForm();
    expect(screen.getByRole('tab', { name: /Detalle clínico/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Pedidos y resultados/i })).toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: /^Anamnesis$/i })).not.toBeInTheDocument();
  });

  it('permite editar cuando existe consulta vacía creada al iniciar atención', async () => {
    mockAtencion = {
      id: 1,
      estado_clinico: 'ABIERTA',
      fecha_cierre: null,
      consulta_ambulatoria: { id: 99 },
    };

    renderForm();

    const anamnesis = screen.getByLabelText(/Anamnesis/i);
    expect(anamnesis).not.toBeDisabled();
    await userEvent.type(anamnesis, 'Paciente refiere dolor torácico');
    expect(anamnesis).toHaveValue('Paciente refiere dolor torácico');
    expect(screen.getByRole('button', { name: /Guardar/i })).toBeEnabled();
  });

  it('bloquea edición cuando la atención está finalizada', () => {
    mockAtencion = {
      id: 1,
      estado_clinico: 'FINALIZADA',
      fecha_cierre: '2026-01-20T12:00:00Z',
      consulta_ambulatoria: {
        id: 99,
        anamnesis: 'Consulta previa',
      },
    };

    renderForm();

    expect(screen.getByText(/Atención finalizada/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Anamnesis/i)).toBeDisabled();
    expect(screen.queryByRole('button', { name: /Guardar/i })).not.toBeInTheDocument();
  });

  it('bloquea edición cuando canEdit es false', () => {
    mockAtencion = {
      id: 1,
      estado_clinico: 'ABIERTA',
      fecha_cierre: null,
      consulta_ambulatoria: { id: 99 },
    };

    renderForm({ canEdit: false });

    expect(screen.getByText(/Tu rol no puede modificar/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Anamnesis/i)).toBeDisabled();
  });

  it('muestra campos clínicos del servidor al reabrir', () => {
    mockAtencion = {
      id: 1,
      estado_clinico: 'FINALIZADA',
      fecha_cierre: '2026-01-20T12:00:00Z',
      consulta_ambulatoria: {
        id: 1,
        atencion_id: 1,
        anamnesis: 'Dolor precordial de 2 horas',
        examen_fisico: 'Ruidos cardíacos normales',
        plan_manejo: 'ECG y enzimas',
      },
    };

    renderForm();

    expect(screen.getByLabelText(/Anamnesis/i)).toHaveValue('Dolor precordial de 2 horas');
    expect(screen.getByLabelText(/Examen físico/i)).toHaveValue('Ruidos cardíacos normales');
    expect(screen.getByRole('tab', { name: /Detalle clínico/i })).toBeInTheDocument();
  });

  it('no deja que un borrador vacío pise datos del servidor', () => {
    sessionStorage.setItem(
      'consulta-amb-borrador-1',
      JSON.stringify({
        anamnesis: '',
        examen_fisico: '',
        diagnostico_presuntivo: '',
        plan_manejo: '',
        antecedentes_relevantes: '',
        alergias: '',
        medicacion_actual: '',
        diagnostico_definitivo: '',
        observaciones_medicas: '',
      })
    );
    mockAtencion = {
      id: 1,
      estado_clinico: 'ABIERTA',
      fecha_cierre: null,
      consulta_ambulatoria: {
        id: 1,
        anamnesis: 'Contenido persistido en BD',
        plan_manejo: 'Seguimiento',
      },
    };

    renderForm();

    expect(screen.getByLabelText(/Anamnesis/i)).toHaveValue('Contenido persistido en BD');
  });

  it('al guardar y cerrar marca la llegada del turno como atendida', async () => {
    mockAtencion = {
      id: 1,
      estado_clinico: 'ABIERTA',
      fecha_cierre: null,
      turno_id: 42,
      consulta_ambulatoria: { id: 99 },
    };
    mockMutateAsync.mockResolvedValue({
      id: 99,
      atencion_id: 1,
      anamnesis: 'Motivo de consulta',
      examen_fisico: 'Examen ok',
      plan_manejo: 'Alta',
    });

    const { container } = renderForm();

    fireEvent.change(screen.getByLabelText(/Anamnesis/i), {
      target: { value: 'Motivo de consulta' },
    });
    fireEvent.change(screen.getByLabelText(/Examen físico/i), {
      target: { value: 'Examen ok' },
    });
    fireEvent.change(screen.getByLabelText(/Plan de manejo/i), {
      target: { value: 'Alta' },
    });
    fireEvent.submit(container.querySelector('form')!);

    await waitFor(() => {
      expect(mockCloseAsync).toHaveBeenCalledWith(1);
    });
    expect(mockMarcarAtendido).toHaveBeenCalledWith(42);
  });
});
