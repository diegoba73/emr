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
} from '@mui/material';
import {
  Visibility,
  VisibilityOff,
  Login as LoginIcon,
  MedicalServices,
} from '@mui/icons-material';
import { useNavigate, Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import toast from 'react-hot-toast';
import { useData } from '../contexts/DataContext';
import { useThemeMode } from '../contexts/ThemeModeContext';
import ThemeModeToggle from '../components/ThemeModeToggle';
import { authPageGradient } from '../theme/buildAppTheme';

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

const Login: React.FC = () => {
  const [showPassword, setShowPassword] = useState(false);
  const navigate = useNavigate();
  const { login, isLoading } = useData();
  const { mode } = useThemeMode();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({
    resolver: yupResolver(loginSchema),
    defaultValues: {
      username: '',
      password: '',
    },
  });

  const onSubmit = async (data: LoginFormData) => {
    try {
      await login({ username: data.username, password: data.password });
      toast.success('Inicio de sesión exitoso');
      navigate('/dashboard', { replace: true });
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
          {/* Logo */}
          <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
            <MedicalServices sx={{ fontSize: 40, color: 'primary.main' }} />
            <Typography variant="h4" component="h1" fontWeight="bold">
              Synesis EMR
            </Typography>
          </Box>

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
        </Paper>
      </Container>
    </Box>
  );
};

export default Login;
