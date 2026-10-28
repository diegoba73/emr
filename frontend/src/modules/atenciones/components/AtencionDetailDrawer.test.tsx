import React from 'react';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
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
}));

jest.mock('./forms/ConsultaAmbulatoriaForm', () => ({
  __esModule: true,
  default: ({ canEdit }: { canEdit: boolean }) => (
    <div data-testid="consulta-form">{canEdit ? 'EDIT-ENABLED' : 'EDIT-DISABLED'}</div>
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
    <MemoryRouter>
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
    </MemoryRouter>
  );
}

describe('AtencionDetailDrawer — permisos QA-ROLE-01', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('enfermería ve el drawer en solo lectura', () => {
    renderDrawer(mockUser({ rol: 'ENFERMERIA' }), false);

    expect(screen.getByText('Detalle de la Atención')).toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: /Resumen/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: /Archivos/i })).not.toBeInTheDocument();
    expect(screen.getByTestId('consulta-form')).toHaveTextContent('EDIT-DISABLED');
  });

  it('paciente ve el drawer propio en solo lectura', () => {
    renderDrawer(mockUser({ rol: 'PACIENTE' }), false);
    expect(screen.getByTestId('consulta-form')).toHaveTextContent('EDIT-DISABLED');
  });

  it('médico ve controles de edición', () => {
    renderDrawer(mockUser({ rol: 'MEDICO' }));
    expect(screen.getByTestId('consulta-form')).toHaveTextContent('EDIT-ENABLED');
  });

  it('admin ve controles de edición', () => {
    renderDrawer(mockUser({ rol: 'ADMIN' }));
    expect(screen.getByTestId('consulta-form')).toHaveTextContent('EDIT-ENABLED');
  });
});
