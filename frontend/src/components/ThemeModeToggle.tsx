import React from 'react';
import { IconButton, Tooltip } from '@mui/material';
import { DarkMode, LightMode } from '@mui/icons-material';
import { useThemeMode } from '../contexts/ThemeModeContext';

export type ThemeModeToggleProps = {
  /** Botón claro para fondos oscuros (p. ej. login con gradient) */
  inverse?: boolean;
};

/**
 * Conmuta entre tema claro y oscuro. Preferencia en localStorage (`emr-color-mode`).
 */
const ThemeModeToggle: React.FC<ThemeModeToggleProps> = ({ inverse = false }) => {
  const { mode, toggle } = useThemeMode();

  return (
    <Tooltip title={mode === 'light' ? 'Modo oscuro' : 'Modo claro'}>
      <span>
        <IconButton
          onClick={toggle}
          color="inherit"
          size="small"
          aria-label={mode === 'light' ? 'Activar modo oscuro' : 'Activar modo claro'}
          sx={
            inverse
              ? {
                  color: 'common.white',
                  bgcolor: 'rgba(0,0,0,0.22)',
                  '&:hover': { bgcolor: 'rgba(0,0,0,0.35)' },
                }
              : undefined
          }
        >
          {mode === 'light' ? <DarkMode fontSize="small" /> : <LightMode fontSize="small" />}
        </IconButton>
      </span>
    </Tooltip>
  );
};

export default ThemeModeToggle;
