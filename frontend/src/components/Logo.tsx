import React from 'react';
import { useTheme } from '@mui/material/styles';

interface LogoProps {
  size?: number;
  className?: string;
}

/** Rutas en `public/` para que el build sirva el archivo con URL estable (evita imports rotos al desplegar). */
function logoSrc(mode: 'light' | 'dark'): string {
  const base = (process.env.PUBLIC_URL || '').replace(/\/$/, '');
  const file = mode === 'dark' ? 'synesis-logo-dark.svg' : 'synesis-logo.svg';
  return `${base}/${file}`;
}

const Logo: React.FC<LogoProps> = ({ size = 800, className = '' }) => {
  const theme = useTheme();
  const mode = theme.palette.mode;
  const src = logoSrc(mode);

  return (
    <div className={`logo-component ${className}`} style={{ width: size, height: size }}>
      <img
        src={src}
        alt="Synesis EMR"
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
