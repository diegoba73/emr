import React from 'react';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import ConsultaAmbulatoriaForm from './ConsultaAmbulatoriaForm';

const theme = createTheme();
const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

jest.mock('../../hooks', () => ({
  useAtencionQuery: () => ({
    data: { id: 1, consulta_ambulatoria: null },
    isLoading: false,
  }),
  useSaveConsultaAmbulatoriaMutation: () => ({ mutateAsync: jest.fn(), isPending: false }),
}));

describe('ConsultaAmbulatoriaForm', () => {
  it('muestra pestañas SOAP', () => {
    render(
      <QueryClientProvider client={client}>
        <ThemeProvider theme={theme}>
          <ConsultaAmbulatoriaForm atencionId={1} canEdit />
        </ThemeProvider>
      </QueryClientProvider>
    );
    expect(screen.getByRole('tab', { name: /Anamnesis/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Examen físico/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Diagnóstico/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Plan/i })).toBeInTheDocument();
  });
});
