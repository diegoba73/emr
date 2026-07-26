import React, { useEffect, useMemo, useState } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Stack,
  TextField,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Alert,
} from '@mui/material';
import { apiService } from '../services/api';
import type { BiKpisResponse } from '../types/bi';

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

function daysAgoISO(n: number) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}

const BiDashboard: React.FC = () => {
  const [desde, setDesde] = useState(daysAgoISO(30));
  const [hasta, setHasta] = useState(todayISO());
  const [data, setData] = useState<BiKpisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await apiService.getBiKpis({ desde, hasta }));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error al cargar KPIs');
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const cards = useMemo(() => {
    const out: Array<{ title: string; value: string; subtitle?: string }> = [];
    if (data?.lims) {
      out.push({
        title: 'TAT p50 (h)',
        value: data.lims.tat_horas.p50 != null ? String(data.lims.tat_horas.p50) : '—',
        subtitle: `n=${data.lims.tat_horas.n} · p90=${data.lims.tat_horas.p90 ?? '—'}`,
      });
      out.push({
        title: 'Rechazo muestras',
        value: `${Math.round(data.lims.rechazo_muestras.tasa * 1000) / 10}%`,
        subtitle: `${data.lims.rechazo_muestras.rechazadas}/${data.lims.rechazo_muestras.total}`,
      });
      out.push({
        title: 'Órdenes LIMS',
        value: String(data.lims.ordenes_en_rango),
      });
    }
    if (data?.turnos) {
      out.push({
        title: 'No-show',
        value: `${Math.round(data.turnos.tasa_no_show * 1000) / 10}%`,
        subtitle: `${data.turnos.no_shows} de ${data.turnos.total_programados}`,
      });
    }
    if (data?.internacion && !data.internacion.error) {
      out.push({
        title: 'Ocupación camas',
        value: `${data.internacion.ocupacion_pct}%`,
        subtitle: `${data.internacion.internaciones_activas} internaciones activas`,
      });
    }
    return out;
  }, [data]);

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h5" fontWeight={700} gutterBottom>
        Indicadores de calidad
      </Typography>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mb: 2 }} alignItems="center">
        <TextField
          type="date"
          label="Desde"
          size="small"
          InputLabelProps={{ shrink: true }}
          value={desde}
          onChange={(e) => setDesde(e.target.value)}
        />
        <TextField
          type="date"
          label="Hasta"
          size="small"
          InputLabelProps={{ shrink: true }}
          value={hasta}
          onChange={(e) => setHasta(e.target.value)}
        />
        <Button variant="contained" onClick={load} disabled={loading}>
          Actualizar
        </Button>
      </Stack>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      {loading && <CircularProgress size={28} />}
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', md: '1fr 1fr 1fr' },
          gap: 2,
          mb: 3,
        }}
      >
        {cards.map((c) => (
          <Card key={c.title} variant="outlined">
            <CardContent>
              <Typography variant="overline" color="text.secondary">
                {c.title}
              </Typography>
              <Typography variant="h4">{c.value}</Typography>
              {c.subtitle && (
                <Typography variant="body2" color="text.secondary">
                  {c.subtitle}
                </Typography>
              )}
            </CardContent>
          </Card>
        ))}
      </Box>

      {data?.lims?.productividad?.por_usuario?.length ? (
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Productividad (resultados validados)
          </Typography>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Usuario</TableCell>
                <TableCell align="right">Total</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {data.lims.productividad.por_usuario.map((r) => (
                <TableRow key={r.usuario}>
                  <TableCell>{r.usuario}</TableCell>
                  <TableCell align="right">{r.total}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Box>
      ) : null}

      {data?.lims?.rechazo_muestras?.top_motivos?.length ? (
        <Box>
          <Typography variant="h6" gutterBottom>
            Motivos de rechazo
          </Typography>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Motivo</TableCell>
                <TableCell align="right">Total</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {data.lims.rechazo_muestras.top_motivos.map((r) => (
                <TableRow key={r.motivo_rechazo}>
                  <TableCell>{r.motivo_rechazo}</TableCell>
                  <TableCell align="right">{r.total}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Box>
      ) : null}
    </Box>
  );
};

export default BiDashboard;
