import React, { useMemo } from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import AppLayout from './AppLayout';
import { ThemeModeProvider, useThemeMode } from '../../contexts/ThemeModeContext';
import { buildAppTheme } from '../../theme/buildAppTheme';

jest.mock('../../contexts/DataContext', () => ({
  __esModule: true,
  DataProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useData: () => ({
    currentUser: { rol: 'MEDICO', first_name: 'T', last_name: 'E', username: 'te' },
    logout: jest.fn().mockResolvedValue(undefined),
  }),
}));

const TestTheme: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { mode } = useThemeMode();
  const theme = useMemo(() => buildAppTheme(mode), [mode]);
  return <ThemeProvider theme={theme}>{children}</ThemeProvider>;
};

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

const Placeholder: React.FC = () => <div>Contenido de prueba</div>;

describe('AppLayout', () => {
  it('renderiza el área principal con Outlet', () => {
    render(
      <ThemeModeProvider>
        <QueryClientProvider client={queryClient}>
          <TestTheme>
            <MemoryRouter initialEntries={['/dashboard']}>
              <Routes>
                <Route element={<AppLayout />}>
                  <Route path="dashboard" element={<Placeholder />} />
                </Route>
              </Routes>
            </MemoryRouter>
          </TestTheme>
        </QueryClientProvider>
      </ThemeModeProvider>
    );
    expect(screen.getByText('Contenido de prueba')).toBeInTheDocument();
  });
});
