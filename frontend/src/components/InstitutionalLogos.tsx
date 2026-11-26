import React from 'react';
import { Box } from '@mui/material';
import { useTheme } from '@mui/material/styles';

interface InstitutionalLogosProps {
  /** Alto máximo de la franja (el ancho se adapta al contenedor). */
  height?: number;
  className?: string;
  /** `compact` sidebar; `login` más aire. */
  variant?: 'compact' | 'login';
}

function publicAsset(file: string): string {
  const base = (process.env.PUBLIC_URL || '').replace(/\/$/, '');
  return `${base}/${file}`;
}

/**
 * Par institucional: ICPL (SVG) | CEHTA (marca oficial, PNG transparente).
 * Siempre en fila; se adapta al ancho del contenedor.
 */
const InstitutionalLogos: React.FC<InstitutionalLogosProps> = ({
  height = 72,
  className = '',
  variant = 'compact',
}) => {
  const theme = useTheme();
  const dark = theme.palette.mode === 'dark';
  const gap = variant === 'login' ? 2 : 1.25;
  const ruleH = Math.round(height * 0.55);

  const icplSrc = publicAsset(dark ? 'synesis-logo-dark.svg' : 'synesis-logo.svg');
  // SVG nítido: CEHTA + CARDIOVASCULAR + corazón (sin subtítulo).
  const cehtaSrc = publicAsset(dark ? 'cehta-logo-dark.svg' : 'cehta-logo.svg');

  return (
    <Box
      className={`institutional-logos ${className}`}
      sx={{
        display: 'flex',
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        gap,
        width: '100%',
        minWidth: 0,
      }}
      aria-label="Instituciones: Pueblo de Luis y CEHTA"
    >
      <Box
        component="img"
        src={icplSrc}
        alt="Instituto de Cardiología Pueblo de Luis"
        sx={{
          height,
          width: 'auto',
          maxWidth: '46%',
          objectFit: 'contain',
          display: 'block',
          flex: '1 1 0',
          minWidth: 0,
          backgroundColor: 'transparent',
        }}
      />
      <Box
        aria-hidden
        sx={{
          width: '1px',
          height: ruleH,
          flexShrink: 0,
          bgcolor: 'divider',
          opacity: 0.8,
        }}
      />
      <Box
        component="img"
        src={cehtaSrc}
        alt="CEHTA Cardiovascular"
        sx={{
          height: height * 0.92,
          width: 'auto',
          maxWidth: '50%',
          objectFit: 'contain',
          display: 'block',
          flex: '1 1 0',
          minWidth: 0,
          backgroundColor: 'transparent',
        }}
      />
    </Box>
  );
};

export default InstitutionalLogos;
