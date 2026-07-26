import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import ConsultaAmbulatoriaForm from './ConsultaAmbulatoriaForm';

const theme = createTheme();
const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
const mockMutateAsync = jest.fn().mockResolvedValue({ id: 1 });
const mockCloseAsync = jest.fn().mockResolvedValue({ id: 1 });

let mockAtencion: Record<string, unknown> = {
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
    sessionStorage.clear();
    mockAtencion = {
      id: 1,
      estado_clinico: 'ABIERTA',
      fecha_cierre: null,
      consulta_ambulatoria: null,
    };
  });

  it('muestra pestañas SOAP', () => {
    renderForm();
    expect(screen.getByRole('tab', { name: /Anamnesis/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Examen físico/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Diagnóstico/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Plan/i })).toBeInTheDocument();
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
    expect(screen.getByRole('tab', { name: /Examen físico/i })).toBeInTheDocument();
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
});
