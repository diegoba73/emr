import React, { useState } from 'react';
import {
  Box,
  Button,
  Card,
  CardActions,
  CardContent,
  CircularProgress,
  Container,
  Stack,
  Typography,
} from '@mui/material';
import {
  LocalHospital,
  MedicalServices,
  Person,
  Science,
} from '@mui/icons-material';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useData } from '../contexts/DataContext';
import { useThemeMode } from '../contexts/ThemeModeContext';
import Logo from '../components/Logo';
import ThemeModeToggle from '../components/ThemeModeToggle';
import { getTourSteps } from '../demo/tourSteps';
import { authPageGradient } from '../theme/buildAppTheme';
import {
  DEMO_ACCOUNTS,
  type DemoTourRole,
} from '../demo/demoStorage';

const ROLE_ICONS: Record<DemoTourRole, React.ReactNode> = {
  medico: <MedicalServices fontSize="large" color="primary" />,
  laboratorio: <Science fontSize="large" color="primary" />,
  enfermeria: <LocalHospital fontSize="large" color="primary" />,
  paciente: <Person fontSize="large" color="primary" />,
};

const DemoLanding: React.FC = () => {
  const { mode } = useThemeMode();
  const { login, isLoading, logout, isAuthenticated } = useData();
  const navigate = useNavigate();
  const [busyRole, setBusyRole] = useState<DemoTourRole | null>(null);

  const startAs = async (role: DemoTourRole) => {
    const account = DEMO_ACCOUNTS[role];
    setBusyRole(role);
    try {
      if (isAuthenticated) {
        try {
          await logout();
        } catch {
          /* ignore */
        }
      }
      await login({ username: account.username, password: account.password }, { demoRole: role });
      toast.success(`Demo como ${account.label}`);
      navigate(role === 'paciente' ? '/portal' : '/dashboard', { replace: true });
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } }; message?: string };
      toast.error(
        err.response?.data?.detail ||
          err.message ||
          'No se pudo iniciar la demo. ¿Corriste ./emrctl seed y ./emrctl seed-demo?'
      );
    } finally {
      setBusyRole(null);
    }
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        background: authPageGradient(mode),
        py: 4,
        position: 'relative',
      }}
    >
      <Box sx={{ position: 'fixed', top: 16, right: 16, zIndex: 10 }}>
        <ThemeModeToggle inverse />
      </Box>
      <Container maxWidth="md">
        <Stack spacing={2} alignItems="center" sx={{ mb: 4, textAlign: 'center' }}>
          <Logo demo inverse size={160} />
          <Typography variant="h3" fontWeight={700} color="common.white">
            Explorá EMR Demo
          </Typography>
          <Typography variant="body1" color="rgba(255,255,255,0.9)" maxWidth={560}>
            Recorrido guiado con datos ficticios (MKTG). Elegí un rol para ingresar y arrancar el
            tour. Cada paso explica qué muestra la pantalla, para qué sirve y qué opciones ofrece tu rol.
          </Typography>
        </Stack>

        <Box
          sx={{
            display: 'grid',
            gap: 2,
            gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' },
          }}
        >
          {(Object.keys(DEMO_ACCOUNTS) as DemoTourRole[]).map((role) => {
            const account = DEMO_ACCOUNTS[role];
            const busy = busyRole === role;
            return (
              <Card
                key={role}
                elevation={6}
                sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}
              >
                <CardContent sx={{ flex: 1 }}>
                  <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 1 }}>
                    {ROLE_ICONS[role]}
                    <Typography variant="h6" fontWeight={700}>
                      {account.label}
                    </Typography>
                  </Stack>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                    {account.description}
                  </Typography>
                  <Typography variant="body2" color="primary" sx={{ mb: 1 }}>
                    {getTourSteps(role).length} pasos · Podés cerrar y reiniciar la guía
                  </Typography>
                  <Typography variant="caption" color="text.secondary" display="block">
                    Usuario: <strong>{account.username}</strong>
                  </Typography>
                  <Typography variant="caption" color="text.secondary" display="block">
                    Clave: <strong>{account.password}</strong>
                  </Typography>
                </CardContent>
                <CardActions sx={{ px: 2, pb: 2 }}>
                  <Button
                    fullWidth
                    variant="contained"
                    disabled={busy || isLoading || busyRole != null}
                    onClick={() => void startAs(role)}
                    startIcon={busy ? <CircularProgress size={18} color="inherit" /> : undefined}
                  >
                    {busy ? 'Ingresando…' : 'Ingresar y ver tour'}
                  </Button>
                </CardActions>
              </Card>
            );
          })}
        </Box>

        <Stack alignItems="center" sx={{ mt: 4 }}>
          <Button component={RouterLink} to="/login" variant="text" sx={{ color: 'common.white' }}>
            Volver al login
          </Button>
        </Stack>
      </Container>
    </Box>
  );
};

export default DemoLanding;
