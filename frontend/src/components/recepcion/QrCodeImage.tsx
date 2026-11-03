import React, { useMemo, useState } from 'react';
import { Box } from '@mui/material';
import { resolveApiBaseUrl } from '../../services/apiBaseUrl';

/**
 * QR offline vía backend local; si falla, fallback externo (solo dibujo).
 */
const QrCodeImage: React.FC<{ value: string; size?: number; alt?: string }> = ({
  value,
  size = 260,
  alt = 'Código QR',
}) => {
  const localSrc = useMemo(() => {
    const base = resolveApiBaseUrl().replace(/\/$/, '');
    return `${base}/recepcion/kiosco-qr.png?data=${encodeURIComponent(value)}`;
  }, [value]);

  const fallbackSrc = useMemo(
    () =>
      `https://api.qrserver.com/v1/create-qr-code/?size=${size}x${size}&margin=10&ecc=M&data=${encodeURIComponent(value)}`,
    [value, size]
  );

  const [src, setSrc] = useState(localSrc);

  // Si cambia el value, volver a intentar el endpoint local
  React.useEffect(() => {
    setSrc(localSrc);
  }, [localSrc]);

  return (
    <Box
      component="img"
      src={src}
      alt={alt}
      width={size}
      height={size}
      onError={() => {
        if (src !== fallbackSrc) setSrc(fallbackSrc);
      }}
      sx={{
        display: 'block',
        mx: 'auto',
        bgcolor: '#fff',
        border: '1px solid #cbd5e1',
        borderRadius: 1,
        p: 1,
      }}
    />
  );
};

export default QrCodeImage;
