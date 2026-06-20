import React, { useMemo } from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import Login from './Login';
import { DataProvider } from '../contexts/DataContext';
import { ThemeModeProvider, useThemeMode } from '../contexts/ThemeModeContext';
import { buildAppTheme } from '../theme/buildAppTheme';

jest.mock('../services/auth', () => ({
  authService: {
    login: jest.fn(),
    logout: jest.fn(),
    getCurrentUser: jest.fn(),
  },
}));

jest.mock('react-hot-toast', () => ({
  __esModule: true,
  default: {
    success: jest.fn(),
    error: jest.fn(),
  },
}));

const LoginTestTheme: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { mode } = useThemeMode();
  const theme = useMemo(() => buildAppTheme(mode), [mode]);
  return <ThemeProvider theme={theme}>{children}</ThemeProvider>;
};

const renderWithProviders = (ui: React.ReactElement) => {
  return render(
    <ThemeModeProvider>
      <LoginTestTheme>
        <BrowserRouter>
          <DataProvider>{ui}</DataProvider>
        </BrowserRouter>
      </LoginTestTheme>
    </ThemeModeProvider>
  );
};

describe('Login', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('debe renderizar el formulario de login', () => {
    renderWithProviders(<Login />);

    expect(screen.getByLabelText(/usuario/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/contraseña/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /ingresar/i })).toBeInTheDocument();
  });

  it('debe mostrar mensajes de validación cuando se envía el formulario vacío', async () => {
    renderWithProviders(<Login />);

    await userEvent.click(screen.getByRole('button', { name: /ingresar/i }));

    await waitFor(() => {
      expect(screen.getByText(/DNI o usuario es requerido/i)).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByText(/la contraseña es requerida/i)).toBeInTheDocument();
    });
  });

  it('debe mostrar mensaje de validación cuando el usuario tiene menos de 3 caracteres', async () => {
    renderWithProviders(<Login />);

    await userEvent.type(screen.getByLabelText(/usuario/i), 'ab');
    await userEvent.click(screen.getByRole('button', { name: /ingresar/i }));

    await waitFor(
      () => {
        expect(
          screen.getByText(/DNI o usuario debe tener al menos 3 caracteres/i)
        ).toBeInTheDocument();
      },
      { timeout: 5000 }
    );
  });

  it('debe mostrar mensaje de validación cuando la contraseña tiene menos de 6 caracteres', async () => {
    renderWithProviders(<Login />);

    await userEvent.type(screen.getByLabelText(/contraseña/i), '12345');
    await userEvent.click(screen.getByRole('button', { name: /ingresar/i }));

    await waitFor(() => {
      expect(screen.getByText(/la contraseña debe tener al menos 6 caracteres/i)).toBeInTheDocument();
    });
  });

  it('debe permitir alternar la visibilidad de la contraseña', async () => {
    renderWithProviders(<Login />);

    const passwordInput = screen.getByLabelText(/contraseña/i) as HTMLInputElement;
    const toggleButton = screen.getByLabelText(/toggle password visibility/i);

    expect(passwordInput.type).toBe('password');

    await userEvent.click(toggleButton);
    await waitFor(() => {
      expect(passwordInput.type).toBe('text');
    });

    await userEvent.click(toggleButton);
    await waitFor(() => {
      expect(passwordInput.type).toBe('password');
    });
  });

  it('debe tener un enlace a la página de registro', () => {
    renderWithProviders(<Login />);

    const registerLink = screen.getByRole('link', { name: /regístrate aquí/i });
    expect(registerLink).toBeInTheDocument();
    expect(registerLink).toHaveAttribute('href', '/register');
  });
});
