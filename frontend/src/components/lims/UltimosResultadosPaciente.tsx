import React, { useEffect, useState } from 'react';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Box,
  CircularProgress,
  Link,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import { useNavigate } from 'react-router-dom';
import { getUltimosResultadosPaciente } from '../../services/limsApi';
import type { TendenciaUltimoResultadoLims, UltimoResultadoItemLims } from '../../types/lims';
import { useData } from '../../contexts/DataContext';
import { pathDetalleOrdenLab } from '../../utils/limsAccess';
import { withNavBack } from '../../utils/navBack';

function formatFechaCorta(iso: string | null | undefined): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleDateString('es-AR', {
      day: '2-digit',
      month: '2-digit',
      year: '2-digit',
    });
  } catch {
    return iso.slice(0, 10);
  }
}

function labelTendencia(t: TendenciaUltimoResultadoLims): string {
  switch (t) {
    case 'sube':
      return '↑';
    case 'baja':
      return '↓';
    case 'igual':
      return '=';
    case 'cambio':
      return '≠';
    default:
      return '—';
  }
}

function formatValor(item: UltimoResultadoItemLims): string {
  const u = (item.unidad || '').trim();
  const v = (item.valor || '').trim() || '—';
  return u ? `${v} ${u}` : v;
}

export interface UltimosResultadosPacienteProps {
  pacienteId: number | null | undefined;
  /** default true: accordion colapsable en el diálogo de pedido */
  compact?: boolean;
  /** Ruta de retorno al abrir el detalle de una orden */
  backPath?: string;
  backLabel?: string;
  /** Ventana en días (default 7). */
  dias?: number;
  /** Máximo de filas (API limit). */
  limit?: number;
  defaultExpanded?: boolean;
}

/**
 * Tabla compacta: analitos informados en los últimos N días (FINALIZADO / parcial),
 * orden tipo informe PDF (paneles juntos). Compara vs valor anterior.
 */
const UltimosResultadosPaciente: React.FC<UltimosResultadosPacienteProps> = ({
  pacienteId,
  compact = true,
  backPath,
  backLabel = '← Volver',
  dias = 7,
  limit = 200,
  defaultExpanded = true,
}) => {
  const navigate = useNavigate();
  const { currentUser } = useData();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [items, setItems] = useState<UltimoResultadoItemLims[]>([]);

  useEffect(() => {
    if (!pacienteId) {
      setItems([]);
      setError('');
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError('');
    getUltimosResultadosPaciente(pacienteId, { dias, limit })
      .then((data) => {
        if (cancelled) return;
        setItems(data.items || []);
      })
      .catch(() => {
        if (cancelled) return;
        setError('No se pudo cargar el historial de resultados.');
        setItems([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [pacienteId, dias, limit]);

  if (!pacienteId) return null;

  const openOrden = (solicitudId: number) => {
    const path = pathDetalleOrdenLab(currentUser, solicitudId);
    if (backPath) {
      navigate(path, withNavBack(backPath, backLabel));
    } else {
      navigate(path);
    }
  };

  const body = (
    <>
      {loading ? (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, py: 1 }}>
          <CircularProgress size={18} />
          <Typography variant="body2" color="text.secondary">
            Cargando últimos resultados…
          </Typography>
        </Box>
      ) : error ? (
        <Typography variant="body2" color="text.secondary">
          {error}
        </Typography>
      ) : items.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          Sin resultados previos informados.
        </Typography>
      ) : (
        <TableContainer sx={{ maxHeight: compact ? 280 : 420 }}>
          <Table size="small" stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell>Analito</TableCell>
                <TableCell>Último valor</TableCell>
                <TableCell>Fecha</TableCell>
                <TableCell align="center" sx={{ width: 56 }}>
                  vs ant.
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {items.map((row) => (
                <TableRow key={`${row.tipo_examen_id}-${row.resultado_id}`} hover>
                  <TableCell>
                    <Typography variant="body2" fontWeight={600}>
                      {row.tipo_examen_nombre}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {row.tipo_examen_codigo}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Link
                      component="button"
                      type="button"
                      variant="body2"
                      onClick={() => openOrden(row.solicitud_id)}
                      underline="hover"
                      sx={{ textAlign: 'left' }}
                    >
                      {formatValor(row)}
                    </Link>
                    {row.valor_anterior ? (
                      <Typography variant="caption" display="block" color="text.secondary">
                        Antes: {row.valor_anterior}
                        {row.unidad ? ` ${row.unidad}` : ''}
                        {row.fecha_anterior ? ` (${formatFechaCorta(row.fecha_anterior)})` : ''}
                      </Typography>
                    ) : null}
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">{formatFechaCorta(row.fecha)}</Typography>
                    {row.solicitud_numero ? (
                      <Typography variant="caption" color="text.secondary" display="block">
                        {row.solicitud_numero}
                      </Typography>
                    ) : null}
                  </TableCell>
                  <TableCell align="center">
                    <Typography
                      variant="body2"
                      title={row.variacion || row.tendencia}
                      fontWeight={600}
                    >
                      {labelTendencia(row.tendencia)}
                    </Typography>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </>
  );

  if (!compact) {
    return (
      <Box sx={{ mb: 2 }}>
        <Typography variant="subtitle2" fontWeight={700} gutterBottom>
          Últimos resultados ({dias} días)
        </Typography>
        {body}
      </Box>
    );
  }

  return (
    <Accordion
      defaultExpanded={defaultExpanded}
      disableGutters
      elevation={0}
      sx={{
        border: 1,
        borderColor: 'divider',
        borderRadius: 1,
        '&:before': { display: 'none' },
      }}
    >
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Typography variant="subtitle2" fontWeight={700}>
          Últimos resultados ({dias} días)
          {!loading && items.length > 0 ? ` · ${items.length}` : ''}
        </Typography>
      </AccordionSummary>
      <AccordionDetails sx={{ pt: 0 }}>{body}</AccordionDetails>
    </Accordion>
  );
};

export default UltimosResultadosPaciente;
