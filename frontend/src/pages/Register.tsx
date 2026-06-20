import React from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  Container,
  CircularProgress,
  Link as MuiLink,
} from '@mui/material';
import { MedicalServices } from '@mui/icons-material';
import toast from 'react-hot-toast';
import { apiService } from '../services/api';
import { useThemeMode } from '../contexts/ThemeModeContext';
import ThemeModeToggle from '../components/ThemeModeToggle';
import { authPageGradient } from '../theme/buildAppTheme';

// Esquema de validación con Yup
const registerSchema = yup.object({
  email: yup
    .string()
    .email('Debe ser un email válido')
    .required('El email es requerido'),
  password: yup
    .string()
    .min(8, 'La contraseña debe tener al menos 8 caracteres')
    .matches(
      /(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
      'La contraseña debe contener al menos una mayúscula, una minúscula y un número'
    )
    .required('La contraseña es requerida'),
  nombre: yup
    .string()
    .min(2, 'El nombre debe tener al menos 2 caracteres')
    .required('El nombre es requerido'),
  apellido: yup
    .string()
    .min(2, 'El apellido debe tener al menos 2 caracteres')
    .required('El apellido es requerido'),
  dni: yup
    .string()
    .matches(/^\d{7,8}$/, 'El DNI debe tener 7 u 8 dígitos')
    .required('El DNI es requerido'),
  telefono: yup
    .string()
    .matches(/^\+?[1-9]\d{1,14}$/, 'El teléfono no es válido')
    .required('El teléfono es requerido'),
  fecha_nacimiento: yup
    .date()
    .typeError('La fecha de nacimiento no es válida')
    .max(new Date(), 'La fecha no puede ser futura')
    .required('La fecha de nacimiento es requerida'),
});

type RegisterFormData = yup.InferType<typeof registerSchema>;

// Interface que coincide exactamente con lo que espera el backend
interface RegisterFormInputs {
  email: string;
  password: string;
  nombre: string;
  apellido: string;
  dni: string;
  telefono: string;
  fecha_nacimiento: string;
}

const Register: React.FC = () => {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = React.useState(false);
  const { mode } = useThemeMode();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormData>({
    resolver: yupResolver(registerSchema),
  });

  const onSubmit = async (data: RegisterFormData) => {
    setIsLoading(true);
    
    try {
      // Log para debug (solo en desarrollo)
      if (process.env.NODE_ENV === 'development') {
        console.log('Enviando datos de registro:', {
          email: data.email,
          nombre: data.nombre,
          apellido: data.apellido,
          dni: data.dni,
          telefono: data.telefono,
          fecha_nacimiento: data.fecha_nacimiento,
          // NO loguear la contraseña
        });
      }

      // Preparar datos para el backend
      const registerData: RegisterFormInputs = {
        email: data.email,
        password: data.password,
        nombre: data.nombre,
        apellido: data.apellido,
        dni: data.dni,
        telefono: data.telefono,
        fecha_nacimiento: data.fecha_nacimiento.toISOString().split('T')[0],
      };

      await apiService.registerPaciente(registerData);

      toast.success('Cuenta creada exitosamente. Por favor inicia sesión.');

      // Pequeño delay para que el usuario lea el toast antes de redirigir
      setTimeout(() => {
        navigate('/login');
      }, 1500);

    } catch (error: any) {
      console.error('Error crítico en registro:', error);

      // Manejo defensivo de errores
      let errorMessage = 'Ocurrió un error inesperado al registrarse.';
      let shouldSuggestLogin = false;

      try {
        // Intentar extraer el mensaje de error de diferentes estructuras posibles
        if (error?.details) {
          // Caso 1: Error con detalles estructurados del backend
          const details = error.details;
          if (typeof details === 'object') {
            // Intentar extraer mensajes específicos por campo
            const fieldErrors: string[] = [];
            
            if (details.email && Array.isArray(details.email)) {
              const emailError = details.email[0];
              fieldErrors.push(`Email: ${emailError}`);
              if (emailError.includes('ya está registrado')) {
                shouldSuggestLogin = true;
              }
            } else if (details.email && typeof details.email === 'string') {
              fieldErrors.push(`Email: ${details.email}`);
              if (details.email.includes('ya está registrado')) {
                shouldSuggestLogin = true;
              }
            }
            
            if (details.dni && Array.isArray(details.dni)) {
              const dniError = details.dni[0];
              fieldErrors.push(`DNI: ${dniError}`);
              if (dniError.includes('ya está registrado') || dniError.includes('inicia sesión')) {
                shouldSuggestLogin = true;
              }
            } else if (details.dni && typeof details.dni === 'string') {
              fieldErrors.push(`DNI: ${details.dni}`);
              if (details.dni.includes('ya está registrado') || details.dni.includes('inicia sesión')) {
                shouldSuggestLogin = true;
              }
            }
            
            if (details.password && Array.isArray(details.password)) {
              fieldErrors.push(`Contraseña: ${details.password[0]}`);
            } else if (details.password && typeof details.password === 'string') {
              fieldErrors.push(`Contraseña: ${details.password}`);
            }

            if (fieldErrors.length > 0) {
              errorMessage = fieldErrors.join('. ');
              if (shouldSuggestLogin) {
                errorMessage += ' Si ya tienes cuenta, por favor inicia sesión.';
              }
            } else if (details.error && typeof details.error === 'string') {
              errorMessage = details.error;
            } else if (details.message && typeof details.message === 'string') {
              errorMessage = details.message;
            }
          }
        } else if (error?.response) {
          // Caso 2: Error de Axios/Fetch con respuesta del servidor
          const responseData = error.response.data || error.response;
          if (responseData?.error && typeof responseData.error === 'string') {
            errorMessage = `Error del servidor: ${responseData.error}`;
          } else if (responseData?.message && typeof responseData.message === 'string') {
            errorMessage = `Error del servidor: ${responseData.message}`;
          } else if (responseData?.detail && typeof responseData.detail === 'string') {
            errorMessage = `Error del servidor: ${responseData.detail}`;
          } else if (typeof responseData === 'string') {
            errorMessage = `Error del servidor: ${responseData}`;
          }
        } else if (error?.message && typeof error.message === 'string') {
          // Caso 3: Error con mensaje directo
          errorMessage = error.message;
        } else if (typeof error === 'string') {
          // Caso 4: Error es directamente un string
          errorMessage = error;
        } else if (error?.request) {
          // Caso 5: La petición se hizo pero no hubo respuesta
          errorMessage = 'No se pudo contactar al servidor. Verifique su conexión.';
        }
      } catch (parseError) {
        // Si falla el parsing del error, usar mensaje genérico
        console.error('Error al parsear el error:', parseError);
        errorMessage = 'Ocurrió un error inesperado. Por favor, intenta nuevamente.';
      }

      // Mostrar error al usuario
      toast.error(errorMessage, {
        duration: 5000, // Mostrar por más tiempo si sugiere login
      });
      
      // Si sugiere login, también mostrar un mensaje adicional
      if (shouldSuggestLogin) {
        setTimeout(() => {
          toast('💡 Si ya tienes cuenta, puedes iniciar sesión con tu DNI y contraseña.', {
            icon: 'ℹ️',
            duration: 4000,
          });
        }, 1000);
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        width: '100vw',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: authPageGradient(mode),
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        overflow: 'auto',
        padding: 2,
      }}
    >
      <Box sx={{ position: 'fixed', top: 16, right: 16, zIndex: 10 }}>
        <ThemeModeToggle inverse />
      </Box>
      <Container component="main" maxWidth="sm">
        <Card
          elevation={24}
          sx={{
            padding: 4,
            borderRadius: 3,
            background:
              mode === 'dark' ? 'rgba(26, 31, 46, 0.95)' : 'rgba(255, 255, 255, 0.95)',
            backdropFilter: 'blur(10px)',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
          }}
        >
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              mb: 3,
            }}
          >
            <MedicalServices
              sx={{
                fontSize: 80,
                mb: 2,
                color: 'primary.main',
                filter: 'drop-shadow(0 4px 8px rgba(0,0,0,0.1))',
              }}
            />
            <Typography
              component="h1"
              variant="h4"
              sx={{
                fontWeight: 700,
                color: 'text.primary',
                textAlign: 'center',
                mb: 1,
              }}
            >
              Registro de Paciente
            </Typography>
            <Typography
              variant="body2"
              color="text.secondary"
              sx={{ textAlign: 'center' }}
            >
              Completa tus datos para crear tu cuenta
            </Typography>
          </Box>

          <CardContent sx={{ px: 0 }}>
            <Box
              component="form"
              onSubmit={handleSubmit(onSubmit)}
              sx={{ width: '100%' }}
            >
              <TextField
                {...register('email')}
                margin="normal"
                required
                fullWidth
                label="Email"
                type="email"
                autoComplete="email"
                autoFocus
                error={!!errors.email}
                helperText={errors.email?.message}
                disabled={isLoading}
                sx={{ mb: 2 }}
              />

              <TextField
                {...register('password')}
                margin="normal"
                required
                fullWidth
                label="Contraseña"
                type="password"
                autoComplete="new-password"
                error={!!errors.password}
                helperText={errors.password?.message}
                disabled={isLoading}
                sx={{ mb: 2 }}
              />

              <TextField
                {...register('nombre')}
                margin="normal"
                required
                fullWidth
                label="Nombre"
                autoComplete="given-name"
                error={!!errors.nombre}
                helperText={errors.nombre?.message}
                disabled={isLoading}
                sx={{ mb: 2 }}
              />

              <TextField
                {...register('apellido')}
                margin="normal"
                required
                fullWidth
                label="Apellido"
                autoComplete="family-name"
                error={!!errors.apellido}
                helperText={errors.apellido?.message}
                disabled={isLoading}
                sx={{ mb: 2 }}
              />

              <TextField
                {...register('dni')}
                margin="normal"
                required
                fullWidth
                label="DNI / Documento"
                autoComplete="off"
                error={!!errors.dni}
                helperText={errors.dni?.message || '7 u 8 dígitos'}
                disabled={isLoading}
                sx={{ mb: 2 }}
              />

              <TextField
                {...register('telefono')}
                margin="normal"
                required
                fullWidth
                label="Teléfono"
                type="tel"
                autoComplete="tel"
                error={!!errors.telefono}
                helperText={errors.telefono?.message}
                disabled={isLoading}
                sx={{ mb: 2 }}
              />

              <TextField
                {...register('fecha_nacimiento')}
                margin="normal"
                required
                fullWidth
                label="Fecha de Nacimiento"
                type="date"
                InputLabelProps={{
                  shrink: true,
                }}
                error={!!errors.fecha_nacimiento}
                helperText={errors.fecha_nacimiento?.message}
                disabled={isLoading}
                sx={{ mb: 3 }}
              />

              <Button
                type="submit"
                fullWidth
                variant="contained"
                size="large"
                disabled={isLoading}
                startIcon={isLoading ? <CircularProgress size={20} /> : null}
                sx={{
                  py: 1.5,
                  fontSize: '1.1rem',
                  fontWeight: 600,
                  borderRadius: 2,
                  textTransform: 'none',
                  background: 'linear-gradient(45deg, #667eea 30%, #764ba2 90%)',
                  boxShadow: '0 4px 14px 0 rgba(102, 126, 234, 0.4)',
                  '&:hover': {
                    background: 'linear-gradient(45deg, #5a6fd8 30%, #6a4190 90%)',
                    boxShadow: '0 6px 20px 0 rgba(102, 126, 234, 0.5)',
                  },
                  '&:disabled': {
                    background: 'linear-gradient(45deg, #a0aec0 30%, #718096 90%)',
                    boxShadow: 'none',
                  },
                }}
              >
                {isLoading ? 'Registrando...' : 'Crear Cuenta'}
              </Button>
            </Box>

            <Box sx={{ mt: 3, textAlign: 'center' }}>
              <Typography variant="body2" color="text.secondary">
                ¿Ya tienes cuenta?{' '}
                <MuiLink
                  component={Link}
                  to="/login"
                  sx={{
                    fontWeight: 600,
                    textDecoration: 'none',
                    '&:hover': {
                      textDecoration: 'underline',
                    },
                  }}
                >
                  Inicia Sesión
                </MuiLink>
              </Typography>
            </Box>
          </CardContent>
        </Card>
      </Container>
    </Box>
  );
};

export default Register;

/* 
 * ============================================================================
 * INSTRUCCIONES PARA QA / TESTING MANUAL
 * ============================================================================
 * 
 * Para debuggear problemas de registro:
 * 
 * 1. Abrir DevTools (F12) antes de probar el registro
 * 2. Ir a la pestaña "Network" (Red)
 * 3. Filtrar por "register" o buscar la petición POST a /api/auth/register/
 * 4. Si falla el registro:
 *    - Revisar la pestaña "Response" para ver la respuesta cruda del servidor
 *    - Revisar la pestaña "Headers" para ver los headers enviados
 *    - Revisar la consola (Console) para ver los logs de error
 * 
 * 5. Verificar en la consola:
 *    - "Enviando datos de registro:" - muestra los datos que se envían (sin password)
 *    - "Error crítico en registro:" - muestra el error completo
 * 
 * 6. Verificar el servidor backend:
 *    - Asegurarse de que el endpoint /api/auth/register/ esté funcionando
 *    - Verificar los logs del servidor Django para ver errores del backend
 * 
 * ============================================================================
 */