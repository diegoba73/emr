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
import SolicitudLabDetalle from './pages/SolicitudLabDetalle';
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
import ListaExamenesTest from './pages/laboratorio/ListaExamenesTest';
import OrdenesLims from './pages/laboratorio/OrdenesLims';
import OrdenesLimsPendientes from './pages/laboratorio/OrdenesLimsPendientes';
import OrdenLimsDetalle from './pages/laboratorio/OrdenLimsDetalle';
import TiposMuestraCatalogo from './pages/laboratorio/TiposMuestraCatalogo';
import ExamenesCatalogo from './pages/laboratorio/ExamenesCatalogo';
import MicrobiologiaHub from './pages/laboratorio/MicrobiologiaHub';
import MicrobiologiaEstudios from './pages/laboratorio/MicrobiologiaEstudios';
import MicrobiologiaEstudioDetalle from './pages/laboratorio/MicrobiologiaEstudioDetalle';
import MicrobiologiaCatalogos from './pages/laboratorio/MicrobiologiaCatalogos';
import PatientDashboard from './components/patient360/PatientDashboard';
import AuditEventsPage from './pages/AuditEventsPage';
import type { User } from './types';
import {
  canAccessArchivosMedicos,
  canAccessAtenciones,
  canAccessAuditoria,
  canAccessCatalogosClinicos,
  canAccessPaciente360,
  canAccessPacientes,
  canAccessSolicitudes,
} from './utils/permissions';
import { canAccessEstudiosModule } from './modules/estudios/permissions';
import { canAccessLimsModule, canAccessMicrobiologia } from './utils/limsAccess';
import { canAccessTurnosAgenda } from './utils/turnoPermissions';

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
  currentUser: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  requiredRole?: string | string[];
  canAccess?: (user: User | null) => boolean;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ 
  children, 
  currentUser, 
  isAuthenticated, 
  isLoading,
  requiredRole,
  canAccess,
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
  
  if (canAccess && !canAccess(currentUser)) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">No tiene permisos para acceder a esta sección.</Alert>
      </Box>
    );
  }

  // Verificar roles si se requiere (legacy; preferir canAccess)
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
            element={
              <ProtectedRoute
                currentUser={currentUser}
                isAuthenticated={isAuthenticated}
                isLoading={isLoading}
                canAccess={canAccessPacientes}
              >
                <Pacientes />
              </ProtectedRoute>
            }
          />
          <Route
            path="/paciente/:id"
            element={
              <ProtectedRoute
                currentUser={currentUser}
                isAuthenticated={isAuthenticated}
                isLoading={isLoading}
                canAccess={canAccessPaciente360}
              >
                <PatientDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/turnos"
            element={
              <ProtectedRoute
                currentUser={currentUser}
                isAuthenticated={isAuthenticated}
                isLoading={isLoading}
                canAccess={canAccessTurnosAgenda}
              >
                <Turnos />
              </ProtectedRoute>
            }
          />
          <Route
            path="/atenciones"
            element={
              <ProtectedRoute
                currentUser={currentUser}
                isAuthenticated={isAuthenticated}
                isLoading={isLoading}
                canAccess={canAccessAtenciones}
              >
                <AtencionesClinicasPage />
              </ProtectedRoute>
            }
          />
          <Route path="/mis-consultas" element={<Navigate to="/atenciones" replace />} />
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
            element={
              <ProtectedRoute
                currentUser={currentUser}
                isAuthenticated={isAuthenticated}
                isLoading={isLoading}
                canAccess={canAccessSolicitudes}
              >
                <Solicitudes />
              </ProtectedRoute>
            }
          />
          <Route
            path="/solicitudes/:id"
            element={
              <ProtectedRoute
                currentUser={currentUser}
                isAuthenticated={isAuthenticated}
                isLoading={isLoading}
                canAccess={canAccessSolicitudes}
              >
                <SolicitudLabDetalle />
              </ProtectedRoute>
            }
          />
          <Route
            path="/archivos"
            element={
              <ProtectedRoute
                currentUser={currentUser}
                isAuthenticated={isAuthenticated}
                isLoading={isLoading}
                canAccess={canAccessArchivosMedicos}
              >
                <ArchivosMedicos />
              </ProtectedRoute>
            }
          />
          <Route path="/archivos-medicos" element={<Navigate to="/archivos" replace />} />
          <Route
            path="/estudios-complementarios"
            element={
              <ProtectedRoute
                currentUser={currentUser}
                isAuthenticated={isAuthenticated}
                isLoading={isLoading}
                canAccess={canAccessEstudiosModule}
              >
                <EstudiosComplementarios />
              </ProtectedRoute>
            }
          />
          <Route
            path="/estudios-complementarios/:id"
            element={
              <ProtectedRoute
                currentUser={currentUser}
                isAuthenticated={isAuthenticated}
                isLoading={isLoading}
                canAccess={canAccessEstudiosModule}
              >
                <EstudioComplementarioDetalle />
              </ProtectedRoute>
            }
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
                requiredRole={['ADMIN', 'MEDICO', 'SECRETARIA']}
                canAccess={canAccessCatalogosClinicos}
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
                requiredRole={['ADMIN', 'MEDICO', 'SECRETARIA']}
                canAccess={canAccessCatalogosClinicos}
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
                requiredRole={['ADMIN', 'MEDICO', 'SECRETARIA']}
                canAccess={canAccessCatalogosClinicos}
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
                requiredRole={['ADMIN', 'MEDICO', 'SECRETARIA']}
                canAccess={canAccessCatalogosClinicos}
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
                requiredRole={['ADMIN', 'MEDICO', 'SECRETARIA']}
                canAccess={canAccessCatalogosClinicos}
              >
                <Especialidades />
              </ProtectedRoute>
            }
          />
          <Route
            path="/laboratorio/pendientes"
            element={
              <ProtectedRoute
                currentUser={currentUser}
                isAuthenticated={isAuthenticated}
                isLoading={isLoading}
                canAccess={canAccessLimsModule}
              >
                <OrdenesLimsPendientes />
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
                canAccess={canAccessLimsModule}
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
                canAccess={canAccessLimsModule}
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
                canAccess={canAccessLimsModule}
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
                canAccess={canAccessMicrobiologia}
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
                canAccess={canAccessMicrobiologia}
              >
                <MicrobiologiaEstudios />
              </ProtectedRoute>
            }
          />
          <Route
            path="/laboratorio/catalogos/examenes"
            element={
              <ProtectedRoute
                currentUser={currentUser}
                isAuthenticated={isAuthenticated}
                isLoading={isLoading}
                canAccess={canAccessLimsModule}
              >
                <ExamenesCatalogo />
              </ProtectedRoute>
            }
          />
          <Route
            path="/laboratorio/catalogos/tipos-muestra"
            element={
              <ProtectedRoute
                currentUser={currentUser}
                isAuthenticated={isAuthenticated}
                isLoading={isLoading}
                canAccess={canAccessLimsModule}
              >
                <TiposMuestraCatalogo />
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
                canAccess={canAccessMicrobiologia}
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
                canAccess={canAccessMicrobiologia}
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
                canAccess={canAccessAuditoria}
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
