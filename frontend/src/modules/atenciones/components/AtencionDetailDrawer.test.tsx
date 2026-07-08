import React from 'react';
import { render, screen, within, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import AtencionDetailDrawer from './AtencionDetailDrawer';
import type { User } from '../../../types';

const theme = createTheme();
const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

const mockAtencion = {
  id: 1,
  tipo_intervencion: 'CONSULTA',
  estado_clinico: 'ABIERTA',
  fecha_admision: '2026-01-15T10:00:00Z',
  fecha_cierre: null,
  paciente: { id: 10, nombre: 'Ana', apellido: 'Paciente', dni: '12345678' },
  medico_principal: { id: 20, nombre: 'Med', apellido: 'Uno' },
  consulta_ambulatoria: null,
  documentos: [],
};

jest.mock('../hooks', () => ({
  useAtencionQuery: () => ({
    data: mockAtencion,
    isLoading: false,
    isError: false,
    error: null,
  }),
  useAtencionesQuery: () => ({ data: { results: [] } }),
}));

jest.mock('./forms/ConsultaAmbulatoriaForm', () => ({
  __esModule: true,
  default: ({ canEdit }: { canEdit: boolean }) => (
    <div data-testid="consulta-form">{canEdit ? 'EDIT-ENABLED' : 'EDIT-DISABLED'}</div>
  ),
}));

jest.mock('./DocumentosAdjuntos', () => ({
  __esModule: true,
  default: ({ canEdit }: { canEdit: boolean; atencionId: number; pacienteId: number }) => (
    <div data-testid="archivos-panel">{canEdit ? 'UPLOAD-ENABLED' : 'UPLOAD-DISABLED'}</div>
  ),
}));

jest.mock('../../../contexts/DataContext', () => ({
  useData: jest.fn(),
}));

const { useData } = jest.requireMock('../../../contexts/DataContext');

function mockUser(overrides: Partial<User> & Pick<User, 'rol'>): User {
  return {
    id: 1,
    username: 'u',
    email: 'u@test.com',
    first_name: 'U',
    last_name: 'T',
    is_active: true,
    is_superuser: false,
    is_staff: false,
    ...overrides,
  };
}

function renderDrawer(user: User | null, canOperate?: boolean) {
  useData.mockReturnValue({ currentUser: user });
  return render(
    <QueryClientProvider client={client}>
      <ThemeProvider theme={theme}>
        <AtencionDetailDrawer
          atencionId={1}
          open
          onClose={jest.fn()}
          currentUser={user}
          canOperate={canOperate}
        />
      </ThemeProvider>
    </QueryClientProvider>
  );
}

describe('AtencionDetailDrawer — permisos QA-ROLE-01', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('enfermería ve el drawer en solo lectura', () => {
    renderDrawer(mockUser({ rol: 'ENFERMERIA' }), false);

    expect(screen.getByText('Detalle de la Atención')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: /Archivos/i }));
    expect(screen.getByTestId('archivos-panel')).toHaveTextContent('UPLOAD-DISABLED');

    fireEvent.click(screen.getByRole('tab', { name: /Detalle clínico/i }));
    expect(screen.getByTestId('consulta-form')).toHaveTextContent('EDIT-DISABLED');
  });

  it('paciente ve el drawer propio en solo lectura', () => {
    renderDrawer(mockUser({ rol: 'PACIENTE' }), false);

    fireEvent.click(screen.getByRole('tab', { name: /Archivos/i }));
    expect(within(screen.getByTestId('archivos-panel')).getByText('UPLOAD-DISABLED')).toBeInTheDocument();
  });

  it('médico ve controles de edición', () => {
    renderDrawer(mockUser({ rol: 'MEDICO' }));

    fireEvent.click(screen.getByRole('tab', { name: /Archivos/i }));
    expect(screen.getByTestId('archivos-panel')).toHaveTextContent('UPLOAD-ENABLED');

    fireEvent.click(screen.getByRole('tab', { name: /Detalle clínico/i }));
    expect(screen.getByTestId('consulta-form')).toHaveTextContent('EDIT-ENABLED');
  });

  it('admin ve controles de edición', () => {
    renderDrawer(mockUser({ rol: 'ADMIN' }));

    fireEvent.click(screen.getByRole('tab', { name: /Detalle clínico/i }));
    expect(screen.getByTestId('consulta-form')).toHaveTextContent('EDIT-ENABLED');
  });
});
