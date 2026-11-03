import React, { useEffect, useMemo, useState } from 'react';
import { Alert, Box, Button, Paper, TextField, Typography } from '@mui/material';
import QrCodeImage from '../components/recepcion/QrCodeImage';
import { getKioscoConfig } from '../services/recepcionApi';
import {
  getStoredKioscoPublicOrigin,
  resolveKioscoPublicOrigin,
  setStoredKioscoPublicOrigin,
} from '../utils/kioscoPublicOrigin';

/**
 * Cartel imprimible: QR fijo que abre el anuncio de llegada (/kiosco-recepcion).
 * En CEHTA/prod apunta a la URL pública del EMR (no IP LAN).
 * Ruta staff: /recepcion/qr-anuncio
 */
const QrAnuncioImprimible: React.FC = () => {
  const [apiOrigin, setApiOrigin] = useState('');
  const [hostDraft, setHostDraft] = useState(() => {
    const stored = getStoredKioscoPublicOrigin();
    if (!stored) return '';
    try {
      return new URL(stored).host;
    } catch {
      return stored.replace(/^https?:\/\//i, '');
    }
  });
  const [publicOrigin, setPublicOrigin] = useState(() => resolveKioscoPublicOrigin());

  useEffect(() => {
    void getKioscoConfig()
      .then((cfg) => {
        if (cfg.espera_origin) {
          setApiOrigin(cfg.espera_origin);
          const next = resolveKioscoPublicOrigin(cfg.espera_origin);
          if (next) setPublicOrigin(next);
        }
      })
      .catch(() => undefined);
  }, []);

  const anuncioUrl = useMemo(() => {
    const origin = resolveKioscoPublicOrigin(apiOrigin || publicOrigin);
    if (!origin) return '';
    return `${origin.replace(/\/$/, '')}/kiosco-recepcion`;
  }, [apiOrigin, publicOrigin]);

  const aplicarHost = () => {
    const raw = hostDraft.trim().replace(/\/$/, '');
    if (!raw) return;
    let origin: string;
    if (/^https?:\/\//i.test(raw)) {
      origin = raw.replace(/\/$/, '');
    } else if (raw.includes('.') && !/^\d+\.\d+\.\d+\.\d+/.test(raw.split(':')[0])) {
      // Dominio público sin esquema → HTTPS (prod CEHTA/ICPL)
      origin = `https://${raw}`;
    } else {
      // IP LAN de desarrollo
      origin = raw.includes(':') ? `http://${raw}` : `http://${raw}:3000`;
    }
    setStoredKioscoPublicOrigin(origin);
    setPublicOrigin(origin);
  };

  return (
    <Box sx={{ p: 2, maxWidth: 720, mx: 'auto' }}>
      <Typography variant="h5" fontWeight={800} gutterBottom>
        QR de anuncio (imprimir)
      </Typography>
      <Typography sx={{ mb: 2, color: 'text.secondary' }}>
        Pegá este cartel en recepción (CEHTA o ICPL). El paciente escanea y elige recepción
        (puesto 1) o sala de extracción. El enlace debe ser la URL pública del EMR, por ejemplo{' '}
        <strong>https://emr.icpueblodeluis.com.ar:8080/kiosco-recepcion</strong>.
      </Typography>

      {!anuncioUrl && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          No hay origen configurado. En producción usá{' '}
          <code>PUBLIC_API_BASE_URL=https://emr.icpueblodeluis.com.ar:8080</code> en el servidor.
          Como override temporal podés pegar el host acá:
          <Box sx={{ display: 'flex', gap: 1, mt: 1.5, flexWrap: 'wrap' }}>
            <TextField
              size="small"
              label="URL o host"
              value={hostDraft}
              onChange={(e) => setHostDraft(e.target.value)}
              placeholder="emr.icpueblodeluis.com.ar:8080"
              sx={{ minWidth: 280 }}
            />
            <Button variant="contained" onClick={aplicarHost} disabled={!hostDraft.trim()}>
              Usar
            </Button>
          </Box>
        </Alert>
      )}

      {anuncioUrl && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Origen del QR: {anuncioUrl.replace(/\/kiosco-recepcion$/, '')}. Si necesitás forzar otro,
          pegá host/URL y aplicá:
          <Box sx={{ display: 'flex', gap: 1, mt: 1.5, flexWrap: 'wrap' }}>
            <TextField
              size="small"
              label="Override (opcional)"
              value={hostDraft}
              onChange={(e) => setHostDraft(e.target.value)}
              placeholder="emr.icpueblodeluis.com.ar:8080"
              sx={{ minWidth: 280 }}
            />
            <Button variant="outlined" onClick={aplicarHost} disabled={!hostDraft.trim()}>
              Guardar override
            </Button>
            <Button
              variant="text"
              onClick={() => {
                setStoredKioscoPublicOrigin('');
                setHostDraft('');
                setPublicOrigin(resolveKioscoPublicOrigin(apiOrigin));
              }}
            >
              Quitar override
            </Button>
          </Box>
        </Alert>
      )}

      <Paper
        elevation={0}
        sx={{
          p: 4,
          textAlign: 'center',
          border: '2px solid #0f172a',
          borderRadius: 2,
          bgcolor: '#fff',
        }}
      >
        <Typography variant="h4" fontWeight={900} sx={{ mb: 1, letterSpacing: 1 }}>
          RECEPCIÓN
        </Typography>
        <Typography sx={{ mb: 3, fontSize: '1.15rem', fontWeight: 600 }}>
          Escanee el QR para anunciarse
        </Typography>
        {anuncioUrl ? (
          <>
            <QrCodeImage value={anuncioUrl} size={280} />
            <Typography sx={{ mt: 2, fontSize: '0.85rem', wordBreak: 'break-all', color: '#64748b' }}>
              {anuncioUrl}
            </Typography>
          </>
        ) : (
          <Typography color="text.secondary">Sin URL todavía</Typography>
        )}
      </Paper>

      <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
        <Button variant="outlined" onClick={() => window.print()} disabled={!anuncioUrl}>
          Imprimir
        </Button>
      </Box>
    </Box>
  );
};

export default QrAnuncioImprimible;
