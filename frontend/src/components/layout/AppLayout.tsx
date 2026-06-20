import React, { useState } from 'react';
import { Box, Toolbar, useMediaQuery, useTheme } from '@mui/material';
import { Outlet, useLocation } from 'react-router-dom';
import Sidebar, { SIDEBAR_WIDTH } from './Sidebar';
import Header from './Header';

/**
 * Layout principal: barra lateral fija, header superior, área de contenido con scroll.
 */
const AppLayout: React.FC = () => {
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();
  const theme = useTheme();
  const isMd = useMediaQuery(theme.breakpoints.up('md'));

  const segmentTitle = (() => {
    const p = location.pathname;
    if (p.startsWith('/paciente/')) return 'Paciente 360';
    if (p.startsWith('/dashboard')) return 'Inicio';
    if (p.startsWith('/pacientes')) return 'Pacientes';
    if (p.startsWith('/turnos')) return 'Turnos';
    if (p.startsWith('/atenciones')) return 'Consultas clínicas';
    if (p.startsWith('/archivos-medicos')) return 'Archivos médicos';
    if (p.startsWith('/solicitudes')) return 'Solicitudes';
    if (p.startsWith('/mis-consultas')) return 'Mis consultas';
    if (p.startsWith('/internacion')) return 'Internación';
    if (p.startsWith('/medicos')) return 'Médicos';
    if (p.startsWith('/usuarios')) return 'Usuarios';
    if (p.startsWith('/catalogos')) return 'Catálogos';
    return 'Synesis EMR';
  })();

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
      <Header
        title={isMd ? segmentTitle : 'Synesis EMR'}
        onOpenMobileNav={() => setMobileOpen(true)}
        showGlobalSearch
      />
      <Sidebar
        mobileOpen={mobileOpen}
        onMobileClose={() => setMobileOpen(false)}
        drawerWidth={SIDEBAR_WIDTH}
        onNavigate={() => setMobileOpen(false)}
      />
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          width: { md: `calc(100% - ${SIDEBAR_WIDTH}px)` },
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <Toolbar />
        <Box
          sx={{
            flex: 1,
            overflow: 'auto',
            px: { xs: 1.5, sm: 2, md: 3 },
            py: { xs: 1.5, md: 2 },
            pb: 4,
          }}
        >
          <Outlet />
        </Box>
      </Box>
    </Box>
  );
};

export default AppLayout;
