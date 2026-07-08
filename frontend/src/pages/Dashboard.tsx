import React from 'react';
import {
  Box,
  Typography,
  GridLegacy as Grid,
  Card,
  CardActionArea,
  CardContent,
  Avatar,
  Paper,
  Chip,
} from '@mui/material';
import {
  CalendarToday,
  LocalHospital,
  Add,
  Search,
  Folder,
  Hotel,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useData } from '../contexts/DataContext';

interface QuickActionCard {
  title: string;
  description: string;
  icon: React.ReactElement;
  path: string;
  color: string;
  roles: string[];
}

const quickActions: QuickActionCard[] = [
  {
    title: 'Nuevo Turno',
    description: 'Crear un nuevo turno médico',
    icon: <Add />,
    path: '/turnos?action=create',
    color: '#667eea',
    roles: ['all'],
  },
  {
    title: 'Buscar Paciente',
    description: 'Buscar y ver información de pacientes',
    icon: <Search />,
    path: '/pacientes',
    color: '#764ba2',
    roles: ['medico', 'admin', 'secretaria', 'enfermeria'],
  },
  {
    title: 'Ver Agenda',
    description: 'Ver calendario de turnos',
    icon: <CalendarToday />,
    path: '/turnos',
    color: '#48bb78',
    roles: ['all'],
  },
  {
    title: 'Consultas',
    description: 'Ver y gestionar atenciones clínicas',
    icon: <LocalHospital />,
    path: '/atenciones',
    color: '#4299e1',
    roles: ['medico', 'admin', 'enfermeria', 'paciente'],
  },
  {
    title: 'Mis archivos',
    description: 'Ver documentos y archivos médicos',
    icon: <Folder />,
    path: '/archivos',
    color: '#ed8936',
    roles: ['paciente'],
  },
  {
    title: 'Estudios complementarios',
    description: 'Ver estudios e informes disponibles',
    icon: <Folder />,
    path: '/estudios-complementarios',
    color: '#38b2ac',
    roles: ['paciente'],
  },
  {
    title: 'Análisis clínico',
    description: 'Estado de tus estudios de laboratorio',
    icon: <Folder />,
    path: '/solicitudes',
    color: '#805ad5',
    roles: ['paciente'],
  },
  {
    title: 'Internación',
    description: 'Gestionar internaciones',
    icon: <Hotel />,
    path: '/internacion',
    color: '#9f7aea',
    roles: ['medico', 'admin', 'enfermeria'],
  },
];

const Dashboard: React.FC = () => {
  const { currentUser, isLoading } = useData();
  const navigate = useNavigate();

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
        <Typography>Cargando...</Typography>
      </Box>
    );
  }

  // Filtrar acciones según el rol del usuario
  const getFilteredActions = (): QuickActionCard[] => {
    if (!currentUser) return [];

    const userRole = (currentUser.rol || '').toLowerCase();
    const isAdmin = userRole === 'admin' || currentUser.is_superuser;

    return quickActions.filter((action) => {
      if (action.roles.includes('all')) return true;
      if (isAdmin) return true; // Admin ve todo
      return action.roles.includes(userRole);
    });
  };

  const filteredActions = getFilteredActions();

  // Obtener nombre completo del usuario
  const getUserDisplayName = (): string => {
    if (!currentUser) return 'Usuario';
    if (currentUser.first_name && currentUser.last_name) {
      return `${currentUser.first_name} ${currentUser.last_name}`;
    }
    return currentUser.username || 'Usuario';
  };

  // Obtener título según rol
  const getRoleTitle = (): string => {
    if (!currentUser) return '';
    const role = (currentUser.rol || '').toUpperCase();
    if (role === 'MEDICO') return 'Dr.';
    if (role === 'ADMIN') return 'Admin.';
    if (role === 'SECRETARIA') return 'Srta.';
    if (role === 'ENFERMERIA') return 'Enf.';
    return 'Sr./Sra.';
  };

  return (
    <Box>
      {/* Header de Bienvenida */}
      <Paper
        elevation={2}
        sx={{
          p: 3,
          mb: 4,
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          color: 'white',
          borderRadius: 2,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Avatar
            sx={{
              width: 64,
              height: 64,
              bgcolor: 'rgba(255, 255, 255, 0.2)',
              fontSize: '1.5rem',
            }}
          >
            {currentUser?.first_name?.[0] || currentUser?.username?.[0] || 'U'}
          </Avatar>
          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="h4" component="h1" fontWeight="bold" gutterBottom>
              Bienvenido, {getRoleTitle()} {getUserDisplayName()}
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
              <Chip
                label={currentUser?.rol || 'Usuario'}
                size="small"
                sx={{
                  bgcolor: 'rgba(255, 255, 255, 0.2)',
                  color: 'white',
                  fontWeight: 600,
                }}
              />
              {currentUser?.medico?.especialidad && (
                <Chip
                  label={currentUser.medico.especialidad.nombre}
                  size="small"
                  sx={{
                    bgcolor: 'rgba(255, 255, 255, 0.2)',
                    color: 'white',
                  }}
                />
              )}
            </Box>
          </Box>
        </Box>
      </Paper>

      {/* Grid de Acciones Rápidas */}
      <Typography variant="h5" component="h2" gutterBottom sx={{ mb: 3, fontWeight: 600 }}>
        Acciones Rápidas
      </Typography>

      <Grid container spacing={3}>
        {filteredActions.map((action) => (
          <Grid item xs={12} sm={6} md={4} lg={3} key={action.title}>
            <Card
              sx={{
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                transition: 'transform 0.2s, box-shadow 0.2s',
                '&:hover': {
                  transform: 'translateY(-4px)',
                  boxShadow: 6,
                },
              }}
            >
              <CardActionArea
                onClick={() => navigate(action.path)}
                sx={{
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'stretch',
                }}
              >
                <CardContent sx={{ flexGrow: 1, p: 3 }}>
                  <Box
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      width: 56,
                      height: 56,
                      borderRadius: 2,
                      bgcolor: `${action.color}15`,
                      color: action.color,
                      mb: 2,
                      '& svg': {
                        fontSize: 32,
                      },
                    }}
                  >
                    {action.icon}
                  </Box>
                  <Typography variant="h6" component="h3" gutterBottom fontWeight={600}>
                    {action.title}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {action.description}
                  </Typography>
                </CardContent>
              </CardActionArea>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Mensaje si no hay acciones disponibles */}
      {filteredActions.length === 0 && (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="h6" color="text.secondary">
            No hay acciones disponibles para tu rol
          </Typography>
        </Paper>
      )}
    </Box>
  );
};

export default Dashboard;
