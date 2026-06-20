import React, { useMemo } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import { CssBaseline, Box, Alert, CircularProgress } from '@mui/material';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';

import './App.css';
import AppLayout from './components/layout/AppLayout';
import Dashboard from './pages/Dashboard';
import Pacientes from './pages/Pacientes';
import Turnos from './pages/Turnos';
import Solicitudes from './pages/Solicitudes';
import ArchivosMedicos from './pages/ArchivosMedicos';
import EstudiosComplementarios from './pages/EstudiosComplementarios';
import EstudioComplementarioDetalle from './pages/EstudioComplementarioDetalle';
import Login from './pages/Login';
import Register from './pages/Register';
import Medicos from './pages/Medicos';
import GestionUsuarios from './pages/GestionUsuarios';
import DiagnosticosCIE10 from './pages/catalogos/DiagnosticosCIE10';
import EstudiosDiagnostico from './pages/catalogos/EstudiosDiagnostico';
import Procedimientos from './pages/catalogos/Procedimientos';
import Medicamentos from './pages/catalogos/Medicamentos';
import Especialidades from './pages/catalogos/Especialidades';
import { DataProvider, useData } from './contexts/DataContext';
import { ThemeModeProvider, useThemeMode } from './contexts/ThemeModeContext';
import { buildAppTheme } from './theme/buildAppTheme';
import AtencionesClinicasPage from './modules/atenciones/AtencionesClinicasPage';
import InternacionDashboard from './pages/InternacionDashboard';
import MisConsultas from './pages/MisConsultas';
import ListaExamenesTest from './pages/laboratorio/ListaExamenesTest';
import OrdenesLims from './pages/laboratorio/OrdenesLims';
import OrdenLimsDetalle from './pages/laboratorio/OrdenLimsDetalle';
import MicrobiologiaHub from './pages/laboratorio/MicrobiologiaHub';
import MicrobiologiaEstudios from './pages/laboratorio/MicrobiologiaEstudios';
import MicrobiologiaEstudioDetalle from './pages/laboratorio/MicrobiologiaEstudioDetalle';
import MicrobiologiaCatalogos from './pages/laboratorio/MicrobiologiaCatalogos';
import PatientDashboard from './components/patient360/PatientDashboard';
import AuditEventsPage from './pages/AuditEventsPage';

// Create query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

interface ProtectedRouteProps {
  children: React.ReactNode;
  currentUser: any;
  isAuthenticated: boolean;
  isLoading: boolean;
  requiredRole?: string | string[];
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ 
  children, 
  currentUser, 
  isAuthenticated, 
  isLoading,
  requiredRole 
}) => {
  // Mostrar loading mientras se verifica la autenticación
  if (isLoading) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        }}
      >
        <CircularProgress size={40} sx={{ color: 'white' }} />
      </Box>
    );
  }

  // Redirigir a login si no está autenticado
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  // Verificar roles si se requiere
  if (requiredRole) {
    const roles = Array.isArray(requiredRole) ? requiredRole : [requiredRole];
    const userRole = (currentUser?.rol || '').toUpperCase();
    const isSuperuser = currentUser?.is_superuser;
    
    if (!isSuperuser && !roles.some(role => userRole === role.toUpperCase())) {
      return (
        <Box sx={{ p: 3 }}>
          <Alert severity="error">No tiene permisos para acceder a esta sección.</Alert>
        </Box>
      );
    }
  }
  
  return <>{children}</>;
};

const AppContent: React.FC = () => {
  const { currentUser, isAuthenticated, isLoading } = useData();

  return (
    <div className="App">
      <Routes>
        {/* Rutas públicas */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* Rutas protegidas con layout (sidebar + header) */}
        <Route
          element={
            <ProtectedRoute
              currentUser={currentUser}
              isAuthenticated={isAuthenticated}
              isLoading={isLoading}
            >
              <AppLayout />
            </ProtectedRoute>
          }
        >
          <Route
            path="/"
            element={<Navigate to="/dashboard" replace />}
          />
          <Route
            path="/dashboard"
            element={<Dashboard />}
          />
          <Route
            path="/pacientes"
            element={<Pacientes />}
          />
          <Route
            path="/paciente/:id"
            element={<PatientDashboard />}
          />
          <Route
            path="/turnos"
            element={<Turnos />}
          />
          <Route
            path="/atenciones"
            element={<AtencionesClinicasPage />}
          />
          <Route
            path="/mis-consultas"
            element={<MisConsultas />}
          />
          <Route
            path="/internacion"
            element={
              <ProtectedRoute
                currentUser={currentUser}
                isAuthenticated={isAuthenticated}
                isLoading={isLoading}
                requiredRole={['ADMIN', 'MEDICO', 'ENFERMERIA']}
              >
                <InternacionDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/solicitudes"
            element={<Solicitudes />}
          />
          <Route
            path="/archivos-medicos"
            element={<ArchivosMedicos />}
          />
          <Route
            path="/estudios-complementarios"
            element={<EstudiosComplementarios />}
          />
          <Route
            path="/estudios-complementarios/:id"
            element={<EstudioComplementarioDetalle />}
          />
          <Route
            path="/medicos"
            element={
              <ProtectedRoute
                currentUser={currentUser}
                isAuthenticated={isAuthenticated}
                isLoading={isLoading}
                requiredRole="ADMIN"
              >
                <Medicos />
              </ProtectedRoute>
            }
          />
          <Route
            path="/usuarios"
            element={
              <ProtectedRoute
                currentUser={currentUser}
                isAuthenticated={isAuthenticated}
                isLoading={isLoading}
                requiredRole="ADMIN"
              >
                <GestionUsuarios />
              </ProtectedRoute>
            }
          />
          <Route
            path="/catalogos/diagnosticos"
            element={
              <ProtectedRoute
                currentUser={currentUser}
                isAuthenticated={isAuthenticated}
                isLoading={isLoading}
                requiredRole={['ADMIN', 'MEDICO']}
              >
                <DiagnosticosCIE10 />
              </ProtectedRoute>
            }
          />
          <Route
            path="/catalogos/estudios"
            element={
              <ProtectedRoute
                currentUser={currentUser}
                isAuthenticated={isAuthenticated}
                isLoading={isLoading}
                requiredRole={['ADMIN', 'MEDICO']}
              >
                <EstudiosDiagnostico />
              </ProtectedRoute>
            }
          />
          <Route
            path="/catalogos/procedimientos"
            element={
              <ProtectedRoute
                currentUser={currentUser}
                isAuthenticated={isAuthenticated}
                isLoading={isLoading}
                requiredRole={['ADMIN', 'MEDICO']}
              >
                <Procedimientos />
              </ProtectedRoute>
            }
          />
          <Route
            path="/catalogos/medicamentos"
            element={
              <ProtectedRoute
                currentUser={currentUser}
                isAuthenticated={isAuthenticated}
                isLoading={isLoading}
                requiredRole={['ADMIN', 'MEDICO']}
              >
                <Medicamentos />
              </ProtectedRoute>
            }
          />
          <Route
            path="/catalogos/especialidades"
            element={
              <ProtectedRoute
                currentUser={currentUser}
                isAuthenticated={isAuthenticated}
                isLoading={isLoading}
                requiredRole={['ADMIN', 'MEDICO']}
              >
                <Especialidades />
              </ProtectedRoute>
            }
          />
          <Route
            path="/laboratorio/ordenes/:id"
            element={
              <ProtectedRoute
                currentUser={currentUser}
                isAuthenticated={isAuthenticated}
                isLoading={isLoading}
              >
                <OrdenLimsDetalle />
              </ProtectedRoute>
            }
          />
          <Route
            path="/laboratorio/ordenes"
            element={
              <ProtectedRoute
                currentUser={currentUser}
                isAuthenticated={isAuthenticated}
                isLoading={isLoading}
              >
                <OrdenesLims />
              </ProtectedRoute>
            }
          />
          <Route
            path="/laboratorio/examenes-test"
            element={
              <ProtectedRoute
                currentUser={currentUser}
                isAuthenticated={isAuthenticated}
                isLoading={isLoading}
              >
                <ListaExamenesTest />
              </ProtectedRoute>
            }
          />
          <Route
            path="/laboratorio/microbiologia/estudios/:id"
            element={
              <ProtectedRoute
                currentUser={currentUser}
                isAuthenticated={isAuthenticated}
                isLoading={isLoading}
              >
                <MicrobiologiaEstudioDetalle />
              </ProtectedRoute>
            }
          />
          <Route
            path="/laboratorio/microbiologia/estudios"
            element={
              <ProtectedRoute
                currentUser={currentUser}
                isAuthenticated={isAuthenticated}
                isLoading={isLoading}
              >
                <MicrobiologiaEstudios />
              </ProtectedRoute>
            }
          />
          <Route
            path="/laboratorio/microbiologia/catalogos"
            element={
              <ProtectedRoute
                currentUser={currentUser}
                isAuthenticated={isAuthenticated}
                isLoading={isLoading}
              >
                <MicrobiologiaCatalogos />
              </ProtectedRoute>
            }
          />
          <Route
            path="/laboratorio/microbiologia"
            element={
              <ProtectedRoute
                currentUser={currentUser}
                isAuthenticated={isAuthenticated}
                isLoading={isLoading}
              >
                <MicrobiologiaHub />
              </ProtectedRoute>
            }
          />
          <Route
            path="/auditoria"
            element={
              <ProtectedRoute
                currentUser={currentUser}
                isAuthenticated={isAuthenticated}
                isLoading={isLoading}
                requiredRole="ADMIN"
              >
                <AuditEventsPage />
              </ProtectedRoute>
            }
          />
        </Route>
      </Routes>
    </div>
  );
};

const AppThemedTree: React.FC = () => {
  const { mode } = useThemeMode();
  const theme = useMemo(() => buildAppTheme(mode), [mode]);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <QueryClientProvider client={queryClient}>
        <DataProvider>
          <AppContent />
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: mode === 'dark' ? '#2d2d2d' : '#363636',
                color: '#fff',
              },
            }}
          />
        </DataProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
};

const App: React.FC = () => (
  <ThemeModeProvider>
    <AppThemedTree />
  </ThemeModeProvider>
);

export default App;
