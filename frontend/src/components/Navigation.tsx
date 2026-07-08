import React, { useState } from 'react';
import {
  Box,
  Drawer,
  AppBar,
  Toolbar,
  List,
  Typography,
  Divider,
  IconButton,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Menu,
  MenuItem,
  Avatar,
  useTheme,
  useMediaQuery,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Home as HomeIcon,
  CalendarToday as CalendarIcon,
  People as PeopleIcon,
  Folder as FolderIcon,
  LocalHospital,
  Person,
  Hotel,
  Schedule,
  AccountCircle,
  Logout,
  MedicalServices,
  FactCheck,
} from '@mui/icons-material';
import { useNavigate, useLocation, Outlet } from 'react-router-dom';
import { useData } from '../contexts/DataContext';
import Logo from './Logo';
import { getHomeNavLabel, getSolicitudesModuleLabel } from '../utils/navLabels';

const drawerWidth = 240;

interface MenuItemConfig {
  text: string;
  icon: React.ReactElement;
  path: string;
  roles: string[]; // 'all' para todos, o roles específicos: 'medico', 'admin', 'secretaria', 'paciente', 'enfermeria'
}

const menuItems: MenuItemConfig[] = [
  { text: 'Inicio', icon: <HomeIcon />, path: '/dashboard', roles: ['all'] },
  { text: 'Consultas', icon: <LocalHospital />, path: '/atenciones', roles: ['medico', 'admin', 'enfermeria', 'paciente'] },
  { text: 'Archivos', icon: <FolderIcon />, path: '/archivos', roles: ['medico', 'admin', 'paciente'] },
  { text: 'Turnos', icon: <CalendarIcon />, path: '/turnos', roles: ['medico', 'admin', 'secretaria', 'paciente'] },
  { text: 'Estudios complementarios', icon: <MedicalServices />, path: '/estudios-complementarios', roles: ['medico', 'admin', 'paciente', 'secretaria'] },
  { text: 'Laboratorio', icon: <Schedule />, path: '/solicitudes', roles: ['medico', 'admin', 'secretaria', 'paciente'] },
  { text: 'Pacientes', icon: <PeopleIcon />, path: '/pacientes', roles: ['medico', 'admin', 'secretaria', 'enfermeria'] },
  { text: 'Internación', icon: <Hotel />, path: '/internacion', roles: ['medico', 'admin', 'enfermeria'] },
  { text: 'Médicos', icon: <Person />, path: '/medicos', roles: ['admin'] },
  { text: 'Usuarios', icon: <Person />, path: '/usuarios', roles: ['admin'] },
  { text: 'Auditoría', icon: <FactCheck />, path: '/auditoria', roles: ['admin'] },
];

interface NavigationProps {
  children?: React.ReactNode;
}

const Navigation: React.FC<NavigationProps> = ({ children }) => {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const navigate = useNavigate();
  const location = useLocation();
  const { currentUser, logout } = useData();

  // Filtrar items según el rol del usuario
  const getFilteredMenuItems = (): MenuItemConfig[] => {
    if (!currentUser) return [];

    const userRole = (currentUser.rol || '').toLowerCase();
    const isAdmin = userRole === 'admin' || currentUser.is_superuser;

    return menuItems.filter((item) => {
      if (item.roles.includes('all')) return true;
      if (isAdmin) return true; // Admin ve todo
      return item.roles.includes(userRole);
    });
  };

  const filteredMenuItems = getFilteredMenuItems();

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const handleProfileMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleProfileMenuClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = async () => {
    handleProfileMenuClose();
    await logout();
    navigate('/login', { replace: true });
  };

  // Obtener iniciales del usuario
  const getInitials = (user: any): string => {
    if (!user) return 'U';
    const firstName = user.first_name || '';
    const lastName = user.last_name || '';
    if (firstName && lastName) {
      return `${firstName[0]}${lastName[0]}`.toUpperCase();
    }
    if (user.username) {
      return user.username.substring(0, 2).toUpperCase();
    }
    return 'U';
  };

  // Obtener nombre completo del usuario
  const getUserDisplayName = (user: any): string => {
    if (!user) return 'Usuario';
    if (user.first_name && user.last_name) {
      return `${user.first_name} ${user.last_name}`;
    }
    return user.username || 'Usuario';
  };

  // Obtener título según rol
  const getRoleTitle = (user: any): string => {
    if (!user) return '';
    const role = (user.rol || '').toUpperCase();
    if (role === 'MEDICO') return 'Dr.';
    if (role === 'ADMIN') return 'Admin.';
    if (role === 'SECRETARIA') return 'Srta.';
    if (role === 'ENFERMERIA') return 'Enf.';
    return 'Sr./Sra.';
  };

  const drawer = (
    <Box>
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          p: 2,
          borderBottom: '1px solid rgba(0,0,0,0.1)',
        }}
      >
        <Logo size={120} />
      </Box>
      <Divider />
      <List sx={{ pt: 1 }}>
        {filteredMenuItems.map((item) => {
          const isSelected = location.pathname === item.path;

          return (
            <ListItem key={item.text} disablePadding>
              <ListItemButton
                onClick={() => {
                  navigate(item.path);
                  if (isMobile) setMobileOpen(false);
                }}
                selected={isSelected}
                sx={{
                  mx: 1,
                  borderRadius: 2,
                  mb: 0.5,
                  '&.Mui-selected': {
                    backgroundColor: 'primary.main',
                    color: 'white',
                    '&:hover': {
                      backgroundColor: 'primary.dark',
                    },
                    '& .MuiListItemIcon-root': {
                      color: 'white',
                    },
                  },
                  '&:hover': {
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                  },
                }}
              >
                <ListItemIcon
                  sx={{
                    minWidth: 40,
                    color: isSelected ? 'white' : 'inherit',
                  }}
                >
                  {item.icon}
                </ListItemIcon>
                <ListItemText
                  primary={
                    item.path === '/dashboard'
                      ? getHomeNavLabel()
                      : item.path === '/solicitudes'
                        ? getSolicitudesModuleLabel(currentUser)
                        : item.text
                  }
                  primaryTypographyProps={{
                    fontWeight: isSelected ? 600 : 400,
                  }}
                />
              </ListItemButton>
            </ListItem>
          );
        })}
      </List>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex' }}>
      <AppBar
        position="fixed"
        sx={{
          width: { md: `calc(100% - ${drawerWidth}px)` },
          ml: { md: `${drawerWidth}px` },
          backgroundColor: 'white',
          color: 'text.primary',
          boxShadow: '0 2px 12px 0 rgba(0,0,0,0.1)',
          zIndex: (theme) => theme.zIndex.drawer + 1,
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { md: 'none' } }}
          >
            <MenuIcon />
          </IconButton>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexGrow: 1 }}>
            <MedicalServices sx={{ color: 'primary.main', fontSize: 28 }} />
            <Typography variant="h6" noWrap component="div" sx={{ fontWeight: 600 }}>
              Synesis EMR
            </Typography>
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="body2" sx={{ display: { xs: 'none', sm: 'block' }, mr: 1 }}>
              {getUserDisplayName(currentUser)}
            </Typography>
            <IconButton
              onClick={handleProfileMenuOpen}
              sx={{ p: 0 }}
            >
              <Avatar sx={{ width: 36, height: 36, bgcolor: 'primary.main' }}>
                {getInitials(currentUser)}
              </Avatar>
            </IconButton>
          </Box>
        </Toolbar>
      </AppBar>

      <Box
        component="nav"
        sx={{ width: { md: drawerWidth }, flexShrink: { md: 0 } }}
      >
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{
            keepMounted: true,
          }}
          sx={{
            display: { xs: 'block', md: 'none' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: drawerWidth,
              backgroundColor: '#f8fafc',
            },
          }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', md: 'block' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: drawerWidth,
              backgroundColor: '#f8fafc',
              borderRight: '1px solid rgba(0,0,0,0.1)',
            },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>

      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleProfileMenuClose}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'right',
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'right',
        }}
      >
        <MenuItem onClick={handleProfileMenuClose}>
          <ListItemIcon>
            <AccountCircle fontSize="small" />
          </ListItemIcon>
          Perfil
        </MenuItem>
        <Divider />
        <MenuItem onClick={handleLogout}>
          <ListItemIcon>
            <Logout fontSize="small" />
          </ListItemIcon>
          Cerrar Sesión
        </MenuItem>
      </Menu>

      {/* Main Content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { md: `calc(100% - ${drawerWidth}px)` },
          minHeight: '100vh',
          backgroundColor: '#f8fafc',
        }}
      >
        <Toolbar /> {/* Spacer para el AppBar */}
        {children || <Outlet />}
      </Box>
    </Box>
  );
};

export default Navigation;
