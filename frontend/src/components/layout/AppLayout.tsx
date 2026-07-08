import React, { useState } from 'react';
import { Box, Toolbar, useMediaQuery, useTheme } from '@mui/material';
import { Outlet, useLocation } from 'react-router-dom';
import Sidebar, { SIDEBAR_WIDTH } from './Sidebar';
import Header from './Header';
import { useData } from '../../contexts/DataContext';
import { getAppSegmentTitle } from '../../utils/navLabels';

/**
 * Layout principal: barra lateral fija, header superior, área de contenido con scroll.
 */
const AppLayout: React.FC = () => {
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();
  const theme = useTheme();
  const isMd = useMediaQuery(theme.breakpoints.up('md'));
  const { currentUser } = useData();

  const segmentTitle = getAppSegmentTitle(location.pathname, currentUser);

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
      <Header
        title={isMd ? segmentTitle : 'Synesis EMR'}
        onOpenMobileNav={() => setMobileOpen(true)}
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
