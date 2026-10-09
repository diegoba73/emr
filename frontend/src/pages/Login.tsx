import Logo from '../components/Logo';
import React, { useState } from 'react';
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  Container,
  CircularProgress,
  InputAdornment,
  IconButton,
  Link as MuiLink,
  Divider,
} from '@mui/material';
import {
  Visibility,
  VisibilityOff,
  Login as LoginIcon,
  MedicalServices,
  PhoneAndroid,
} from '@mui/icons-material';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import toast from 'react-hot-toast';
import { useData } from '../contexts/DataContext';
import { authService } from '../services/auth';
import { isPacienteRole } from '../utils/navLabels';
import { useThemeMode } from '../contexts/ThemeModeContext';
import ThemeModeToggle from '../components/ThemeModeToggle';
import { authPageGradient } from '../theme/buildAppTheme';
import { consumeDemoPrefillUsername } from '../demo/demoStorage';

/** Descarga pública del APK (Android). Sobrescribible por env en builds. */
const MOVIL_APK_URL =
  process.env.REACT_APP_MOVIL_APK_URL ||
  'https://emr.icpueblodeluis.com.ar:8080/synesis-movil.apk';

// Esquema de validación con Yup
const loginSchema = yup.object({
  username: yup
    .string()
    .required('El DNI o usuario es requerido')
    .min(3, 'El DNI o usuario debe tener al menos 3 caracteres'),
  password: yup
    .string()
    .required('La contraseña es requerida')
    .min(6, 'La contraseña debe tener al menos 6 caracteres'),
});

type LoginFormData = yup.InferType<typeof loginSchema>;

const isDemoMode = process.env.REACT_APP_DEMO_MODE === 'true';

const Login: React.FC = () => {
  const [showPassword, setShowPassword] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isLoading } = useData();
  const { mode } = useThemeMode();

  const redirectAfterLogin = (() => {
    const from = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname;
    if (from && from.startsWith('/') && !from.startsWith('//') && from !== '/login') {
      return from;
    }
    return null;
  })();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({
    resolver: yupResolver(loginSchema),
    defaultValues: {
      username: consumeDemoPrefillUsername(),
      password: '',
    },
  });

  const onSubmit = async (data: LoginFormData) => {
    try {
      await login({ username: data.username, password: data.password });
      toast.success('Inicio de sesión exitoso');
      const user = await authService.getCurrentUser();
      if (isPacienteRole(user)) {
        navigate('/portal', { replace: true });
        return;
      }
      navigate(redirectAfterLogin || '/dashboard', { replace: true });

    } catch (error: any) {
      const errorMessage =
        error.response?.data?.detail ||
        error.message ||
        'Credenciales inválidas. Por favor, intente nuevamente.';
      toast.error(errorMessage);
    }
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: authPageGradient(mode),
        padding: 2,
        position: 'relative',
      }}
    >
      <Box sx={{ position: 'fixed', top: 16, right: 16, zIndex: 10 }}>
        <ThemeModeToggle inverse />
      </Box>
      <Container maxWidth="sm">
        <Paper
          elevation={24}
          sx={{
            padding: 4,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            borderRadius: 3,
          }}
        >
          {/* Identidad genérica en el despliegue demo. */}
          {isDemoMode ? (
            <Box sx={{ mb: 3 }}><Logo demo size={150} /></Box>
          ) : (
          <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
            <MedicalServices sx={{ fontSize: 40, color: 'primary.main' }} />
            <Typography variant="h4" component="h1" fontWeight="bold">
              Synesis EMR
            </Typography>
          </Box>
          )}

          <Typography variant="h6" color="text.secondary" gutterBottom>
            Iniciar Sesión
          </Typography>

          <Box
            component="form"
            onSubmit={handleSubmit(onSubmit)}
            sx={{ width: '100%', mt: 3 }}
          >
            <TextField
              {...register('username')}
              fullWidth
              label="DNI / Usuario"
              margin="normal"
              autoComplete="username"
              autoFocus
              error={!!errors.username}
              helperText={errors.username?.message || 'Ingresa tu DNI o nombre de usuario'}
              disabled={isSubmitting || isLoading}
            />

            <TextField
              {...register('password')}
              fullWidth
              label="Contraseña"
              type={showPassword ? 'text' : 'password'}
              margin="normal"
              autoComplete="current-password"
              error={!!errors.password}
              helperText={errors.password?.message}
              disabled={isSubmitting || isLoading}
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      aria-label="toggle password visibility"
                      onClick={() => setShowPassword(!showPassword)}
                      edge="end"
                      disabled={isSubmitting || isLoading}
                    >
                      {showPassword ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />

            <Button
              type="submit"
              fullWidth
              variant="contained"
              sx={{ mt: 3, mb: 2, py: 1.5 }}
              disabled={isSubmitting || isLoading}
              startIcon={
                isSubmitting || isLoading ? (
                  <CircularProgress size={20} color="inherit" />
                ) : (
                  <LoginIcon />
                )
              }
            >
              {isSubmitting || isLoading ? 'Iniciando sesión...' : 'Ingresar'}
            </Button>

            <Button
              component={Link}
              to="/demo"
              fullWidth
              variant="outlined"
              sx={{ mb: 2, py: 1.25 }}
              disabled={isSubmitting || isLoading}
            >
              Probar demo guiada
            </Button>

            <Box sx={{ textAlign: 'center', mt: 2 }}>
              <MuiLink
                component={Link}
                to="/register"
                variant="body2"
                sx={{ textDecoration: 'none' }}
              >
                ¿No tienes cuenta? Regístrate aquí
              </MuiLink>
            </Box>
          </Box>

          {!isDemoMode && (
            <>
              <Divider sx={{ width: '100%', my: 3 }} />
              <Box
                sx={{
                  width: '100%',
                  display: 'flex',
                  flexDirection: { xs: 'column', sm: 'row' },
                  alignItems: 'center',
                  gap: 2,
                  textAlign: { xs: 'center', sm: 'left' },
                }}
              >
                <Box
                  component="a"
                  href={MOVIL_APK_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label="Descargar aplicación móvil SYNESIS para Android"
                  sx={{
                    flexShrink: 0,
                    p: 1,
                    borderRadius: 2,
                    bgcolor: 'common.white',
                    border: 1,
                    borderColor: 'divider',
                    lineHeight: 0,
                  }}
                >
                  <Box
                    component="img"
                    src={`${process.env.PUBLIC_URL || ''}/qr-synesis-movil.png`}
                    alt="Código QR para instalar SYNESIS móvil"
                    sx={{ width: 120, height: 120, display: 'block' }}
                  />
                </Box>
                <Box sx={{ flex: 1 }}>
                  <Typography
                    variant="subtitle2"
                    fontWeight={700}
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 0.75,
                      justifyContent: { xs: 'center', sm: 'flex-start' },
                    }}
                  >
                    <PhoneAndroid fontSize="small" color="primary" />
                    Aplicación móvil
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                    Escaneá el código QR con tu teléfono Android para descargar e instalar
                    SYNESIS. Luego abrí la app, ingresá el código de clínica{' '}
                    <strong>ICPL</strong> o <strong>CEHTA</strong> y utilizá las mismas
                    credenciales de acceso.
                  </Typography>
                  <MuiLink
                    href={MOVIL_APK_URL}
                    target="_blank"
                    rel="noopener noreferrer"
                    variant="body2"
                    sx={{ display: 'inline-block', mt: 1 }}
                  >
                    Descargar para Android
                  </MuiLink>
                </Box>
              </Box>
            </>
          )}
        </Paper>
      </Container>
    </Box>
  );
};

export default Login;
