import React from 'react';
import { readDemoTourRole } from '../demo/demoStorage';
import { useTheme } from '@mui/material/styles';

interface LogoProps {
  size?: number;
  className?: string;
  demo?: boolean;
  inverse?: boolean;
}

/** Rutas en `public/` para que el build sirva el archivo con URL estable (evita imports rotos al desplegar). */
function logoSrc(mode: 'light' | 'dark', demo: boolean): string {
  const base = (process.env.PUBLIC_URL || '').replace(/\/$/, '');
  const file = demo
    ? `demo-logo-${mode}.svg`
    : mode === 'dark' ? 'synesis-logo-dark.svg' : 'synesis-logo.svg';
  return `${base}/${file}`;
}

const Logo: React.FC<LogoProps> = ({ size = 800, className = '', demo = false, inverse = false }) => {
  const theme = useTheme();
  const mode = inverse ? 'dark' : theme.palette.mode;
  const demoBrand = demo || process.env.REACT_APP_DEMO_MODE === 'true' || readDemoTourRole() != null;
  const src = logoSrc(mode, demoBrand);

  return (
    <div className={`logo-component ${className}`} style={{ width: size, height: size }}>
      <img
        src={src}
        alt={demoBrand ? 'EMR Demo — entorno de ejemplo' : 'Synesis EMR'}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'contain',
          maxWidth: '100%',
        }}
      />
    </div>
  );
};

export default Logo;
