import React, { useState } from 'react';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Paper,
  Typography,
} from '@mui/material';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import {
  postSugerirInterpretacion,
  type SugerirInterpretacionResponse,
} from '../../services/limsApi';

export interface SugerirInterpretacionPanelProps {
  ordenId: number;
  estadoOrden: string;
  disabled?: boolean;
}

const SugerirInterpretacionPanel: React.FC<SugerirInterpretacionPanelProps> = ({
  ordenId,
  estadoOrden,
  disabled = false,
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<SugerirInterpretacionResponse | null>(null);

  if (estadoOrden === 'PENDIENTE') {
    return null;
  }

  const generar = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await postSugerirInterpretacion(ordenId, { prefer_medgemma: true });
      setData(res);
    } catch {
      setError('No se pudo generar la sugerencia. Probá de nuevo.');
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  const fuenteLabel =
    data?.fuente === 'medgemma'
      ? 'Sugerencia MedGemma'
      : data
        ? 'Sugerencia por reglas'
        : null;

  return (
    <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 1, mb: 1 }}>
        <Typography variant="subtitle1" fontWeight={700}>
          Interpretación asistida
        </Typography>
        <Button
          size="small"
          variant="outlined"
          startIcon={loading ? <CircularProgress size={14} /> : <AutoAwesomeIcon />}
          onClick={() => void generar()}
          disabled={disabled || loading}
        >
          Generar sugerencia
        </Button>
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
        Ayuda orientativa para el médico según resultados y historial. No es diagnóstico ni
        informe firmado; no se guarda en la historia clínica hasta que un profesional lo
        incorpore manualmente.
      </Typography>

      {error ? <Alert severity="warning">{error}</Alert> : null}

      {data ? (
        <Alert severity="info" sx={{ alignItems: 'flex-start' }}>
          <Typography variant="caption" display="block" sx={{ mb: 0.5, fontWeight: 600 }}>
            {fuenteLabel}
            {data.modelo ? ` · ${data.modelo}` : ''}
            {typeof data.total_analizados === 'number'
              ? ` · ${data.total_analizados} analitos`
              : ''}
          </Typography>
          <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
            {data.texto}
          </Typography>
        </Alert>
      ) : null}
    </Paper>
  );
};

export default SugerirInterpretacionPanel;
