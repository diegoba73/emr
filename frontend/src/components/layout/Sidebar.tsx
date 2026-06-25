import React from 'react';
import {
  Box,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Divider,
  Typography,
} from '@mui/material';
import {
  Home as HomeIcon,
  People as PeopleIcon,
  CalendarToday as CalendarIcon,
  LocalHospital,
  Folder as FolderIcon,
  AssignmentTurnedIn as SolicitudIcon,
  MenuBook as CatalogIcon,
  FactCheck as AuditIcon,
  Science as ScienceIcon,
  Biotech as BiotechIcon,
  Description,
} from '@mui/icons-material';
import { useLocation, useNavigate } from 'react-router-dom';
import { useData } from '../../contexts/DataContext';
import { User } from '../../types';
import Logo from '../Logo';
import {
  canAccessArchivosMedicos,
  canAccessAtenciones,
  canAccessAuditoria,
  canAccessPacientes,
  canAccessSolicitudes,
} from '../../utils/permissions';
import { canAccessEstudiosModule } from '../../modules/estudios/permissions';
import { canAccessLimsModule, canAccessMicrobiologia } from '../../utils/limsAccess';

export const SIDEBAR_WIDTH = 260;

export interface NavItem {
  text: string;
  path: string;
  icon: React.ReactElement;
  /** @deprecated usar canAccessNavItem */
  roles?: string[];
  canAccess?: (user: User | null) => boolean;
}

const navItems: NavItem[] = [
  { text: 'Dashboard', icon: <HomeIcon />, path: '/dashboard', canAccess: () => true },
  { text: 'Pacientes', icon: <PeopleIcon />, path: '/pacientes', canAccess: canAccessPacientes },
  { text: 'Turnos', icon: <CalendarIcon />, path: '/turnos', roles: ['medico', 'admin', 'secretaria', 'paciente'] },
  { text: 'Consultas', icon: <LocalHospital />, path: '/atenciones', canAccess: canAccessAtenciones },
  { text: 'Archivos', icon: <FolderIcon />, path: '/archivos-medicos', canAccess: canAccessArchivosMedicos },
  {
    text: 'Estudios complementarios',
    icon: <Description />,
    path: '/estudios-complementarios',
    canAccess: canAccessEstudiosModule,
  },
  { text: 'Solicitudes', icon: <SolicitudIcon />, path: '/solicitudes', canAccess: canAccessSolicitudes },
  { text: 'Mis consultas', icon: <FolderIcon />, path: '/mis-consultas', roles: ['medico', 'paciente'] },
  { text: 'Internación', icon: <LocalHospital />, path: '/internacion', roles: ['medico', 'admin', 'enfermeria'] },
];

const adminOnly: NavItem[] = [
  { text: 'Médicos', icon: <PeopleIcon />, path: '/medicos', roles: ['admin'] },
  { text: 'Usuarios', icon: <PeopleIcon />, path: '/usuarios', roles: ['admin'] },
  { text: 'Auditoría', icon: <AuditIcon />, path: '/auditoria', canAccess: canAccessAuditoria },
];

const labItems: NavItem[] = [
  { text: 'Órdenes LIMS', icon: <ScienceIcon />, path: '/laboratorio/ordenes', canAccess: canAccessLimsModule },
  { text: 'Microbiología', icon: <BiotechIcon />, path: '/laboratorio/microbiologia/estudios', canAccess: canAccessMicrobiologia },
  { text: 'Catálogos micro', icon: <CatalogIcon />, path: '/laboratorio/microbiologia/catalogos', canAccess: canAccessMicrobiologia },
];

const catalogItems: NavItem[] = [
  { text: 'CIE-10', icon: <CatalogIcon />, path: '/catalogos/diagnosticos', roles: ['admin', 'medico'] },
  { text: 'Estudios', icon: <CatalogIcon />, path: '/catalogos/estudios', roles: ['admin', 'medico'] },
  { text: 'Procedimientos', icon: <CatalogIcon />, path: '/catalogos/procedimientos', roles: ['admin', 'medico'] },
  { text: 'Medicamentos', icon: <CatalogIcon />, path: '/catalogos/medicamentos', roles: ['admin', 'medico'] },
  { text: 'Especialidades', icon: <CatalogIcon />, path: '/catalogos/especialidades', roles: ['admin', 'medico'] },
];

const filterByRole = (items: NavItem[], currentUser: User | null): NavItem[] => {
  if (!currentUser) return [];
  const userRole = (currentUser.rol || '').toLowerCase();
  const isAdmin = userRole === 'admin' || currentUser.is_superuser;
  return items.filter((item) => {
    if (item.canAccess) {
      return item.canAccess(currentUser);
    }
    if (!item.roles) return false;
    if (item.roles.includes('all')) return true;
    if (isAdmin) return true;
    return item.roles.includes(userRole);
  });
};

export interface SidebarContentProps {
  onNavigate?: () => void;
}

export const SidebarContent: React.FC<SidebarContentProps> = ({ onNavigate }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { currentUser } = useData();

  const primary = filterByRole(navItems, currentUser);
  const adminItems = filterByRole(adminOnly, currentUser);
  const catalogNav = filterByRole(catalogItems, currentUser);
  const labNav = filterByRole(labItems, currentUser);

  const go = (path: string) => {
    navigate(path);
    onNavigate?.();
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          p: 2,
          borderBottom: 1,
          borderColor: 'divider',
        }}
      >
        <Logo size={110} />
      </Box>
      <Typography variant="caption" color="text.secondary" sx={{ px: 2, pt: 1.5, pb: 0.5 }}>
        Principal
      </Typography>
      <List sx={{ pt: 0.5, px: 0.5 }}>
        {primary.map((item) => {
          const selected = location.pathname === item.path;
          return (
            <ListItem key={item.path} disablePadding>
              <ListItemButton
                selected={selected}
                onClick={() => go(item.path)}
                sx={{
                  mx: 0.5,
                  borderRadius: 2,
                  mb: 0.25,
                  '&.Mui-selected': {
                    backgroundColor: 'primary.main',
                    color: 'primary.contrastText',
                    '& .MuiListItemIcon-root': { color: 'inherit' },
                    '&:hover': { backgroundColor: 'primary.dark' },
                  },
                }}
              >
                <ListItemIcon sx={{ minWidth: 40, color: selected ? 'inherit' : 'action.active' }}>{item.icon}</ListItemIcon>
                <ListItemText primary={item.text} primaryTypographyProps={{ fontWeight: selected ? 600 : 400, fontSize: 15 }} />
              </ListItemButton>
            </ListItem>
          );
        })}
      </List>
      {labNav.length > 0 && (
        <>
          <Divider sx={{ my: 1 }} />
          <Typography variant="caption" color="text.secondary" sx={{ px: 2, py: 0.5 }}>
            Laboratorio (LIMS)
          </Typography>
          <List sx={{ pt: 0.5, px: 0.5 }}>
            {labNav.map((item) => {
              const selected =
                location.pathname === item.path ||
                (item.path === '/laboratorio/ordenes' && location.pathname.startsWith('/laboratorio/ordenes')) ||
                (item.path === '/laboratorio/microbiologia/estudios' &&
                  location.pathname.startsWith('/laboratorio/microbiologia')) ||
                (item.path === '/laboratorio/microbiologia/catalogos' &&
                  location.pathname.startsWith('/laboratorio/microbiologia/catalogos'));
              return (
                <ListItem key={item.path} disablePadding>
                  <ListItemButton
                    selected={selected}
                    onClick={() => go(item.path)}
                    sx={{
                      mx: 0.5,
                      borderRadius: 2,
                      mb: 0.25,
                      '&.Mui-selected': {
                        backgroundColor: 'primary.main',
                        color: 'primary.contrastText',
                        '& .MuiListItemIcon-root': { color: 'inherit' },
                        '&:hover': { backgroundColor: 'primary.dark' },
                      },
                    }}
                  >
                    <ListItemIcon sx={{ minWidth: 40, color: selected ? 'inherit' : 'action.active' }}>{item.icon}</ListItemIcon>
                    <ListItemText primary={item.text} primaryTypographyProps={{ fontWeight: selected ? 600 : 400, fontSize: 15 }} />
                  </ListItemButton>
                </ListItem>
              );
            })}
          </List>
        </>
      )}
      {adminItems.length > 0 && (
        <>
          <Divider sx={{ my: 1 }} />
          <Typography variant="caption" color="text.secondary" sx={{ px: 2, py: 0.5 }}>
            Administración
          </Typography>
          <List sx={{ pt: 0.5, px: 0.5 }}>
            {adminItems.map((item) => {
              const selected = location.pathname === item.path;
              return (
                <ListItem key={item.path} disablePadding>
                  <ListItemButton
                    selected={selected}
                    onClick={() => go(item.path)}
                    sx={{
                      mx: 0.5,
                      borderRadius: 2,
                      mb: 0.25,
                      '&.Mui-selected': {
                        backgroundColor: 'secondary.main',
                        color: 'secondary.contrastText',
                        '& .MuiListItemIcon-root': { color: 'inherit' },
                      },
                    }}
                  >
                    <ListItemIcon sx={{ minWidth: 40, color: selected ? 'inherit' : 'action.active' }}>{item.icon}</ListItemIcon>
                    <ListItemText primary={item.text} primaryTypographyProps={{ fontWeight: selected ? 600 : 400, fontSize: 15 }} />
                  </ListItemButton>
                </ListItem>
              );
            })}
          </List>
        </>
      )}
      {catalogNav.length > 0 && (
        <>
          <Divider sx={{ my: 1 }} />
          <Typography variant="caption" color="text.secondary" sx={{ px: 2, py: 0.5 }}>
            Catálogos
          </Typography>
          <List sx={{ pt: 0.5, px: 0.5 }}>
            {catalogNav.map((item) => {
              const selected = location.pathname === item.path;
              return (
                <ListItem key={item.path} disablePadding>
                  <ListItemButton
                    selected={selected}
                    onClick={() => go(item.path)}
                    sx={{ mx: 0.5, borderRadius: 2, mb: 0.25 }}
                  >
                    <ListItemIcon sx={{ minWidth: 40, color: selected ? 'primary.main' : 'action.active' }}>{item.icon}</ListItemIcon>
                    <ListItemText primary={item.text} primaryTypographyProps={{ fontWeight: selected ? 600 : 400, fontSize: 14 }} />
                  </ListItemButton>
                </ListItem>
              );
            })}
          </List>
        </>
      )}
    </Box>
  );
};

export interface SidebarProps extends SidebarContentProps {
  mobileOpen: boolean;
  onMobileClose: () => void;
  drawerWidth?: number;
}

const Sidebar: React.FC<SidebarProps> = ({
  mobileOpen,
  onMobileClose,
  drawerWidth = SIDEBAR_WIDTH,
  onNavigate,
}) => {
  const handleNav = () => {
    onNavigate?.();
    onMobileClose();
  };

  return (
    <Box
      component="nav"
      sx={{ width: { md: drawerWidth }, flexShrink: { md: 0 } }}
    >
      <Drawer
        variant="temporary"
        open={mobileOpen}
        onClose={onMobileClose}
        ModalProps={{ keepMounted: true }}
        sx={{
          display: { xs: 'block', md: 'none' },
          '& .MuiDrawer-paper': { width: drawerWidth, boxSizing: 'border-box' },
        }}
      >
        <SidebarContent onNavigate={handleNav} />
      </Drawer>
      <Drawer
        variant="permanent"
        open
        sx={{
          display: { xs: 'none', md: 'block' },
          '& .MuiDrawer-paper': {
            width: drawerWidth,
            boxSizing: 'border-box',
            borderRight: 1,
            borderColor: 'divider',
            bgcolor: 'background.paper',
          },
        }}
      >
        <SidebarContent />
      </Drawer>
    </Box>
  );
};

export default Sidebar;
