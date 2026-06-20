import { createTheme, Theme } from '@mui/material/styles';

/**
 * Tema de aplicación (claro/oscuro). Los colores de marca se mantienen; se ajustan contraste y fondos.
 */
export function buildAppTheme(mode: 'light' | 'dark'): Theme {
  return createTheme({
    palette: {
      mode,
      primary:
        mode === 'light'
          ? { main: '#667eea', light: '#8fa4f3', dark: '#4a5fd8' }
          : { main: '#7c8ff0', light: '#9aa8f4', dark: '#5568c9' },
      secondary:
        mode === 'light'
          ? { main: '#764ba2', light: '#9a6bb8', dark: '#5a3a7a' }
          : { main: '#8a5db8', light: '#a37fc9', dark: '#6a4088' },
      background:
        mode === 'light'
          ? { default: '#f8fafc', paper: '#ffffff' }
          : { default: '#0f1419', paper: '#1a1f2e' },
    },
    typography: {
      fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
      h4: { fontWeight: 700 },
      h5: { fontWeight: 600 },
      h6: { fontWeight: 600 },
    },
    shape: {
      borderRadius: 12,
    },
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          body: (p: { theme: Theme }) => ({
            backgroundColor: p.theme.palette.background.default,
            color: p.theme.palette.text.primary,
          }),
        },
      },
      MuiButton: {
        styleOverrides: {
          root: {
            textTransform: 'none',
            fontWeight: 600,
            borderRadius: 8,
          },
        },
      },
      MuiCard: {
        styleOverrides: {
          root: (p: { theme: Theme }) => ({
            borderRadius: 12,
            boxShadow:
              p.theme.palette.mode === 'dark'
                ? '0 2px 12px 0 rgba(0,0,0,0.45)'
                : '0 2px 12px 0 rgba(0,0,0,0.1)',
            border: `1px solid ${
              p.theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)'
            }`,
          }),
        },
      },
    },
  });
}

export function authPageGradient(mode: 'light' | 'dark'): string {
  return mode === 'light'
    ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
    : 'linear-gradient(135deg, #1a1f2e 0%, #2d1b4e 100%)';
}
