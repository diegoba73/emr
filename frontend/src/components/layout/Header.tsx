import React, { useState } from 'react';
import {
  AppBar,
  Toolbar,
  Box,
  Typography,
  IconButton,
  Menu,
  MenuItem,
  ListItemIcon,
  Divider,
  Avatar,
  useMediaQuery,
  useTheme,
} from '@mui/material';
import {
  AccountCircle,
  Logout,
  Menu as MenuIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useData } from '../../contexts/DataContext';
import ThemeModeToggle from '../ThemeModeToggle';

const drawerWidth = 260;

export interface AppHeaderProps {
  onOpenMobileNav?: () => void;
  title?: string;
}

const Header: React.FC<AppHeaderProps> = ({ onOpenMobileNav, title }) => {
  const theme = useTheme();
  const isMdUp = useMediaQuery(theme.breakpoints.up('md'));
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const navigate = useNavigate();
  const { currentUser, logout } = useData();

  const getInitials = (user: typeof currentUser): string => {
    if (!user) return 'U';
    if (user.first_name && user.last_name) {
      return `${user.first_name[0]}${user.last_name[0]}`.toUpperCase();
    }
    if (user.username) return user.username.substring(0, 2).toUpperCase();
    return 'U';
  };

  const getUserDisplayName = (user: typeof currentUser): string => {
    if (!user) return 'Usuario';
    if (user.first_name && user.last_name) {
      return `${user.first_name} ${user.last_name}`;
    }
    return user.username || 'Usuario';
  };

  return (
    <AppBar
      position="fixed"
      elevation={0}
      sx={{
        width: { md: `calc(100% - ${drawerWidth}px)` },
        ml: { md: `${drawerWidth}px` },
        backgroundColor: 'background.paper',
        color: 'text.primary',
        borderBottom: 1,
        borderColor: 'divider',
        zIndex: (t) => t.zIndex.drawer + 1,
      }}
    >
      <Toolbar sx={{ gap: 2, minHeight: 64 }}>
        {onOpenMobileNav && !isMdUp && (
          <IconButton
            color="inherit"
            edge="start"
            onClick={onOpenMobileNav}
            aria-label="abrir menú de navegación"
          >
            <MenuIcon />
          </IconButton>
        )}

        <Box sx={{ display: 'flex', alignItems: 'center', minWidth: 0, flexShrink: 0 }}>
          {title && (
            <Typography variant="subtitle1" noWrap fontWeight={600} sx={{ maxWidth: { xs: 160, sm: 320 } }}>
              {title}
            </Typography>
          )}
        </Box>

        <Box sx={{ flexGrow: 1 }} />

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, ml: 'auto' }}>
          <ThemeModeToggle />
          <Typography variant="body2" sx={{ display: { xs: 'none', sm: 'block' } }} noWrap>
            {getUserDisplayName(currentUser)}
          </Typography>
          <IconButton onClick={(e) => setAnchorEl(e.currentTarget)} sx={{ p: 0 }} aria-label="menú de usuario">
            <Avatar sx={{ width: 36, height: 36, bgcolor: 'primary.main' }}>{getInitials(currentUser)}</Avatar>
          </IconButton>
        </Box>

        <Menu
          anchorEl={anchorEl}
          open={Boolean(anchorEl)}
          onClose={() => setAnchorEl(null)}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
          transformOrigin={{ vertical: 'top', horizontal: 'right' }}
        >
          <MenuItem
            onClick={() => {
              setAnchorEl(null);
            }}
          >
            <ListItemIcon>
              <AccountCircle fontSize="small" />
            </ListItemIcon>
            Perfil
          </MenuItem>
          <Divider />
          <MenuItem
            onClick={async () => {
              setAnchorEl(null);
              await logout();
              navigate('/login', { replace: true });
            }}
          >
            <ListItemIcon>
              <Logout fontSize="small" />
            </ListItemIcon>
            Cerrar sesión
          </MenuItem>
        </Menu>
      </Toolbar>
    </AppBar>
  );
};

export { drawerWidth };
export default Header;
