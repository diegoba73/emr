import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
  useTheme,
} from '@mui/material';
import { getHistorialAnalitos } from '../../services/limsApi';
import {
  armarSerieTendencia,
  puntosNumericos,
  type PuntoTendenciaAnalito,
} from './tendenciaAnalitoSerie';

export interface TendenciaAnalitoActual {
  valor: string;
  valor_numerico?: string | number | null;
  unidad?: string | null;
  fecha?: string | null;
  solicitudNumero?: string | null;
  rango_min?: string | number | null;
  rango_max?: string | number | null;
}

export interface TendenciaAnalitoDialogProps {
  open: boolean;
  onClose: () => void;
  solicitudId: number;
  tipoExamenId: number;
  tipoExamenNombre: string;
  tipoExamenCodigo?: string | null;
  actual?: TendenciaAnalitoActual | null;
}

function formatFechaCorta(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: '2-digit' });
}

function parseRango(raw: string | number | null | undefined): number | null {
  if (raw == null || raw === '') return null;
  const n = typeof raw === 'number' ? raw : Number(String(raw).replace(',', '.').trim());
  return Number.isFinite(n) ? n : null;
}

const CHART_W = 560;
const CHART_H = 220;
const PAD = { top: 16, right: 16, bottom: 36, left: 48 };

function TendenciaChartSvg({
  puntos,
  rangoMin,
  rangoMax,
  unidad,
}: {
  puntos: PuntoTendenciaAnalito[];
  rangoMin: number | null;
  rangoMax: number | null;
  unidad: string | null;
}) {
  const theme = useTheme();
  const nums = puntos.map((p) => p.valorNumerico as number);
  let yMin = Math.min(...nums);
  let yMax = Math.max(...nums);
  if (rangoMin != null) yMin = Math.min(yMin, rangoMin);
  if (rangoMax != null) yMax = Math.max(yMax, rangoMax);
  if (yMin === yMax) {
    yMin -= 1;
    yMax += 1;
  }
  const padY = (yMax - yMin) * 0.08;
  yMin -= padY;
  yMax += padY;

  const innerW = CHART_W - PAD.left - PAD.right;
  const innerH = CHART_H - PAD.top - PAD.bottom;

  const xAt = (i: number) =>
    PAD.left + (puntos.length === 1 ? innerW / 2 : (i / (puntos.length - 1)) * innerW);
  const yAt = (v: number) => PAD.top + ((yMax - v) / (yMax - yMin)) * innerH;

  const linePts = puntos.map((p, i) => `${xAt(i)},${yAt(p.valorNumerico as number)}`).join(' ');

  const ticks = 4;
  const yTicks = Array.from({ length: ticks + 1 }, (_, i) => yMin + ((yMax - yMin) * i) / ticks);

  let band: { y1: number; y2: number } | null = null;
  if (rangoMin != null && rangoMax != null) {
    band = { y1: yAt(rangoMax), y2: yAt(rangoMin) };
  }

  const axisColor = theme.palette.text.secondary;
  const lineColor = theme.palette.primary.main;
  const actualColor = theme.palette.secondary.main;

  return (
    <Box sx={{ width: '100%', overflowX: 'auto' }}>
      <svg
        viewBox={`0 0 ${CHART_W} ${CHART_H}`}
        width="100%"
        role="img"
        aria-label={`Tendencia${unidad ? ` (${unidad})` : ''}`}
      >
        {band && (
          <rect
            x={PAD.left}
            y={band.y1}
            width={innerW}
            height={Math.max(0, band.y2 - band.y1)}
            fill={theme.palette.success.main}
            opacity={0.12}
          />
        )}
        {yTicks.map((v) => (
          <g key={v}>
            <line
              x1={PAD.left}
              x2={CHART_W - PAD.right}
              y1={yAt(v)}
              y2={yAt(v)}
              stroke={axisColor}
              strokeOpacity={0.25}
            />
            <text
              x={PAD.left - 6}
              y={yAt(v)}
              textAnchor="end"
              dominantBaseline="middle"
              fontSize={10}
              fill={axisColor}
            >
              {v.toLocaleString('es-AR', { maximumFractionDigits: 2 })}
            </text>
          </g>
        ))}
        <polyline fill="none" stroke={lineColor} strokeWidth={2} points={linePts} />
        {puntos.map((p, i) => (
          <g key={`${p.solicitudId ?? 'a'}-${i}`}>
            <circle
              cx={xAt(i)}
              cy={yAt(p.valorNumerico as number)}
              r={p.esActual ? 5 : 3.5}
              fill={p.esActual ? actualColor : lineColor}
            >
              <title>
                {formatFechaCorta(p.fecha)}: {p.valor}
                {p.unidad ? ` ${p.unidad}` : ''}
                {p.esActual ? ' (actual)' : ''}
              </title>
            </circle>
            <text
              x={xAt(i)}
              y={CHART_H - 12}
              textAnchor="middle"
              fontSize={9}
              fill={axisColor}
            >
              {formatFechaCorta(p.fecha)}
            </text>
          </g>
        ))}
      </svg>
    </Box>
  );
}

const TendenciaAnalitoDialog: React.FC<TendenciaAnalitoDialogProps> = ({
  open,
  onClose,
  solicitudId,
  tipoExamenId,
  tipoExamenNombre,
  tipoExamenCodigo,
  actual,
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [previos, setPrevios] = useState<
    Array<{
      valor: string;
      valor_numerico?: string | number | null;
      unidad?: string | null;
      fecha: string | null;
      solicitud_id: number;
      solicitud_numero: string | null;
    }>
  >([]);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoading(true);
    setError('');
    setPrevios([]);
    getHistorialAnalitos(solicitudId, 50)
      .then((data) => {
        if (cancelled) return;
        const item = data.analitos.find((a) => a.tipo_examen_id === tipoExamenId);
        setPrevios(item?.previos ?? []);
        setLoading(false);
      })
      .catch(() => {
        if (cancelled) return;
        setError('No se pudo cargar el historial de este analito.');
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, solicitudId, tipoExamenId]);

  const serie = useMemo(
    () =>
      armarSerieTendencia({
        previos,
        actual: actual
          ? {
              valor: actual.valor,
              valor_numerico: actual.valor_numerico,
              unidad: actual.unidad,
              fecha: actual.fecha,
              solicitudId,
              solicitudNumero: actual.solicitudNumero ?? null,
            }
          : null,
      }),
    [previos, actual, solicitudId]
  );

  const numericos = useMemo(() => puntosNumericos(serie), [serie]);
  const rangoMin = parseRango(actual?.rango_min);
  const rangoMax = parseRango(actual?.rango_max);
  const unidad =
    actual?.unidad ||
    serie.find((p) => p.unidad)?.unidad ||
    null;

  const titulo = tipoExamenCodigo
    ? `${tipoExamenNombre} (${tipoExamenCodigo})`
    : tipoExamenNombre;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Tendencia · {titulo}</DialogTitle>
      <DialogContent dividers>
        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress size={32} />
          </Box>
        )}
        {!loading && error && <Alert severity="warning">{error}</Alert>}
        {!loading && !error && serie.length === 0 && (
          <Typography color="text.secondary">No hay valores para graficar.</Typography>
        )}
        {!loading && !error && serie.length > 0 && (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {numericos.length >= 2 ? (
              <TendenciaChartSvg
                puntos={numericos}
                rangoMin={rangoMin}
                rangoMax={rangoMax}
                unidad={unidad}
              />
            ) : (
              <Alert severity="info">
                {numericos.length === 1
                  ? 'Hace falta al menos otro valor numérico histórico para mostrar la gráfica. Se listan los resultados abajo.'
                  : 'Este analito no tiene valores numéricos suficientes para una gráfica. Se listan los resultados abajo.'}
              </Alert>
            )}
            {unidad && numericos.length >= 2 && (
              <Typography variant="caption" color="text.secondary">
                Unidad: {unidad}
                {rangoMin != null && rangoMax != null
                  ? ` · Referencia: ${rangoMin} – ${rangoMax}`
                  : ''}
              </Typography>
            )}
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Fecha</TableCell>
                  <TableCell>Valor</TableCell>
                  <TableCell>Orden</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {[...serie].reverse().map((p, i) => (
                  <TableRow key={`${p.solicitudId ?? 'x'}-${i}`} selected={p.esActual}>
                    <TableCell>
                      {formatFechaCorta(p.fecha)}
                      {p.esActual ? ' · actual' : ''}
                    </TableCell>
                    <TableCell sx={{ fontVariantNumeric: 'tabular-nums' }}>
                      {p.valor}
                      {p.unidad ? ` ${p.unidad}` : ''}
                    </TableCell>
                    <TableCell>{p.solicitudNumero || (p.solicitudId ? `#${p.solicitudId}` : '—')}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cerrar</Button>
      </DialogActions>
    </Dialog>
  );
};

export default TendenciaAnalitoDialog;
