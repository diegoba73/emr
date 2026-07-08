import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Collapse,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import type { AnalisisLongitudinalOrden } from '../../types/lims';
import { getAnalisisLongitudinal } from '../../services/limsApi';

export interface AnalisisLongitudinalPanelProps {
  ordenId: number;
  estadoOrden: string;
  totalResultados: number;
  /** Cambia al guardar resultados para forzar recarga del análisis. */
  resultadosFingerprint?: string;
}

const VARIACION_LABEL: Record<string, string> = {
  sin_historial: 'Sin historial',
  estable: 'Estable',
  moderada: 'Moderada',
  significativa: 'Significativa',
  brusca: 'Brusca',
  cambio_cualitativo: 'Cambio cualitativo',
  cambio_valor: 'Cambio de valor',
  sin_comparacion_numerica: '—',
};

const VARIACION_COLOR: Record<string, 'default' | 'success' | 'warning' | 'error' | 'info'> = {
  sin_historial: 'default',
  estable: 'success',
  moderada: 'warning',
  significativa: 'warning',
  brusca: 'error',
  cambio_cualitativo: 'info',
  cambio_valor: 'info',
  sin_comparacion_numerica: 'default',
};

const AnalisisLongitudinalPanel: React.FC<AnalisisLongitudinalPanelProps> = ({
  ordenId,
  estadoOrden,
  totalResultados,
  resultadosFingerprint = '',
}) => {
  const [data, setData] = useState<AnalisisLongitudinalOrden | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detalleAbierto, setDetalleAbierto] = useState(false);

  const cargar = useCallback(async () => {
    if (estadoOrden === 'PENDIENTE') return;
    setLoading(true);
    setError(null);
    try {
      const res = await getAnalisisLongitudinal(ordenId);
      setData(res);
    } catch {
      setError('No se pudo obtener el análisis longitudinal.');
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [estadoOrden, ordenId]);

  useEffect(() => {
    if (estadoOrden === 'PENDIENTE' || totalResultados === 0) return;
    void cargar();
  }, [cargar, estadoOrden, totalResultados, ordenId, resultadosFingerprint]);

  if (estadoOrden === 'PENDIENTE') {
    return null;
  }

  return (
    <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 1, mb: 1 }}>
        <Typography variant="subtitle1" fontWeight={700}>
          Análisis vs referencia e historial
        </Typography>
        <Button
          size="small"
          startIcon={loading ? <CircularProgress size={14} /> : <RefreshIcon />}
          onClick={() => void cargar()}
          disabled={loading}
        >
          Actualizar
        </Button>
        {data ? (
          <Chip
            size="small"
            label={`${data.total_analizados} analizados · ${data.total_con_historial} con historial`}
            variant="outlined"
          />
        ) : null}
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
        Comparación automática con rangos del catálogo y el último resultado previo del paciente.
        Sugerencia operativa — no reemplaza la validación del profesional.
      </Typography>

      {error ? <Alert severity="warning">{error}</Alert> : null}

      {!error && loading && !data ? (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, py: 1 }}>
          <CircularProgress size={20} />
          <Typography variant="body2" color="text.secondary">
            Analizando resultados…
          </Typography>
        </Box>
      ) : null}

      {data && data.resumen_alertas.length > 0 ? (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mb: 1 }}>
          {data.resumen_alertas.map((alerta) => (
            <Alert key={alerta} severity="warning" variant="outlined">
              {alerta}
            </Alert>
          ))}
        </Box>
      ) : null}

      {data && data.total_analizados > 0 && data.resumen_alertas.length === 0 ? (
        <Alert severity="success" variant="outlined" sx={{ mb: 1 }}>
          Sin alertas de referencia ni variación histórica significativa en los resultados cargados.
        </Alert>
      ) : null}

      {data && data.total_analizados === 0 ? (
        <Alert severity="info" variant="outlined">
          Cargá al menos un resultado con valor para ver el análisis.
        </Alert>
      ) : null}

      {data && data.total_analizados > 0 ? (
        <>
          <Button size="small" onClick={() => setDetalleAbierto((v) => !v)} sx={{ mt: 0.5 }}>
            {detalleAbierto ? 'Ocultar detalle' : 'Ver detalle por examen'}
          </Button>
          <Collapse in={detalleAbierto}>
            <TableContainer sx={{ mt: 1 }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Examen</TableCell>
                    <TableCell>Valor</TableCell>
                    <TableCell>Referencia</TableCell>
                    <TableCell>Historial</TableCell>
                    <TableCell>Variación</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {data.resultados.map((item) => {
                    const variacion = item.historial.variacion;
                    return (
                      <TableRow key={item.resultado_id}>
                        <TableCell>
                          {item.tipo_examen_nombre}
                          {item.tipo_examen_codigo ? (
                            <Typography component="span" variant="caption" color="text.secondary" sx={{ ml: 0.5 }}>
                              ({item.tipo_examen_codigo})
                            </Typography>
                          ) : null}
                        </TableCell>
                        <TableCell>
                          {item.valor_actual}
                          {item.unidad ? ` ${item.unidad}` : ''}
                        </TableCell>
                        <TableCell>
                          {item.referencia.es_critico ? (
                            <Chip size="small" label="Crítico" color="error" />
                          ) : item.referencia.es_patologico ? (
                            <Chip size="small" label="Fuera de rango" color="warning" />
                          ) : item.referencia.en_rango ? (
                            <Chip size="small" label="En rango" color="success" variant="outlined" />
                          ) : (
                            '—'
                          )}
                        </TableCell>
                        <TableCell>
                          {item.historial.tiene_historial ? (
                            <>
                              {item.historial.valor_anterior}
                              {item.historial.dias_desde_anterior != null
                                ? ` (${item.historial.dias_desde_anterior} d)`
                                : ''}
                            </>
                          ) : (
                            'Sin previo'
                          )}
                        </TableCell>
                        <TableCell>
                          <Chip
                            size="small"
                            label={VARIACION_LABEL[variacion] ?? variacion}
                            color={VARIACION_COLOR[variacion] ?? 'default'}
                            variant="outlined"
                          />
                          {item.historial.delta_porcentual ? (
                            <Typography variant="caption" display="block" color="text.secondary">
                              {item.historial.delta_porcentual}%
                            </Typography>
                          ) : null}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </TableContainer>
          </Collapse>
        </>
      ) : null}
    </Paper>
  );
};

export default AnalisisLongitudinalPanel;
