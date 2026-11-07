import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Link,
  Paper,
  Typography,
} from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
import { getHistorialCultivoMicro } from '../../../services/limsMicroApi';
import type { HistorialCultivoEpisodioLims } from '../../../types/lims';
import { pathDetalleEstudioMicro } from '../../../utils/limsAccess';

function formatFechaCorta(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: '2-digit' });
}

function chipColor(
  desarrollo: HistorialCultivoEpisodioLims['desarrollo']
): 'success' | 'warning' | 'default' {
  if (desarrollo === 'SIN_DESARROLLO') return 'success';
  if (desarrollo === 'CON_DESARROLLO') return 'warning';
  return 'default';
}

export interface HistorialCultivoMicroPanelProps {
  estudioId: number;
  tipoCultivoNombre?: string | null;
}

/**
 * Historial del mismo tipo de cultivo (espejo de «Previos» en carga clínica).
 * Lista cualquier microorganismo aislado en episodios anteriores — no filtra
 * por el organismo del estudio actual.
 */
const HistorialCultivoMicroPanel: React.FC<HistorialCultivoMicroPanelProps> = ({
  estudioId,
  tipoCultivoNombre,
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [previos, setPrevios] = useState<HistorialCultivoEpisodioLims[]>([]);
  const [revision, setRevision] = useState(0);

  const reload = useCallback(() => setRevision((n) => n + 1), []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');
    getHistorialCultivoMicro(estudioId, 10)
      .then((data) => {
        if (cancelled) return;
        setPrevios(data.previos || []);
        setLoading(false);
      })
      .catch(() => {
        if (cancelled) return;
        setError(
          'No se pudo consultar el historial de este cultivo. Reintentá; esto no significa que el paciente no tenga estudios anteriores.'
        );
        setPrevios([]);
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [estudioId, revision]);

  return (
    <Paper variant="outlined" sx={{ p: 2, mt: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap', mb: 1 }}>
        <Typography variant="subtitle1" fontWeight={600}>
          Historial del cultivo
        </Typography>
        {tipoCultivoNombre ? (
          <Typography variant="body2" color="text.secondary">
            ({tipoCultivoNombre})
          </Typography>
        ) : null}
        <Button size="small" disabled={loading} onClick={reload} sx={{ ml: 'auto' }}>
          {loading ? 'Consultando…' : 'Actualizar'}
        </Button>
      </Box>
      <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
        Episodios previos del mismo tipo de cultivo. Se muestran todos los microorganismos
        aislados (pueden diferir entre episodios) y si hubo con/sin desarrollo.
      </Typography>

      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
          <CircularProgress size={28} />
        </Box>
      )}
      {error && (
        <Alert severity="warning" sx={{ mb: 1 }}>
          {error}
        </Alert>
      )}
      {!loading && !error && previos.length === 0 && (
        <Typography variant="body2" color="text.secondary">
          Sin estudios previos informados de este cultivo para el paciente.
        </Typography>
      )}
      {!loading && previos.length > 0 && (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.25 }}>
          {previos.map((p) => (
            <Box
              key={p.estudio_id}
              sx={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: 0.75,
                alignItems: 'center',
                borderBottom: 1,
                borderColor: 'divider',
                pb: 1,
              }}
            >
              <Link
                component={RouterLink}
                to={pathDetalleEstudioMicro(p.estudio_id)}
                underline="hover"
                variant="body2"
                fontWeight={600}
              >
                {p.estudio_numero || `#${p.estudio_id}`}
              </Link>
              <Typography variant="caption" color="text.secondary">
                {formatFechaCorta(p.fecha)}
              </Typography>
              <Chip
                size="small"
                color={chipColor(p.desarrollo)}
                variant="outlined"
                label={p.desarrollo_display}
                sx={{ height: 22 }}
              />
              {p.microorganismos.length === 0 ? (
                <Typography variant="caption" color="text.secondary">
                  Sin microorganismos identificados
                </Typography>
              ) : (
                p.microorganismos.map((m) => (
                  <Chip
                    key={`${p.estudio_id}-${m.microorganismo_id}`}
                    size="small"
                    label={m.nombre}
                    sx={{ height: 22, '& .MuiChip-label': { px: 0.75, fontSize: '0.7rem' } }}
                  />
                ))
              )}
            </Box>
          ))}
        </Box>
      )}
    </Paper>
  );
};

export default HistorialCultivoMicroPanel;
