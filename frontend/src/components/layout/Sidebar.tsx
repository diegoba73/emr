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
  Emergency as EmergencyIcon,
  Folder as FolderIcon,
  AssignmentTurnedIn as SolicitudIcon,
  MenuBook as CatalogIcon,
  FactCheck as AuditIcon,
  Science as ScienceIcon,
  Biotech as BiotechIcon,
  HourglassEmpty as PendientesIcon,
  Description,
  QrCodeScanner as BarcodeIcon,
  Inventory as RecepcionIcon,
  Inventory2 as InventarioIcon,
  Analytics as QcIcon,
  Insights as BiIcon,
  Timeline as PortalTimelineIcon,
  MeetingRoom as MeetingRoomIcon,
} from '@mui/icons-material';
import { useLocation, useNavigate } from 'react-router-dom';
import { useData } from '../../contexts/DataContext';
import { User } from '../../types';
import Logo from '../Logo';
import {
  canAccessArchivosMedicos,
  canAccessAtenciones,
  canAccessAuditoria,
  canAccessBiDashboard,
  canAccessCatalogosClinicos,
  canAccessPacientes,
  canAccessPortal,
  canAccessPortalDocumentos,
  canAccessPortalHistoria,
  canAccessPortalResultados,
  canAccessPortalTurnos,
  canAccessSolicitudes,
  isLaboratorioRole,
  isPacienteRole,
} from '../../utils/permissions';
import { canAccessEstudiosModule } from '../../modules/estudios/permissions';
import {
  canAccessLimsCatalogos,
  canAccessLimsPendientes,
  canAccessLimsOrdenes,
  canAccessLimsModule,
  canAccessMicrobiologia,
  canOperateLims,
} from '../../utils/limsAccess';
import { canAccessTurnosAgenda } from '../../utils/turnoPermissions';
import { getHomeNavLabel, getSolicitudesModuleLabel } from '../../utils/navLabels';

export const SIDEBAR_WIDTH = 260;

export interface NavItem {
  text: string;
  path: string;
  icon: React.ReactElement;
  /** @deprecated usar canAccessNavItem */
  roles?: string[];
  canAccess?: (user: User | null) => boolean;
  /** Resuelve etiqueta según rol (p. ej. Laboratorio / Análisis Clínico). */
  resolveLabel?: (user: User | null) => string;
}

const navItems: NavItem[] = [
  { text: 'Inicio', icon: <HomeIcon />, path: '/dashboard', canAccess: (u) => !isPacienteRole(u), resolveLabel: () => getHomeNavLabel() },
  { text: 'Pacientes', icon: <PeopleIcon />, path: '/pacientes', canAccess: (u) => canAccessPacientes(u) && !isLaboratorioRole(u) },
  { text: 'Turnos', icon: <CalendarIcon />, path: '/turnos', canAccess: canAccessTurnosAgenda },
  { text: 'Atenciones Clínicas', icon: <LocalHospital />, path: '/atenciones', canAccess: canAccessAtenciones },
  { text: 'Guardia', icon: <EmergencyIcon />, path: '/guardia', canAccess: canAccessAtenciones },
  { text: 'Archivos', icon: <FolderIcon />, path: '/archivos', canAccess: canAccessArchivosMedicos },
  {
    text: 'Estudios complementarios',
    icon: <Description />,
    path: '/estudios-complementarios',
    canAccess: canAccessEstudiosModule,
  },
  {
    text: 'Laboratorio',
    icon: <SolicitudIcon />,
    path: '/solicitudes',
    canAccess: canAccessSolicitudes,
    resolveLabel: getSolicitudesModuleLabel,
  },
  { text: 'Internación', icon: <LocalHospital />, path: '/internacion', roles: ['medico', 'admin', 'enfermeria'] },
  { text: 'Indicadores', icon: <BiIcon />, path: '/bi', canAccess: canAccessBiDashboard },
];

const portalItems: NavItem[] = [
  { text: 'Mi portal', icon: <HomeIcon />, path: '/portal', canAccess: canAccessPortal },
  { text: 'Mis turnos', icon: <CalendarIcon />, path: '/portal/turnos', canAccess: canAccessPortalTurnos },
  { text: 'Mis resultados', icon: <ScienceIcon />, path: '/portal/resultados', canAccess: canAccessPortalResultados },
  { text: 'Mis documentos', icon: <FolderIcon />, path: '/portal/documentos', canAccess: canAccessPortalDocumentos },
  { text: 'Mi historia', icon: <PortalTimelineIcon />, path: '/portal/historia', canAccess: canAccessPortalHistoria },
];

const adminOnly: NavItem[] = [
  { text: 'Médicos', icon: <PeopleIcon />, path: '/medicos', roles: ['admin'] },
  { text: 'Usuarios', icon: <PeopleIcon />, path: '/usuarios', roles: ['admin'] },
  { text: 'Recursos', icon: <MeetingRoomIcon />, path: '/recursos', roles: ['admin'] },
  { text: 'Auditoría', icon: <AuditIcon />, path: '/auditoria', canAccess: canAccessAuditoria },
];

const labItems: NavItem[] = [
  { text: 'Consulta muestra', icon: <BarcodeIcon />, path: '/laboratorio/muestras/consulta', canAccess: canAccessLimsModule },
  { text: 'Pendientes', icon: <PendientesIcon />, path: '/laboratorio/pendientes', canAccess: canAccessLimsPendientes },
  { text: 'Recepción muestras', icon: <RecepcionIcon />, path: '/laboratorio/muestras/recepcion', canAccess: canOperateLims },
  { text: 'Órdenes LIMS', icon: <ScienceIcon />, path: '/laboratorio/ordenes', canAccess: canAccessLimsOrdenes },
  { text: 'Microbiología', icon: <BiotechIcon />, path: '/laboratorio/microbiologia/estudios', canAccess: canAccessMicrobiologia },
  { text: 'Inventario', icon: <InventarioIcon />, path: '/laboratorio/inventario', canAccess: canAccessLimsModule },
  { text: 'Control calidad', icon: <QcIcon />, path: '/laboratorio/qc', canAccess: canAccessLimsModule },
];

const labCatalogItems: NavItem[] = [
  { text: 'Exámenes', icon: <CatalogIcon />, path: '/laboratorio/catalogos/examenes', canAccess: canAccessLimsCatalogos },
  { text: 'Tipos de muestra', icon: <CatalogIcon />, path: '/laboratorio/catalogos/tipos-muestra', canAccess: canAccessLimsCatalogos },
  { text: 'Paneles', icon: <CatalogIcon />, path: '/laboratorio/catalogos/paneles', canAccess: canAccessLimsCatalogos },
  { text: 'Catálogos micro', icon: <CatalogIcon />, path: '/laboratorio/microbiologia/catalogos', canAccess: canAccessMicrobiologia },
];

const catalogItems: NavItem[] = [
  { text: 'CIE-10', icon: <CatalogIcon />, path: '/catalogos/diagnosticos', canAccess: canAccessCatalogosClinicos },
  { text: 'Estudios', icon: <CatalogIcon />, path: '/catalogos/estudios', canAccess: canAccessCatalogosClinicos },
  { text: 'Procedimientos', icon: <CatalogIcon />, path: '/catalogos/procedimientos', canAccess: canAccessCatalogosClinicos },
  { text: 'Medicamentos', icon: <CatalogIcon />, path: '/catalogos/medicamentos', canAccess: canAccessCatalogosClinicos },
  { text: 'Especialidades', icon: <CatalogIcon />, path: '/catalogos/especialidades', canAccess: canAccessCatalogosClinicos },
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

  const primary = filterByRole(isPacienteRole(currentUser) ? portalItems : navItems, currentUser);
  const adminItems = filterByRole(adminOnly, currentUser);
  const catalogNav = filterByRole(catalogItems, currentUser);
  const labNav = isPacienteRole(currentUser) ? [] : filterByRole(labItems, currentUser);
  const labCatalogNav = isPacienteRole(currentUser) ? [] : filterByRole(labCatalogItems, currentUser);

  const go = (path: string) => {
    navigate(path);
    onNavigate?.();
  };

  const navButtonSx = {
    mx: 0.5,
    borderRadius: 2,
    mb: 0.25,
    '&.Mui-selected': {
      backgroundColor: 'primary.main',
      color: 'primary.contrastText',
      '& .MuiListItemIcon-root': { color: 'inherit' },
      '&:hover': { backgroundColor: 'primary.dark' },
    },
  } as const;

  const isLabPathSelected = (item: NavItem) => {
    const p = location.pathname;
    if (p === item.path || p.startsWith(`${item.path}/`)) return true;
    // Microbiología: estudios y detalle, sin marcar cuando estás en catálogos micro.
    if (item.path === '/laboratorio/microbiologia/estudios') {
      return (
        p.startsWith('/laboratorio/microbiologia') &&
        !p.startsWith('/laboratorio/microbiologia/catalogos')
      );
    }
    return false;
  };

  const renderNavList = (items: NavItem[], selectedFn: (item: NavItem) => boolean) => (
    <List sx={{ pt: 0.5, px: 0.5 }}>
      {items.map((item) => {
        const selected = selectedFn(item);
        return (
          <ListItem key={item.path} disablePadding>
            <ListItemButton selected={selected} onClick={() => go(item.path)} sx={navButtonSx}>
              <ListItemIcon sx={{ minWidth: 40, color: selected ? 'inherit' : 'action.active' }}>
                {item.icon}
              </ListItemIcon>
              <ListItemText
                primary={item.resolveLabel ? item.resolveLabel(currentUser) : item.text}
                primaryTypographyProps={{ fontWeight: selected ? 600 : 400, fontSize: 15 }}
              />
            </ListItemButton>
          </ListItem>
        );
      })}
    </List>
  );

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
        {isPacienteRole(currentUser) ? 'Mi portal' : 'Principal'}
      </Typography>
      {renderNavList(primary, (item) => location.pathname === item.path)}
      {labNav.length > 0 && (
        <>
          <Divider sx={{ my: 1 }} />
          <Typography variant="caption" color="text.secondary" sx={{ px: 2, py: 0.5 }}>
            Laboratorio (LIMS)
          </Typography>
          {renderNavList(labNav, isLabPathSelected)}
        </>
      )}
      {labCatalogNav.length > 0 && (
        <>
          <Divider sx={{ my: 1 }} />
          <Typography variant="caption" color="text.secondary" sx={{ px: 2, py: 0.5 }}>
            Catálogos LIMS
          </Typography>
          {renderNavList(labCatalogNav, isLabPathSelected)}
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
                    <ListItemIcon sx={{ minWidth: 40, color: selected ? 'inherit' : 'action.active' }}>
                      {item.icon}
                    </ListItemIcon>
                    <ListItemText
                      primary={item.text}
                      primaryTypographyProps={{ fontWeight: selected ? 600 : 400, fontSize: 15 }}
                    />
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
            Catálogos clínicos
          </Typography>
          {renderNavList(catalogNav, (item) => location.pathname === item.path)}
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
